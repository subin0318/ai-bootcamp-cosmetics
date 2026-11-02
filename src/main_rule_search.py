import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from getpass import getpass
from openai import OpenAI

# OPENAI_API_KEY: 환경변수에 없으면 실행 시 입력받음 (입력값은 화면에 표시되지 않음)
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass("OPENAI_API_KEY 입력: ").strip()
MODEL_NAME = "gpt-4o-mini"

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_JSON = ROOT / "data" / "products" / "products.json"

client = OpenAI()

SYSTEM_PROMPT = """\
너는 사용자의 문장에서 화장품 검색 조건을 '정확히' 추출하는 파서(parser)다.
반드시 JSON만 출력해라. 다른 텍스트 금지.

출력 형식:
{
  "skin_type": "dry|oily|combination|sensitive|null",
  "category": "cream|serum|toner|cleanser|sunscreen|null",
  "ingredient": "string|null"
}

규칙:
- 사용자가 '나는 건성 피부야' => skin_type="dry"
- 화장품 종류 단어를 category로 매핑:
  크림=cream, 세럼/앰플=serum, 토너=toner, 클렌저/폼/워시=cleanser, 선크림/자차/선젤=sunscreen
- 성분은 사용자가 말한 키워드를 그대로 ingredient에 넣어라. (예: "히알루론산", "판테놀", "코코글루코사이드")
- 값이 없거나 불명확하면 null
"""

def load_products() -> List[Dict[str, Any]]:
    if not PRODUCTS_JSON.exists():
        raise FileNotFoundError(f"products.json 파일이 없습니다: {PRODUCTS_JSON}")
    with PRODUCTS_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)

def parse_query_with_llm(user_text: str) -> Dict[str, Optional[str]]:
    resp = client.responses.create(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
    )
    raw = (resp.output_text or "").strip()
    try:
        obj = json.loads(raw)
        return {
            "skin_type": obj.get("skin_type"),
            "category": obj.get("category"),
            "ingredient": obj.get("ingredient"),
        }
    except Exception:
        # 파싱 실패 시 전부 null로 처리
        return {"skin_type": None, "category": None, "ingredient": None}

def normalize_skin(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip().lower()
    # 한국어 입력도 혹시 들어오면 대비
    mapping = {
        "건성": "dry", "dry": "dry",
        "지성": "oily", "oily": "oily",
        "복합성": "combination", "combination": "combination",
        "민감성": "sensitive", "sensitive": "sensitive",
    }
    return mapping.get(s, s)

def score_product(p: Dict[str, Any], skin: Optional[str], category: Optional[str], ingredient: Optional[str]) -> int:
    score = 0
    # category match
    if category and p.get("category") == category:
        score += 100
    # skin match (list 포함)
    if skin and skin in (p.get("skin_type") or []):
        score += 50
    # ingredient match (부분일치)
    if ingredient:
        ing_raw = (p.get("ingredients_raw") or "")
        if ingredient in ing_raw:
            score += 30
    return score

def filter_products(products: List[Dict[str, Any]],
                    skin: Optional[str],
                    category: Optional[str],
                    ingredient: Optional[str],
                    top_k: int = 5) -> List[Dict[str, Any]]:
    skin = normalize_skin(skin)

    def has_skin(p): 
        return (not skin) or (skin in (p.get("skin_type") or []))

    def has_category(p):
        return (not category) or (p.get("category") == category)

    def has_ingredient(p):
        if not ingredient:
            return True
        return ingredient in (p.get("ingredients_raw") or "")

    def uniq_extend(dst: List[Dict[str, Any]], src: List[Dict[str, Any]]):
        seen = {d.get("id") for d in dst}
        for p in src:
            if p.get("id") not in seen:
                dst.append(p)
                seen.add(p.get("id"))
            if len(dst) >= top_k:
                break

    # 1) strict: category + skin + ingredient
    strict = [p for p in products if has_category(p) and has_skin(p) and has_ingredient(p)]

    # 2) relax skin: category + ingredient
    cat_ing = [p for p in products if has_category(p) and has_ingredient(p)]

    # 3) relax ingredient: category + skin
    cat_skin = [p for p in products if has_category(p) and has_skin(p)]

    # 4) category only
    cat_only = [p for p in products if has_category(p)]

    def sort_key(p):
        sc = score_product(p, skin, category, ingredient)
        price = p.get("price_krw") if isinstance(p.get("price_krw"), int) else 10**9
        return (-sc, price)

    for arr in (strict, cat_ing, cat_skin, cat_only):
        arr.sort(key=sort_key)

    picked: List[Dict[str, Any]] = []
    uniq_extend(picked, strict)
    uniq_extend(picked, cat_ing)
    uniq_extend(picked, cat_skin)
    uniq_extend(picked, cat_only)

    return picked[:top_k]

def recommend_top5(user_text: str) -> Dict[str, Any]:
    products = load_products()
    parsed = parse_query_with_llm(user_text)

    skin = parsed.get("skin_type")
    category = parsed.get("category")
    ingredient = parsed.get("ingredient")

    matched = filter_products(products, skin, category, ingredient)[:5]

    results = []
    for p in matched:
        results.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "category": p.get("category"),
            "price_krw": p.get("price_krw"),
            "skin_type": p.get("skin_type"),
            "reason": f"조건 매칭: skin={skin}, category={category}, ingredient={ingredient}"
        })

    return {
        "parsed_hint": {
            "skin_type": skin,
            "category": category,
            "ingredient": ingredient
        },
        "results": results
    }

def print_results(obj: Dict[str, Any]) -> None:
    results = obj.get("results", [])
    if not results:
        print("최종 추천:")
        print("조건에 맞는 제품이 없습니다.")
        print("파싱 결과:", obj.get("parsed_hint"))
        return

    print("파싱 결과:", obj.get("parsed_hint"))
    print("최종 추천 Top-5:")
    for i, r in enumerate(results, 1):
        price = r.get("price_krw")
        price_text = f"{price}원" if isinstance(price, int) else "가격정보없음"
        skin_text = ",".join(r.get("skin_type") or [])
        print(f"{i}. {r.get('name')} ({price_text}) [{r.get('category')}] [{skin_text}]")
        print(f"   - {r.get('reason')}")

def main():
    queries = [
        "나는 건성 피부야 히알루론산이 들어간 크림을 추천해줘",
        "나는 민감성 피부야 코코글루코사이드가 들어간 클렌저 추천해줘",
        "나는 지성 피부야 나이아신아마이드 들어간 세럼 추천해줘",
        "나는 복합성 피부야 판테놀 들어간 토너 추천해줘",
    ]

    for q in queries:
        print("\n" + "=" * 60)
        print("QUERY:", q)
        out = recommend_top5(q)
        print_results(out)

if __name__ == "__main__":
    main()
