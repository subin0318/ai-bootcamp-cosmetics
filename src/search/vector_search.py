import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class VectorSearcher:
    def __init__(self, index_path="indexes/faiss.index", id_map_path="indexes/id_map.json"):
        self.index = faiss.read_index(str(index_path))
        with open(Path(id_map_path), "r", encoding="utf-8") as f:
            self.id_map = json.load(f)
        self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    def search(self, query_text: str, top_k: int = 10):
        q_emb = self.model.encode([query_text], normalize_embeddings=True)
        q_emb = np.asarray(q_emb, dtype="float32")

        scores, idxs = self.index.search(q_emb, top_k)
        scores = scores[0].tolist()
        idxs = idxs[0].tolist()

        results = []
        for score, ix in zip(scores, idxs):
            if ix == -1:
                continue
            results.append({"product_id": self.id_map[ix], "score": float(score)})
        return results
