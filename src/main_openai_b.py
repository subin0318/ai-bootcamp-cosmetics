import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from getpass import getpass
from openai import OpenAI
import re

# OPENAI_API_KEY: 환경변수에 없으면 실행 시 입력받음 (입력값은 화면에 표시되지 않음)
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass("OPENAI_API_KEY 입력: ").strip()

FORCE_REINDEX = True

# ✅ 너가 원한대로: 모델명도 그대로 유지 (recommend_top5() 안에서 사용)
MODEL_NAME = "gpt-4o-mini"

# ===== 경로 설정 =====
ROOT = Path(__file__).resolve().parents[1]  # src/.. = project root
PRODUCTS_JSON = ROOT / "data" / "products" / "products.json"  # 네 경로 기준
VS_ID_FILE = ROOT / "vector_store_id.txt"

# ===== OpenAI 클라이언트 =====
client = OpenAI()

# ===== 프롬프트 (Top-5 채우기 + 모호한 쿼리 해석 강화) =====
SYSTEM_PROMPT = """\
너는 화장품 검색/추천 엔진이다.
반드시 file_search로 검색된 제품 레코드(업로드된 products.json에서 나온 항목)만 사용해 답해라.
추측/상상으로 제품을 만들면 안 된다.

중요:
- 쿼리가 모호해도(예: "여름 피부") 최대한 해석해서 '가까운' 제품을 Top-5로 채워라.
- 단, 검색 컨텍스트에 없는 제품은 절대 results에 넣지 마라.

해석 규칙(쿼리 → 힌트):
- 피부타입 키워드:
  - 건성/건조/속건조/땡김/각질 => dry
  - 지성/유분/피지/번들/T존/트러블 => oily
  - 복합/복합성 => combination
  - 민감/예민/자극/진정 => sensitive
  - 여름/산뜻/가벼운 => oily 또는 combination 성향 우선(무겁지 않은 제품 선호)
- 카테고리 키워드:
  - 크림 => cream
  - 세럼/앰플 => serum
  - 토너 => toner
  - 클렌저/폼/워시 => cleanser
  - 선크림/자차/선젤 => sunscreen
  - 카테고리가 없으면 cream을 기본으로 둬라.
- 성분 키워드:
  - 판테놀/세라마이드/시카(병풀/마데카소사이드)/히알루론산/나이아신아마이드/비타민C(아스코빅애씨드)
  - ingredients_raw에서 부분일치로 매칭해라.

선정/정렬 규칙:
1) category 일치가 최우선
2) skin_type 일치(또는 포함)가 그 다음
3) ingredient 일치
4) 동점이면 price_krw 낮은 순

출력은 반드시 JSON만 출력해라. (설명 문장 금지)
형식:
{
  "parsed_hint": {
    "skin_type": "dry|oily|combination|sensitive|null",
    "category": "cream|serum|toner|cleanser|sunscreen|null",
    "ingredient": "string|null"
  },
  "results": [
    {
      "id": "P001",
      "name": "제품명",
      "category": "cream",
      "price_krw": 28000,
      "skin_type": ["dry"],
      "reason": "쿼리와의 매칭 이유(짧게)"
    }
  ]
}

규칙:
- results는 '가능하면' 5개를 채워라. (컨텍스트 후보가 5개 미만이면 있는 만큼만)
- 검색된 컨텍스트에 해당 제품 레코드가 없으면 results에 넣지 마라.
- 후보가 정말 없으면 results는 [] 로 둬라.
- price_krw가 없으면 null로 둬라.
"""


def load_vector_store_id() -> Optional[str]:
    env_id = os.getenv("OPENAI_VECTOR_STORE_ID")
    if env_id:
        return env_id.strip()
    if VS_ID_FILE.exists():
        value = VS_ID_FILE.read_text(encoding="utf-8").strip()
        return value or None
    return None


def save_vector_store_id(vs_id: str) -> None:
    VS_ID_FILE.write_text(vs_id, encoding="utf-8")


def setup_vector_store_if_needed() -> str:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY 환경변수가 없습니다.")

    if not PRODUCTS_JSON.exists():
        raise FileNotFoundError(f"products.json 파일이 없습니다: {PRODUCTS_JSON}")

    # ✅ 무조건 새로 생성
    vs = client.vector_stores.create(name="cosmetics-products")

    uploaded = client.files.create(
        file=PRODUCTS_JSON.open("rb"),
        purpose="assistants",
    )

    client.vector_stores.files.create(
        vector_store_id=vs.id,
        file_id=uploaded.id,
    )

    save_vector_store_id(vs.id)
    return vs.id


def robust_json_loads(text: str) -> Dict[str, Any]:
    """
    모델이 JSON 앞뒤로 잡텍스트를 섞어도 JSON만 뽑아서 최대한 파싱
    """
    text = (text or "").strip()
    if not text:
        return {
            "parsed_hint": {"skin_type": None, "category": None, "ingredient": None},
            "results": [],
            "_raw_output": "",
        }

    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass

    return {
        "parsed_hint": {"skin_type": None, "category": None, "ingredient": None},
        "results": [],
        "_raw_output": text,
    }


def recommend_top5(query: str, vector_store_id: str) -> Dict[str, Any]:
    """
    Responses + file_search로 검색 → 모델이 JSON으로 Top-5 생성
    """
    resp = client.responses.create(
        model=MODEL_NAME,  # ✅ 모델은 손대지 말라고 해서 그대로
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        tools=[
            {
                "type": "file_search",
                "vector_store_ids": [vector_store_id],
                "max_num_results": 50,  # 후보 넉넉히
            }
        ],
    )

    text = (resp.output_text or "").strip()
    return robust_json_loads(text)


def print_results(result_obj: Dict[str, Any]) -> None:
    results = result_obj.get("results", [])
    if not results:
        print("최종 추천:")
        print("조건에 맞는 제품이 없습니다.")
        if result_obj.get("_raw_output"):
            print("\n[DEBUG] 모델 원문 출력(파싱 실패/빈 결과):")
            print(result_obj["_raw_output"])
        return

    print("최종 추천 Top-5:")
    for i, r in enumerate(results[:5], start=1):
        name = r.get("name", "이름없음")
        price = r.get("price_krw")
        price_text = f"{int(price)}원" if isinstance(price, (int, float)) else "가격정보없음"
        category = r.get("category", "unknown")
        skin = r.get("skin_type", [])
        skin_text = ",".join(skin) if isinstance(skin, list) else str(skin)

        print(f"{i}. {name} ({price_text}) [{category}] [{skin_text}]")
        reason = r.get("reason")
        if reason:
            print(f"   - {reason}")


def main():
    vs_id = setup_vector_store_if_needed()
    print(f"[OK] VECTOR_STORE_ID = {vs_id}")

    queries = [
    
        "여름 크림 추천 (판테놀)",
    ]

    for q in queries:
        print("\n" + "=" * 60)
        print("QUERY:", q)
        out = recommend_top5(q, vs_id)
        print_results(out)


if __name__ == "__main__":
    main()