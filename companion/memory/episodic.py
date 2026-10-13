import asyncio
import time
import uuid
from pathlib import Path

import chromadb

HALF_LIFE_DAYS = 14.0  # a routine memory loses half its weight in two weeks


class EpisodicMemory:
    def __init__(self, path: str | Path = "data/chroma") -> None:
        Path(path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(path))
        self._col = self._client.get_or_create_collection(
            "episodes", metadata={"hnsw:space": "cosine"}
        )

    def add(self, text: str, importance: float = 0.5, kind: str = "conversation") -> str:
        """importance: 0.0 (routine) to 1.0 (high-impact, decays much slower)."""
        mem_id = uuid.uuid4().hex
        self._col.add(
            ids=[mem_id],
            documents=[text],
            metadatas=[{"ts": time.time(), "importance": float(importance), "kind": kind}],
        )
        return mem_id

    def search(self, query: str, k: int = 5, pool: int = 20) -> list[dict]:
        """Semantic search, re-ranked so recent or important memories win."""
        count = self._col.count()
        if count == 0:
            return []
        res = self._col.query(query_texts=[query], n_results=min(pool, count))
        now = time.time()
        scored = []
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            similarity = 1.0 - dist
            age_days = (now - meta["ts"]) / 86400
            half_life = HALF_LIFE_DAYS * (1 + 3 * meta["importance"])
            decay = 0.5 ** (age_days / half_life)
            scored.append({
                "text": doc,
                "score": similarity * decay,
                "similarity": similarity,
                "age_days": age_days,
                **meta,
            })
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:k]

    # Chroma is synchronous, so these keep the event loop (and voice) from blocking.
    async def aadd(self, *args, **kwargs) -> str:
        return await asyncio.to_thread(self.add, *args, **kwargs)

    async def asearch(self, *args, **kwargs) -> list[dict]:
        return await asyncio.to_thread(self.search, *args, **kwargs)