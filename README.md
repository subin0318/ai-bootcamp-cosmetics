# 피부 유형·성분 기반 화장품 추천 시스템

전남대 AI 부트캠프 경시대회 프로젝트.
"나는 건성 피부야 히알루론산이 들어간 크림 추천해줘"처럼 자연어로 입력하면 피부 유형·제품 종류·성분을 뽑아 로컬 제품 목록(103개)에서 최대 5개를 추천합니다.

> 피부 진단이나 제품 효과 측정 기능은 없습니다. 데이터에 기록된 라벨을 비교할 뿐이며, 가격은 실시간 가격이 아닙니다.

## 동작 방식 (메인: Gradio 화면)

```
사용자 문장 → GPT(gpt-4o-mini)로 조건 JSON 추출 {skin_type, category, ingredient}
           → products.json 필터링 (strict → 종류+성분 → 종류+피부 → 종류만, 단계적 완화)
           → 그룹 내 점수(종류 100 + 피부 50 + 성분 30)·가격 오름차순 정렬
           → 중복 제거 후 상위 5개를 표로 표시
```

GPT는 문장 해석만 하고, 제품 선정은 Python 코드가 합니다.

## 실행 경로

| 경로 | 파일 | 내용 |
| --- | --- | --- |
| A. 추천 화면 (메인) | `src/app_gradio.py` → `src/main_rule_search.py` | GPT 조건 추출 + 규칙 필터·점수 정렬 |
| B. 로컬 벡터 검색 | `src/main.py`, `src/search/` | SentenceTransformer 임베딩 + FAISS + 조건 필터 |
| C. OpenAI 파일 검색 | `src/main_openai_b.py` | 제품 JSON 업로드 후 `file_search`로 GPT가 추천 |
| D. 네이버 쇼핑 연동 | `test.py` | GPT 함수호출 → 네이버 쇼핑 검색 API (별도 Gradio 화면) |
| E. 규칙 기반 모듈 | `src/search_parser.py`, `src/recommender.py` | 키워드 힌트 + 가중치 합산 (A·B에서 미사용) |

## 폴더 구조

```
data/
  products/products.json      제품 103개 (id, name, category, price_krw, skin_type, ingredients_raw)
  dictionaries/               피부·제품 종류·성분 별칭 사전
indexes/                      FAISS 인덱스, 인덱스 행 → 제품 ID 매핑
src/
  app_gradio.py               추천 화면
  main_rule_search.py         A 경로 추천 로직
  main.py                     B 경로 벡터 검색 추천
  main_openai_b.py            C 경로
  parsing/                    질의 파싱, 성분 별칭 확장
  search/                     인덱스 생성, 벡터 검색, 필터
docs/                         상세 기술문서
test.py                       D 경로 (테스트 파일 아님)
```

## 설치 및 실행

Python 가상환경을 켜고 패키지를 설치합니다 (프로젝트 루트에서 실행).

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

API 키는 코드에 넣지 않습니다. 환경변수로 미리 설정하거나, 설정하지 않으면 실행할 때 터미널에서 입력받습니다 (입력값은 화면에 표시되지 않음).

```powershell
$env:OPENAI_API_KEY = "<your-key>"
$env:NAVER_CLIENT_ID = "<your-id>"          # test.py에서만 필요
$env:NAVER_CLIENT_SECRET = "<your-secret>"  # test.py에서만 필요
```

```powershell
python src/app_gradio.py          # A: 추천 화면
python src/main_rule_search.py    # A: 명령행 예제
python src/search/build_index.py  # B: 벡터 인덱스 생성/갱신
python src/main.py                # B: 벡터 검색 예제
python src/main_openai_b.py       # C: 파일 검색 예제
python test.py                    # D: 네이버 쇼핑 화면 (네이버 API 키 필요)
```

## 알려진 제약

- 저장된 FAISS 인덱스에는 제품 2개만 들어 있음 → B 경로 사용 전 `build_index.py`로 재생성 필요
- B 경로 파서: 한국어 피부 유형 미추출, 성분에 문장 전체가 잡히는 경우, `선크림`이 `cream`으로 분류됨
- A 경로: 조건이 완화되어 채워진 제품도 결과에 섞이며, 화면에 어떤 조건이 맞았는지는 표시하지 않음
- 피부 유형 `all`을 모든 피부에 대응시키는 처리 없음

자세한 내용은 [기술문서](docs/화장품_추천_시스템_기술문서.md)를 참고하세요.

## 기술 스택

Python · OpenAI API (Responses, file_search, function calling) · Sentence-Transformers · FAISS · Gradio · Pandas
