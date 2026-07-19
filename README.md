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

## 개발자 노트 / 유지보수

- 경로 유연성
  - 현재 `build_dataset.py`는 기본적으로 `/private/tmp/ml-latest-small.zip` 경로를 사용합니다. 환경에 따라 CLI 인자나 환경변수로 입력 파일 경로를 받도록 개선하는 것을 권장합니다.

- 생성 파일 취급
  - `movies_dataset.js`와 `wikidata_ko_labels_cache.json`은 생성 파일입니다. 저장소에 큰 데이터 파일을 커밋하면 리포지토리 크기가 급증하므로, 가능하면 다음 중 하나를 권장합니다:
    - .gitignore에 추가하고 CI(예: GitHub Actions)에서 배포 시 생성
    - 생성 파일을 분할하거나 압축하여 저장

- CI/배포 권장 사항
  - GitHub Pages에 정적 파일을 배포 중이므로, `movies_dataset.js`를 CI 파이프라인에서 생성하고 결과만 배포하는 흐름으로 바꾸면 협업과 PR 유지 관리가 쉬워집니다.

- 캐시 및 외부 호출
  - Wikidata 조회 결과는 `wikidata_ko_labels_cache.json`에 저장됩니다. 캐시 파일을 재사용하면 API 호출 횟수를 줄이고 재현성을 높일 수 있습니다.

- 코드 개선 제안
  - `build_dataset.py`를 CLI 인자(또는 환경변수)로 입력/출력 경로와 제한(예: fetch limit)을 받도록 리팩터링하면 재현성과 테스트가 쉬워집니다.
  - 현재 태그 매핑(USER_TAG_MAP, GENRE_TAGS 등)은 코드 상수로 정의되어 있으므로 별도 구성 파일(예: YAML/JSON)로 분리하면 확장성이 좋아집니다.

- 로컬 학습/프라이버시
  - 사용자의 피드백(👍/👎)은 로컬에만 저장됩니다(localStorage). 외부 전송은 하지 않으므로 개인 정보 유출 우려는 없습니다.

---

원하시면 제가 이 변경사항을 바로 README.md에 커밋(또는 별도 브랜치로 PR 생성)했습니다. 다른 문구 수정이나 추가 항목이 있으면 알려주세요.
