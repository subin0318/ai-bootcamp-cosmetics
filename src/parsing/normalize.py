import json
from pathlib import Path

_ALIAS_PATH = Path("data/dictionaries/ingredient_alias.json")


def load_ingredient_alias():
    with open(_ALIAS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def expand_ingredient_terms(user_term: str, alias_map: dict) -> list[str]:
    t = user_term.strip().lower()

    # 1) 표준키로 직접 들어온 경우
    if t in alias_map:
        return [x.lower() for x in alias_map[t]]

    # 2) alias를 역으로 찾아서 표준키 찾기
    for canonical, aliases in alias_map.items():
        aliases_lower = [a.lower() for a in aliases]
        if t in aliases_lower:
            return aliases_lower

    # 3) 못 찾으면 그대로
    return [t]
