"""
Thin wrapper over the configured vector store (Chroma), used by
app.agents.search_agent.SearchAgent.

The Chroma client/collection are opened lazily on first use (not at import
time), and a missing/empty collection is treated as "no results yet" rather
than a crash — run `python -m app.rag.index_builder` to populate it from
data/processed/problems.json.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.rag.embeddings import collection_name, get_embedding_function, resolve_chroma_dir

logger = logging.getLogger(__name__)


def _split(value: str) -> list[str]:
    return [v for v in (value or "").split(",") if v]


class Retriever:
    """Thin wrapper over the configured vector store (Chroma or FAISS)."""

    def __init__(self):
        self.provider = settings.vector_store_provider
        self._client = None
        self._collection = None
        self._collection_missing = False

    def _get_collection(self):
        if self._collection is not None or self._collection_missing:
            return self._collection

        import chromadb

        if self._client is None:
            self._client = chromadb.PersistentClient(path=str(resolve_chroma_dir()))

        name = collection_name()
        try:
            self._collection = self._client.get_collection(
                name, embedding_function=get_embedding_function()
            )
        except Exception:
            logger.warning(
                "Chroma collection %r does not exist yet (no results until "
                "`python -m app.rag.index_builder` is run)",
                name,
            )
            self._collection_missing = True
            return None
        return self._collection

    def retrieve(self, query: str, top_k: int = 10) -> list[dict]:
        if not query or not query.strip():
            return []

        collection = self._get_collection()
        if collection is None or collection.count() == 0:
            return []

        result = collection.query(query_texts=[query], n_results=top_k)

        ids = result.get("ids", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        candidates = []
        for doc_id, meta, distance in zip(ids, metadatas, distances):
            # Cosine distance in [0, 2] (0 = identical) -> a 0..1 relevance
            # score where higher is more relevant, clamped for safety.
            score = max(0.0, min(1.0, 1.0 - distance))
            candidates.append(
                {
                    "id": doc_id,
                    "title": meta.get("title", ""),
                    "source": meta.get("source", ""),
                    "hackathon_name": meta.get("hackathon_name") or None,
                    "domain": _split(meta.get("domain", "")),
                    "technologies": _split(meta.get("technologies", "")),
                    "skills": _split(meta.get("skills", "")),
                    "difficulty": meta.get("difficulty") or None,
                    "summary": meta.get("summary", ""),
                    "score": score,
                    # Absent (never scored) -> dict.get returns None, which
                    # matches the Optional[float] fields on RankedResult.
                    "resume_value_score": meta.get("resume_value_score"),
                    "industry_relevance_score": meta.get("industry_relevance_score"),
                    "technical_depth_score": meta.get("technical_depth_score"),
                }
            )
        return candidates
