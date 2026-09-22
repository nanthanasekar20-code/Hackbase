"""
Tests for the Chroma index builder + retriever wiring (Phase 3/4).

These use a tiny, deterministic, dependency-free fake embedding function
(word-overlap based) rather than the real sentence-transformers/spaCy
providers, so the tests run anywhere without needing model weights, a
network connection, or spaCy/sentence-transformers installed. What's under
test here is the *pipeline wiring* — build_index() populates a real Chroma
collection from data/processed/problems.json-shaped records, and
Retriever.retrieve() reads it back and shapes results correctly — not the
embedding model's semantic quality.
"""

import json

import pytest

from app.core.config import settings


class _FakeEmbeddingFunction:
    """Deterministic, network-free "embedding": one dimension per keyword,
    1.0 if the keyword appears in the text (case-insensitive), else 0.0.
    Real enough to produce meaningfully different vectors for different
    text and to rank obviously-relevant documents above irrelevant ones,
    without depending on any real model."""

    KEYWORDS = [
        "ai", "agriculture", "computer", "vision", "blockchain",
        "healthcare", "education", "water", "crop", "farmer",
    ]

    def __call__(self, input):
        out = []
        for text in input:
            lowered = text.lower()
            out.append([1.0 if kw in lowered else 0.0 for kw in self.KEYWORDS])
        return out


@pytest.fixture
def rag_env(tmp_path, monkeypatch):
    """Points the index builder + retriever at an isolated tmp Chroma dir
    and a small fixture corpus, using the fake embedding function above."""
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    problems = [
        {
            "id": "sih:p1",
            "title": "AI Crop Disease Detection",
            "summary": "Use computer vision and AI to detect crop diseases from farmer photos.",
            "source": "sih",
            "hackathon_name": "SIH 2025",
            "domain": ["AI/ML", "Agriculture"],
            "technologies": ["Python", "OpenCV"],
            "skills": [],
            "difficulty": None,
        },
        {
            "id": "sih:p2",
            "title": "Blockchain Supply Chain Tracker",
            "summary": "A blockchain based ledger for tracking pharmaceutical supply chains.",
            "source": "sih",
            "hackathon_name": "SIH 2025",
            "domain": ["Blockchain & Web3"],
            "technologies": ["Solidity"],
            "skills": [],
            "difficulty": None,
            "resume_value_score": 8.5,
            "industry_relevance_score": 7.0,
            "technical_depth_score": 9.0,
        },
        {
            "id": "campus:p3",
            "title": "Rural Healthcare Access Platform",
            "summary": "Telemedicine platform improving healthcare access in rural water-scarce regions.",
            "source": "campus",
            "hackathon_name": "Code Coalescence 2025",
            "domain": ["Healthcare"],
            "technologies": [],
            "skills": [],
            "difficulty": None,
        },
    ]
    (processed_dir / "problems.json").write_text(json.dumps(problems), encoding="utf-8")

    monkeypatch.setattr(settings, "chroma_persist_dir", str(tmp_path / "chroma"))

    import app.rag.index_builder as index_builder
    import app.rag.retriever as retriever

    monkeypatch.setattr(index_builder, "PROCESSED_PATH", processed_dir / "problems.json")
    # Patch the names as imported into each module (`from ... import ...`
    # binds a local reference at import time), not the embeddings module
    # itself — patching the source module alone wouldn't affect these
    # already-bound references and would silently fall through to the
    # real (network-dependent) sentence-transformers provider.
    monkeypatch.setattr(index_builder, "get_embedding_function", lambda: _FakeEmbeddingFunction())
    monkeypatch.setattr(index_builder, "collection_name", lambda: "test_collection")
    monkeypatch.setattr(retriever, "get_embedding_function", lambda: _FakeEmbeddingFunction())
    monkeypatch.setattr(retriever, "collection_name", lambda: "test_collection")

    return index_builder, retriever


def test_build_index_populates_collection_from_processed_corpus(rag_env):
    index_builder, _ = rag_env
    count = index_builder.build_index()
    assert count == 3


def test_retriever_returns_relevant_results_after_index_build(rag_env):
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()
    results = r.retrieve("AI agriculture computer vision", top_k=3)

    assert len(results) == 3
    # The AI/agriculture/computer-vision problem should rank first.
    assert results[0]["id"] == "sih:p1"
    assert results[0]["score"] > results[-1]["score"]


def test_retriever_result_shape_matches_ranked_result_fields(rag_env):
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()
    results = r.retrieve("blockchain", top_k=1)

    assert results, "expected at least one result"
    top = results[0]
    assert top["id"] == "sih:p2"
    assert isinstance(top["domain"], list)
    assert top["domain"] == ["Blockchain & Web3"]
    assert isinstance(top["technologies"], list)
    assert isinstance(top["score"], float)
    assert top["title"] == "Blockchain Supply Chain Tracker"


def test_retriever_passes_through_resume_value_scores_when_present(rag_env):
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()
    results = r.retrieve("blockchain", top_k=1)

    top = results[0]
    assert top["id"] == "sih:p2"
    assert top["resume_value_score"] == 8.5
    assert top["industry_relevance_score"] == 7.0
    assert top["technical_depth_score"] == 9.0


def test_retriever_leaves_resume_value_scores_none_when_never_scored(rag_env):
    # sih:p1 in the fixture corpus above has no resume_value_score key at
    # all (not yet run through scripts/enrich_resume_value.py) — must come
    # back as None, never a fabricated 0 or omitted key that would crash a
    # caller expecting it.
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()
    results = r.retrieve("AI agriculture", top_k=3)

    p1 = next(r for r in results if r["id"] == "sih:p1")
    assert p1["resume_value_score"] is None
    assert p1["industry_relevance_score"] is None
    assert p1["technical_depth_score"] is None


def test_retriever_returns_empty_list_when_no_index_built(tmp_path, monkeypatch):
    """No build_index() call happened -> the collection doesn't exist yet.
    This must degrade gracefully to [], not raise."""
    monkeypatch.setattr(settings, "chroma_persist_dir", str(tmp_path / "chroma_empty"))

    import app.rag.retriever as retriever

    monkeypatch.setattr(retriever, "get_embedding_function", lambda: _FakeEmbeddingFunction())
    monkeypatch.setattr(retriever, "collection_name", lambda: "nonexistent_collection")

    r = retriever.Retriever()
    assert r.retrieve("anything", top_k=5) == []


def test_retriever_returns_empty_list_for_blank_query(rag_env):
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()
    assert r.retrieve("", top_k=5) == []
    assert r.retrieve("   ", top_k=5) == []
