# src/search_parser.py
import re

SKIN_SYNONYMS = {
    "건성": "dry",
    "복합성": "combination",
    "지성": "oily",
    "민감": "sensitive",
    "민감성": "sensitive",
}

CATEGORY_SYNONYMS = {
    "크림": "cream",
    "토너": "toner",
    "세럼": "serum",
    "클렌저": "cleanser",
    "선크림": "sunscreen",
    "자차": "sunscreen",
    "선젤": "sunscreen",
}

OILY_HINTS = ["t존", "번들", "피지", "유분", "기름", "트러블"]
DRY_HINTS  = ["건조", "땡김", "각질", "속건조"]
CALM_HINTS = ["진정", "시카", "민감", "장벽"]
LIGHT_HINTS = ["산뜻", "가벼", "여름"]

INGREDIENT_WORDS = {
    "panthenol": ["판테놀"],
    "cica": ["시카", "병풀", "병풀추출물", "마데카소사이드"],
    "hyaluronic": ["히알", "히알루론산"],
    "niacinamide": ["나이아신", "나이아신아마이드"],
    "vitaminc": ["비타민c", "비타민 c", "아스코빅", "아스코빅애씨드"],
}

def normalize(q: str) -> str:
    q = q.lower()
    q = re.sub(r"[^0-9a-z가-힣\s]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q

def extract_constraints(query: str) -> dict:
    q = normalize(query)
    q_nospace = q.replace(" ", "")

    category = None
    for k, v in CATEGORY_SYNONYMS.items():
        if k in q:
            category = v
            break

    skin = None
    for k, v in SKIN_SYNONYMS.items():
        if k in q:
            skin = v
            break

    skin_candidates = set()
    if skin:
        skin_candidates.add(skin)

    if any(h in q_nospace for h in OILY_HINTS):
        skin_candidates.add("oily")
    if any(h in q_nospace for h in DRY_HINTS):
        skin_candidates.add("dry")
    if any(h in q_nospace for h in ["민감", "민감성"]):
        skin_candidates.add("sensitive")

    ingredients = set()
    for key, words in INGREDIENT_WORDS.items():
        if any(w.replace(" ", "") in q_nospace for w in words):
            ingredients.add(key)

    intent = {
        "want_calm": any(h in q_nospace for h in CALM_HINTS),
        "prefer_light": any(h in q_nospace for h in LIGHT_HINTS),
    }

    return {
        "category": category,
        "skin_candidates": skin_candidates if skin_candidates else None,
        "ingredients": ingredients,
        "intent": intent,
        "raw": q,
    }
