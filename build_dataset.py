import csv
import io
import json
import math
import re
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ZIP_PATH = Path("/private/tmp/ml-latest-small.zip")
OUT_PATH = ROOT / "movies_dataset.js"
KO_LABEL_CACHE_PATH = ROOT / "wikidata_ko_labels_cache.json"
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
RECENT_YEAR_CUTOFF = 2010
TARGET_RECENT_RATIO = 10

GENRE_TAGS = {
    "Action": ["action", "kinetic"],
    "Adventure": ["adventure", "journey"],
    "Animation": ["animation", "visual"],
    "Children": ["family", "warm"],
    "Comedy": ["comedy", "warm"],
    "Crime": ["crime", "dark"],
    "Documentary": ["documentary", "realistic"],
    "Drama": ["drama", "emotional"],
    "Fantasy": ["fantasy", "wonder"],
    "Film-Noir": ["noir", "crime"],
    "Horror": ["horror", "dark"],
    "IMAX": ["visual", "grand"],
    "Musical": ["music", "dream"],
    "Mystery": ["mystery", "puzzle"],
    "Romance": ["romance", "bittersweet"],
    "Sci-Fi": ["sci-fi", "future"],
    "Thriller": ["thriller", "dark"],
    "War": ["war", "survival"],
    "Western": ["western", "classic"],
}

USER_TAG_MAP = {
    "atmospheric": "melancholy",
    "bittersweet": "bittersweet",
    "black comedy": "dark",
    "cerebral": "mind",
    "cinematography": "visual",
    "clever": "puzzle",
    "coming of age": "coming-of-age",
    "dark": "dark",
    "disturbing": "dark",
    "dreamlike": "surreal",
    "emotional": "emotional",
    "family": "family",
    "funny": "comedy",
    "heartwarming": "warm",
    "inspirational": "hope",
    "intelligent": "precise",
    "love": "romance",
    "mindfuck": "mind",
    "mystery": "mystery",
    "philosophical": "philosophical",
    "psychology": "mind",
    "quirky": "quirky",
    "revenge": "revenge",
    "romance": "romance",
    "sci-fi": "sci-fi",
    "surreal": "surreal",
    "thought-provoking": "philosophical",
    "time travel": "time",
    "twist ending": "twist",
    "visually appealing": "visual",
}

WIKIDATA_GENRE_TAGS = {
    "action film": ["action", "kinetic"],
    "adventure film": ["adventure", "journey"],
    "animated film": ["animation", "visual"],
    "anime": ["animation", "visual"],
    "comedy film": ["comedy", "warm"],
    "crime film": ["crime", "dark"],
    "documentary film": ["documentary", "realistic"],
    "drama film": ["drama", "emotional"],
    "fantasy film": ["fantasy", "wonder"],
    "horror film": ["horror", "dark"],
    "musical film": ["music", "dream"],
    "mystery film": ["mystery", "puzzle"],
    "romance film": ["romance", "bittersweet"],
    "romantic comedy": ["romance", "comedy", "warm"],
    "science fiction film": ["sci-fi", "future"],
    "thriller film": ["thriller", "dark"],
    "war film": ["war", "survival"],
    "western film": ["western", "classic"],
}


def parse_title(raw_title):
    match = re.search(r"\((\d{4})\)\s*$", raw_title)
    year = int(match.group(1)) if match else None
    title = re.sub(r"\s*\(\d{4}\)\s*$", "", raw_title)
    alt_match = re.match(r"(.+), The$", title)
    if alt_match:
        title = f"The {alt_match.group(1)}"
    alt_match = re.match(r"(.+), A$", title)
    if alt_match:
        title = f"A {alt_match.group(1)}"
    alt_match = re.match(r"(.+), An$", title)
    if alt_match:
        title = f"An {alt_match.group(1)}"
    return title, year


def unique(items):
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def request_sparql(query):
    data = urllib.parse.urlencode({"query": query, "format": "json"}).encode("utf-8")
    request = urllib.request.Request(
        WIKIDATA_ENDPOINT,
        data=data,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "movie-recommender-local/1.0 (public Wikidata enrichment)",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def binding_value(binding, key):
    return binding.get(key, {}).get("value", "")


def fetch_korean_labels(imdb_ids):
    if KO_LABEL_CACHE_PATH.exists():
        return json.loads(KO_LABEL_CACHE_PATH.read_text(encoding="utf-8"))

    labels = {}
    imdb_values = sorted({imdb_id for imdb_id in imdb_ids if imdb_id})
    for start in range(0, len(imdb_values), 250):
        batch = imdb_values[start:start + 250]
        values = " ".join(f'"{imdb_id}"' for imdb_id in batch)
        query = f"""
        SELECT ?imdb ?koLabel WHERE {{
          VALUES ?imdb {{ {values} }}
          ?film wdt:P345 ?imdb.
          ?film rdfs:label ?koLabel.
          FILTER(LANG(?koLabel) = "ko")
        }}
        """
        try:
          result = request_sparql(query)
        except Exception as exc:
          print(f"Warning: Korean label batch failed at {start}: {exc}")
          continue
        for row in result["results"]["bindings"]:
            labels[binding_value(row, "imdb")] = binding_value(row, "koLabel")
        time.sleep(0.15)
    KO_LABEL_CACHE_PATH.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    return labels


def tags_from_wikidata_genres(genre_text):
    tags = []
    for genre in genre_text.split("|"):
        normalized = genre.strip().lower()
        tags.extend(WIKIDATA_GENRE_TAGS.get(normalized, []))
        if "comedy" in normalized:
            tags.extend(["comedy", "warm"])
        if "romance" in normalized or "romantic" in normalized:
            tags.extend(["romance", "bittersweet"])
        if "thriller" in normalized:
            tags.extend(["thriller", "dark"])
        if "horror" in normalized:
            tags.extend(["horror", "dark"])
        if "science fiction" in normalized or "sci-fi" in normalized:
            tags.extend(["sci-fi", "future"])
        if "animation" in normalized or "animated" in normalized:
            tags.extend(["animation", "visual"])
        if "drama" in normalized:
            tags.extend(["drama", "emotional"])
        if "crime" in normalized:
            tags.extend(["crime", "dark"])
        if "documentary" in normalized:
            tags.extend(["documentary", "realistic"])
    return unique(tags)[:7] or ["drama", "emotional"]


def fetch_recent_wikidata_movies(limit):
    if limit <= 0:
        return []

    movies = []
    page_size = 750
    for year in range(2026, RECENT_YEAR_CUTOFF - 1, -1):
        for offset in range(0, 10000, page_size):
            if len(movies) >= limit:
                return movies[:limit]
            query = f"""
            SELECT ?film ?enLabel ?koLabel ?imdb ?date WHERE {{
              ?film wdt:P31 wd:Q11424;
                    wdt:P577 ?date;
                    rdfs:label ?enLabel.
              FILTER(LANG(?enLabel) = "en")
              FILTER(?date >= "{year}-01-01T00:00:00Z"^^xsd:dateTime && ?date < "{year + 1}-01-01T00:00:00Z"^^xsd:dateTime)
              ?film rdfs:label ?koLabel.
              FILTER(LANG(?koLabel) = "ko")
              OPTIONAL {{ ?film wdt:P345 ?imdb. }}
            }}
            LIMIT {page_size}
            OFFSET {offset}
            """
            try:
                result = request_sparql(query)
            except Exception as exc:
                print(f"Warning: recent Wikidata fetch failed for {year} offset {offset}: {exc}")
                break
            rows = result["results"]["bindings"]
            for row in rows:
                english_title = binding_value(row, "enLabel")
                korean_title = binding_value(row, "koLabel")
                date = binding_value(row, "date")
                movie_year = int(date[:4]) if date[:4].isdigit() else year
                movies.append({
                    "id": binding_value(row, "imdb") or binding_value(row, "film").rsplit("/", 1)[-1],
                    "title": korean_title or english_title,
                    "englishTitle": english_title,
                    "year": movie_year,
                    "tags": ["drama", "emotional"],
                    "note": "Wikidata 공개 영화 데이터를 바탕으로 2010년 이후 추천 후보에 포함했습니다.",
                })
            print(f"Fetched {len(movies)} recent Wikidata movies through {year}")
            if len(rows) < page_size:
                break
            time.sleep(0.2)
    return movies[:limit]


def deduplicate_movies(movies):
    seen = set()
    result = []
    for movie in movies:
        key = movie.get("id") or f"{movie['englishTitle'].lower()}-{movie.get('year', '')}"
        fallback_key = f"{movie['englishTitle'].lower()}-{movie.get('year', '')}"
        if key in seen or fallback_key in seen:
            continue
        seen.add(key)
        seen.add(fallback_key)
        result.append(movie)
    return result


def main():
    if not ZIP_PATH.exists():
        raise SystemExit(f"Missing dataset zip: {ZIP_PATH}")

    tag_counts = defaultdict(Counter)
    imdb_by_movie_id = {}
    with zipfile.ZipFile(ZIP_PATH) as archive:
        with archive.open("ml-latest-small/links.csv") as links_file:
            reader = csv.DictReader(io.TextIOWrapper(links_file, encoding="utf-8"))
            for row in reader:
                imdb_id = row["imdbId"].strip()
                if imdb_id:
                    imdb_by_movie_id[row["movieId"]] = f"tt{imdb_id.zfill(7)}"

        korean_labels = fetch_korean_labels(imdb_by_movie_id.values())

        with archive.open("ml-latest-small/tags.csv") as tags_file:
            reader = csv.DictReader(io.TextIOWrapper(tags_file, encoding="utf-8"))
            for row in reader:
                normalized = row["tag"].strip().lower()
                mapped = USER_TAG_MAP.get(normalized)
                if mapped:
                    tag_counts[row["movieId"]][mapped] += 1

        movies = []
        with archive.open("ml-latest-small/movies.csv") as movies_file:
            reader = csv.DictReader(io.TextIOWrapper(movies_file, encoding="utf-8"))
            for row in reader:
                title, year = parse_title(row["title"])
                genres = [] if row["genres"] == "(no genres listed)" else row["genres"].split("|")
                tags = []
                for genre in genres:
                    tags.extend(GENRE_TAGS.get(genre, []))
                tags.extend([tag for tag, _ in tag_counts[row["movieId"]].most_common(3)])
                tags = unique(tags)[:7]
                if not tags:
                    tags = ["drama", "emotional"]
                imdb_id = imdb_by_movie_id.get(row["movieId"], "")
                korean_title = korean_labels.get(imdb_id, "")
                movies.append({
                    "id": imdb_id or f"ml-{row['movieId']}",
                    "title": korean_title or title,
                    "englishTitle": title,
                    "year": year or "",
                    "tags": tags,
                    "note": "",
                })

    ko_movies = [movie for movie in movies if movie["title"] != movie["englishTitle"]]
    old_count = sum(1 for movie in ko_movies if isinstance(movie["year"], int) and movie["year"] < RECENT_YEAR_CUTOFF)
    recent_count = sum(1 for movie in ko_movies if isinstance(movie["year"], int) and movie["year"] >= RECENT_YEAR_CUTOFF)
    needed_recent = max(0, old_count * TARGET_RECENT_RATIO - recent_count)
    if needed_recent:
        fetch_count = math.ceil(needed_recent * 1.4)
        print(f"Need {needed_recent} more Korean-title post-{RECENT_YEAR_CUTOFF} movies for 1:{TARGET_RECENT_RATIO} display ratio; fetching {fetch_count} before dedupe")
        movies.extend(fetch_recent_wikidata_movies(fetch_count))
        movies = deduplicate_movies(movies)

    OUT_PATH.write_text(
        "window.MOVIE_DATASET = "
        + json.dumps(movies, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(movies)} movies to {OUT_PATH}")


if __name__ == "__main__":
    main()
