import json
import os
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def product_to_text(p: dict) -> str:
    # 벡터 검색에 쓸 텍스트(이 조합이 꽤 안정적임)
    name = p.get("name", "")
    category = p.get("category", "")
    ingredients = p.get("ingredients_raw", "")
    skin = " ".join(p.get("skin_type", []) or [])
    return f"{name} | {category} | {skin} | {ingredients}"


def main():
    products_path = Path("data/products/products.json")
    index_path = Path("indexes/faiss.index")
    id_map_path = Path("indexes/id_map.json")

    if not products_path.exists():
        raise FileNotFoundError(f"products.json not found: {products_path}")

    with open(products_path, "r", encoding="utf-8") as f:
        products = json.load(f)

    if not isinstance(products, list) or len(products) == 0:
        raise ValueError("products.json must be a non-empty list")

    os.makedirs("indexes", exist_ok=True)

    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    texts = [product_to_text(p) for p in products]
    embeddings = model.encode(texts, normalize_embeddings=True)
    embeddings = np.asarray(embeddings, dtype="float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine 유사도 = normalize + inner product
    index.add(embeddings)

    faiss.write_index(index, str(index_path))

    # 인덱스 row -> product_id 매핑 저장
    id_map = [p.get("id") for p in products]
    with open(id_map_path, "w", encoding="utf-8") as f:
        json.dump(id_map, f, ensure_ascii=False, indent=2)

    print("인덱스 생성 완료")
    print("제품 수:", len(products))
    print("벡터 차원:", dim)
    print("저장:", index_path)


if __name__ == "__main__":
    main()
