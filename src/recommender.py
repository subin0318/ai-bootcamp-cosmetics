# src/recommender.py
from search_parser import extract_constraints, INGREDIENT_WORDS

def score_product(p: dict, c: dict) -> int:
    score = 0

    # 1) category (가장 중요)
    if c["category"] and p["category"] == c["category"]:
        score += 5

    # 2) skin
    if c["skin_candidates"]:
        if any(s in p["skin_type"] for s in c["skin_candidates"]):
            score += 3

    # 3) ingredients
    raw = (p.get("ingredients_raw") or "").lower().replace(" ", "")
    for key in c["ingredients"]:
        if any(w.replace(" ", "") in raw for w in INGREDIENT_WORDS[key]):
            score += 3

    # 4) intent (여름/산뜻/진정 같은 보조 신호)
    if c["intent"].get("prefer_light"):
        if "oily" in p["skin_type"] or "combination" in p["skin_type"]:
            score += 1

    if c["intent"].get("want_calm"):
        if "sensitive" in p["skin_type"]:
            score += 1

    return score

def recommend(products: list, query: str, topk: int = 5) -> list:
    c = extract_constraints(query)
    scored = [(score_product(p, c), p) for p in products]
    scored.sort(key=lambda x: (-x[0], x[1]["price_krw"]))

    # ❗ Top-5 강제 (0점도 포함 가능하지만, 아래처럼 커트 가능)
    result = [p for s, p in scored if s > 0][:topk]

    # 그래도 부족하면(데이터가 너무 적으면) 0점도 채워서 Top-5 보장
    if len(result) < topk:
        filler = [p for s, p in scored if p not in result][: (topk - len(result))]
        result.extend(filler)

    return result
