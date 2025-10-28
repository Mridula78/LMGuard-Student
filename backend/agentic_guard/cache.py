import hashlib
from typing import Dict, Optional, List
from collections import OrderedDict

import numpy as np

from deps import config


class EmbeddingCache:
    def __init__(self, max_items: int = None):
        self.max_items = max_items or config.CACHE_MAX_ITEMS
        self.cache: OrderedDict[str, Dict] = OrderedDict()
        self.embeddings: Dict[str, List[float]] = {}

    def _compute_key(self, embedding: List[float]) -> str:
        rounded = [round(x, 4) for x in embedding]
        key_str = str(rounded)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _cosine_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        arr1 = np.array(emb1)
        arr2 = np.array(emb2)
        denom = (np.linalg.norm(arr1) * np.linalg.norm(arr2)) or 1.0
        return float(np.dot(arr1, arr2) / denom)

    def add(self, embedding: List[float], decision: Dict, timestamp: str) -> None:
        key = self._compute_key(embedding)
        if len(self.cache) >= self.max_items:
            oldest_key = next(iter(self.cache))
            self.cache.pop(oldest_key, None)
            self.embeddings.pop(oldest_key, None)

        self.cache[key] = {"decision": decision, "timestamp": timestamp}
        self.embeddings[key] = embedding
        self.cache.move_to_end(key)

    def query(self, embedding: List[float], threshold: float = 0.88) -> Optional[Dict]:
        best_key = None
        best_score = threshold
        for key, emb in self.embeddings.items():
            score = self._cosine_similarity(embedding, emb)
            if score > best_score:
                best_score = score
                best_key = key
        if best_key is not None:
            self.cache.move_to_end(best_key)
            return self.cache[best_key]["decision"]
        return None


embedding_cache = EmbeddingCache()


