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

# Small, deliberately bounded nudges for optional personalization (see
# retrieve()'s interests/skill_level params) — a ranking BOOST among
# otherwise-similar-relevance results, never a filter and never large
# enough to override genuine semantic relevance (scores are clamped to
# [0, 1], and a real relevance gap between two results is almost always
# bigger than either boost alone).
_INTEREST_BOOST = 0.03
_SKILL_LEVEL_BOOST = 0.03


def _split(value: str) -> list[str]:
    return [v for v in (value or "").split(",") if v]


class Retriever:
    """Thin wrapper over the configured vector store (Chroma or FAISS)."""

    def __init__(self):
        self.provider = settings.vector_store_provider
        self._client = None
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
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
            # Deliberately NOT cached as a permanent "missing" flag — a real
            # incident hit this: the collection lookup failed once (a
            # transient lock/race with another process touching the same
            # Chroma store, or the server starting a moment before
            # `python -m app.rag.index_builder` had finished), and every
            # search for the rest of that server process's life silently
            # returned [] forever, with no way to recover short of a manual
            # restart — indistinguishable from "search is just broken" to a
            # user. Retrying on the next call instead means a transient
            # failure heals itself as soon as the real cause clears, at the
            # cost of one cheap extra get_collection() call per retrieve()
            # while it's still down.
            logger.warning(
                "Chroma collection %r not available right now (no results "
                "until `python -m app.rag.index_builder` has run, or until "
                "a transient error clears — will retry on the next search)",
                name,
            )
            return None
        return self._collection

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        interests: list[str] | None = None,
        skill_level: str | None = None,
    ) -> list[dict]:
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
                    # All nine share this handling — see
                    # app.rag.index_builder.ENRICHMENT_SCORE_FIELDS for the
                    # None-omission on the write side.
                    "resume_value_score": meta.get("resume_value_score"),
                    "industry_relevance_score": meta.get("industry_relevance_score"),
                    "technical_depth_score": meta.get("technical_depth_score"),
                    "novelty_score": meta.get("novelty_score"),
                    "dataset_availability_score": meta.get("dataset_availability_score"),
                    "hardware_requirement_score": meta.get("hardware_requirement_score"),
                    "competition_potential_score": meta.get("competition_potential_score"),
                    "social_impact_score": meta.get("social_impact_score"),
                    "feasibility_score": meta.get("feasibility_score"),
                    # Same "absent means unknown, never guessed" handling
                    # for the "New" badge's underlying date.
                    "first_seen_at": meta.get("first_seen_at") or None,
                }
            )

        # Optional personalization (see app.models.user.User.interests/
        # skill_level) — deliberately gated on "nothing was passed", not
        # just looping with no-op boosts, so an anonymous caller or a
        # logged-in user who never set either preference gets this exact
        # same `candidates` list back, in Chroma's own relevance order,
        # with zero extra work. That's what makes this byte-for-byte
        # identical to before this feature existed, not just "usually the
        # same" — there's no float addition or re-sort for either case to
        # accidentally perturb.
        if not interests and not skill_level:
            return candidates

        interests_set = set(interests or [])
        for candidate in candidates:
            boost = 0.0
            if interests_set and any(d in interests_set for d in candidate["domain"]):
                boost += _INTEREST_BOOST
            # candidate["difficulty"] is None for virtually every problem
            # today (see app.core.taxonomy.SKILL_LEVELS's docstring) — this
            # match just never fires yet, which is correct, not broken.
            if skill_level and candidate["difficulty"] and candidate["difficulty"].lower() == skill_level.lower():
                boost += _SKILL_LEVEL_BOOST
            if boost:
                candidate["score"] = min(1.0, candidate["score"] + boost)

        # A boost only ever nudges otherwise-similar-relevance results
        # above one another — it's always small relative to a genuine
        # relevance gap — so this re-sort can only reorder near-ties, never
        # promote a weak match over a strong one. Stable sort: candidates
        # that end up with equal scores keep Chroma's original relative
        # order rather than shuffling.
        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates
