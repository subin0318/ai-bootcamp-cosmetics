import json
import re
from pathlib import Path

SKIN_PATH = Path("data/dictionaries/skin_alias.json")
CAT_PATH = Path("data/dictionaries/category_alias.json")


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


SKIN_MAP = _load_json(SKIN_PATH)
CAT_MAP = _load_json(CAT_PATH)


def extract_skin_type(text: str) -> str | None:
    t = text.lower()
    for canonical, aliases in SKIN_MAP.items():
        for a in aliases:
            if a.lower() in t:
                return canonical
    return None


def extract_product_type(text: str) -> str | None:
    t = text.lower()
    for canonical, aliases in CAT_MAP.items():
        for a in aliases:
            if a.lower() in t:
                return canonical
    return None


def extract_ingredient(text: str) -> str | None:
    """
    아주 단순한 규칙:
    - 'OO 들어간', 'OO 함유', 'OO 성분', 'OO 포함' 같은 패턴에서 OO 추출
    - 못 찾으면 None
    """
    t = text.strip()

    patterns = [
        r"([가-힣a-zA-Z0-9\+\- ]{2,30})\s*(들어간|함유|성분|포함)",
        r"(?:with|contains)\s*([a-zA-Z0-9\+\- ]{2,30})",
    ]

    for pat in patterns:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            cand = m.group(1).strip()
            cand = re.sub(r"\s{2,}", " ", cand)
            # 너무 길면 컷
            if 2 <= len(cand) <= 30:
                return cand
    return None


def parse_query(text: str) -> dict:
    """
    질문 1줄 -> 내부 조건 JSON
    """
    return {
        "query_text": text,
        "skin_type": extract_skin_type(text),          # dry/oily/combination/None
        "product_type": extract_product_type(text),    # cream/serum/.../None
        "ingredient": extract_ingredient(text),        # "판테놀" 같은 값 또는 None
    }
