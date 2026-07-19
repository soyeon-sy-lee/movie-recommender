# Movie Recommender

인생영화 3편을 입력하면 취향 태그 기반으로 영화 3편을 추천하는 정적 웹앱입니다.

## Live Demo

https://soyeon-sy-lee.github.io/movie-recommender/

## Features

- 영화 제목 자동완성
- 유사도 점수 기반 Top 3 추천
- 이미 본 영화 개별 교체
- 취향 해석 코멘트
- 👍 / 👎 피드백 기반 로컬 재학습
- 2010년 이후 영화 중심 추천 후보 다운샘플링

## 데이터셋 생성

이 프로젝트는 추천 후보를 만들기 위해 MovieLens 데이터셋과 Wikidata의 공개 정보를 사용합니다. 데이터 생성은 로컬에서 재현 가능하며, 다음 절차로 진행됩니다.

1. MovieLens ml-latest-small 다운로드

```bash
mkdir -p /private/tmp
curl -L -o /private/tmp/ml-latest-small.zip https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
```

2. 데이터 생성 스크립트 실행

```bash
python3 build_dataset.py
```

- 위 스크립트는 `/private/tmp/ml-latest-small.zip` 경로의 압축을 읽어 `movies_dataset.js`와 `wikidata_ko_labels_cache.json`을 프로젝트 루트에 생성합니다.
- 생성된 `movies_dataset.js`는 클라이언트에서 `window.MOVIE_DATASET`으로 사용됩니다.

데이터 출처 및 라이선스

- MovieLens (ml-latest-small): https://grouplens.org/datasets/movielens/ (원본 데이터셋의 이용 약관을 확인하세요)
- Wikidata (한국어 라벨 조회): https://www.wikidata.org/

참고: 원본 데이터의 라이선스/이용약관은 각 출처에 따릅니다. 코드(애플리케이션) 자체와 데이터의 라이선스는 별도로 검토해야 합니다.

## 동작 원리 (간단한 아키텍처)

- 데이터 생산
  - `build_dataset.py`가 MovieLens CSV(links.csv, movies.csv, tags.csv)를 파싱하고, 장르/태그 매핑과 사용자 태그 매핑을 합쳐 영화별 태그를 생성합니다.
  - Wikidata에서 한국어 레이블을 추가로 조회해 `wikidata_ko_labels_cache.json`에 캐시합니다.
  - 최종 영화 목록은 `movies_dataset.js`로 출력되며, 클라이언트에서 정적 데이터로 사용됩니다.

- 클라이언트(프런트엔드)
  - `index.html`이 UI 진입점으로, `movies_dataset.js`를 불러 자동완성, 추천 랭킹, 취향 해석, 피드백(로컬 재학습)을 수행합니다.
  - 로컬 학습(피드백)은 브라우저의 localStorage에 `movieRecommenderLearning:v1` 키로 저장되어 사용자별 간단한 맞춤화에 사용됩니다.

- 주요 설정 포인트 (코드 내)
  - `build_dataset.py`의 RECENT_YEAR_CUTOFF (기본값 2010)와 TARGET_RECENT_RATIO (기본값 10)은 추천 후보의 연도 균형을 조정합니다.
  - `movies_dataset.js` 내 `LEARNING_STORAGE_KEY`는 로컬 학습 키 이름입니다.


