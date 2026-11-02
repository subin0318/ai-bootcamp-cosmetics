import json

from parsing.normalize import load_ingredient_alias, expand_ingredient_terms
from parsing.query_parser import parse_query
from search.filters import filter_products
from search.vector_search import VectorSearcher


def load_products():
    with open("data/products/products.json", "r", encoding="utf-8") as f:
        return json.load(f)


PRODUCTS = load_products()
PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}

ALIAS_MAP = load_ingredient_alias()
SEARCHER = VectorSearcher()


def recommend_auto(query_text: str, return_n: int = 5):
    parsed = parse_query(query_text)

    skin_type = parsed["skin_type"]      # 디폴트 강제 X 권장
    product_type = parsed["product_type"]
    ingredient = parsed["ingredient"] or ""

    # 점진적으로 top_k 확대
   
    top_k = 200
    max_top_k = 3000  # 또는 5000

    while True:
        hits = SEARCHER.search(query_text, top_k=top_k)

        candidate_products = []
        for h in hits:
            p = PRODUCT_BY_ID.get(h["product_id"])
            if not p:
                continue
            p2 = dict(p)
            p2["_vec_score"] = h["score"]
            candidate_products.append(p2)

        # 필터링
        if ingredient:
            ingredient_terms = expand_ingredient_terms(ingredient, ALIAS_MAP)
            filtered = filter_products(
                products=candidate_products,
                skin_type=skin_type,
                ingredient_terms=ingredient_terms,
                product_type=product_type,
                budget_krw_max=None,
            )
        else:
            filtered = []
            for p in candidate_products:
                # 타입 조건이 있으면 적용, 없으면 통과
                if product_type and p.get("category") != product_type:
                    continue

                # skin_type 조건이 있으면 적용, 없으면 통과
                p_skin = p.get("skin_type") or []
                if skin_type:
                    if isinstance(p_skin, str):
                        p_skin = [p_skin]
                    if skin_type not in p_skin:
                        continue

                filtered.append(p)

        # 정렬
        filtered.sort(key=lambda x: x.get("_vec_score", 0), reverse=True)

        # 충분히 모였거나 더 늘릴 수 없으면 종료
        if len(filtered) >= return_n or top_k >= max_top_k:
            return parsed, filtered[:return_n]

        # 부족하면 top_k 2배로 확장
        top_k *= 2


def main():
    query = "건성 피부 크림 추천"
    parsed, results = recommend_auto(query, return_n=5)

    if not results:
        print("최종 추천:")
        print("조건에 맞는 제품이 없습니다.")
        return

    print("최종 추천 Top-5:")
    for i, r in enumerate(results, start=1):
        # 벡터 점수(_vec_score)를 출력 (없으면 score, 그것도 없으면 0)
        s = r.get("_vec_score", r.get("score", 0))
        print(f"{i}. {r['name']} ({r.get('price', '가격정보없음')}원) score={s:.4f}")
     

if __name__ == "__main__":
    main()
