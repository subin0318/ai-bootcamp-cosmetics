from typing import List, Dict


def filter_products(
    products: List[Dict],
    skin_type: str,
    ingredient_terms: list[str],
    product_type: str,
    budget_krw_max: int | None = None,
):
    result = []

    for p in products:
        if p.get("category") != product_type:
            continue

        if skin_type not in (p.get("skin_type") or []):
            continue

        ing_raw = (p.get("ingredients_raw") or "").lower()
        if not any(term.lower() in ing_raw for term in ingredient_terms):
            continue

        if budget_krw_max is not None:
            price = p.get("price_krw")
            if isinstance(price, int) and price > budget_krw_max:
                continue

        result.append(p)

    return result
