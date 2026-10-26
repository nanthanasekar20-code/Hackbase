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
            "novelty_score": 6.5,
            "dataset_availability_score": 4.0,
            "hardware_requirement_score": 2.0,
            "competition_potential_score": 7.5,
            "social_impact_score": 8.0,
            "feasibility_score": 9.5,
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


def test_retriever_passes_through_the_six_newer_enrichment_scores_when_present(rag_env):
    """novelty_score/dataset_availability_score/hardware_requirement_score/
    competition_potential_score/social_impact_score/feasibility_score —
    added alongside the original three, same None-omission handling."""
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()
    results = r.retrieve("blockchain", top_k=1)

    top = results[0]
    assert top["id"] == "sih:p2"
    assert top["novelty_score"] == 6.5
    assert top["dataset_availability_score"] == 4.0
    assert top["hardware_requirement_score"] == 2.0
    assert top["competition_potential_score"] == 7.5
    assert top["social_impact_score"] == 8.0
    assert top["feasibility_score"] == 9.5


def test_retriever_leaves_the_six_newer_enrichment_scores_none_when_never_scored(rag_env):
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()
    results = r.retrieve("AI agriculture", top_k=3)

    p1 = next(r for r in results if r["id"] == "sih:p1")
    assert p1["novelty_score"] is None
    assert p1["dataset_availability_score"] is None
    assert p1["hardware_requirement_score"] is None
    assert p1["competition_potential_score"] is None
    assert p1["social_impact_score"] is None
    assert p1["feasibility_score"] is None


def test_enrichment_score_fields_constant_matches_enrichment_scripts_score_fields():
    """index_builder.ENRICHMENT_SCORE_FIELDS is defined independently from
    scripts/enrich_resume_value.SCORE_FIELDS (by design — see both
    modules' docstrings on why they don't share an import) and must be
    kept in sync by hand, same risk as build_corpus.RESUME_VALUE_FIELDS."""
    import app.rag.index_builder as index_builder
    from scripts.enrich_resume_value import SCORE_FIELDS

    assert set(index_builder.ENRICHMENT_SCORE_FIELDS) == set(SCORE_FIELDS)


def test_retriever_returns_empty_list_when_no_index_built(tmp_path, monkeypatch):
    """No build_index() call happened -> the collection doesn't exist yet.
    This must degrade gracefully to [], not raise."""
    monkeypatch.setattr(settings, "chroma_persist_dir", str(tmp_path / "chroma_empty"))

    import app.rag.retriever as retriever

    monkeypatch.setattr(retriever, "get_embedding_function", lambda: _FakeEmbeddingFunction())
    monkeypatch.setattr(retriever, "collection_name", lambda: "nonexistent_collection")

    r = retriever.Retriever()
    assert r.retrieve("anything", top_k=5) == []


def test_retriever_recovers_after_a_transient_collection_lookup_failure(rag_env):
    """Regression test for a real incident: a Retriever instance is a
    long-lived singleton (app.agents.search_agent.search_agent), so if its
    very first collection lookup fails for any transient reason (a lock
    race with another process touching the same Chroma store, or the
    server starting a moment before index_builder finished), it must not
    get stuck returning [] for every search for the rest of that process's
    life — the next call has to retry, not reuse a cached "missing" verdict."""
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()

    # Simulate the first lookup hitting a transient failure by pointing the
    # client at a Retriever that hasn't built its client yet, then forcing
    # one failing get_collection() call before letting the real one through.
    import chromadb

    original_persistent_client = chromadb.PersistentClient
    call_count = {"n": 0}

    class _FlakyClient:
        def __init__(self, *args, **kwargs):
            self._real = original_persistent_client(*args, **kwargs)

        def get_collection(self, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("simulated transient Chroma lookup failure")
            return self._real.get_collection(*args, **kwargs)

    chromadb.PersistentClient = _FlakyClient
    try:
        # First call: the simulated failure -> empty, not an exception.
        assert r.retrieve("blockchain", top_k=1) == []
        # Second call on the SAME Retriever instance: must retry and
        # recover, not keep returning [] forever from a cached failure.
        results = r.retrieve("blockchain", top_k=1)
        assert len(results) == 1
        assert results[0]["id"] == "sih:p2"
    finally:
        chromadb.PersistentClient = original_persistent_client


def test_retriever_returns_empty_list_for_blank_query(rag_env):
    index_builder, retriever = rag_env
    index_builder.build_index()

    r = retriever.Retriever()
    assert r.retrieve("", top_k=5) == []
    assert r.retrieve("   ", top_k=5) == []


# --- Optional personalization (app.models.user.User.interests/
# skill_level) — a ranking BOOST among near-ties, never a filter. See
# retrieve()'s docstring comment for why the no-personalization path must
# be byte-for-byte identical to the pre-personalization behavior above.


def test_retrieve_with_no_personalization_is_identical_to_omitting_the_params(rag_env):
    index_builder, retriever = rag_env
    index_builder.build_index()
    r = retriever.Retriever()

    plain = r.retrieve("AI agriculture computer vision", top_k=3)
    explicit_none = r.retrieve("AI agriculture computer vision", top_k=3, interests=None, skill_level=None)
    explicit_empty = r.retrieve("AI agriculture computer vision", top_k=3, interests=[], skill_level="")

    assert plain == explicit_none == explicit_empty


class _FakeCollection:
    """A canned Chroma collection — lets the boost math itself be tested
    with exact, controlled relevance gaps, instead of depending on
    _FakeEmbeddingFunction's keyword overlap happening to produce a
    particular distance."""

    def __init__(self, ids, metadatas, distances):
        self._ids = ids
        self._metadatas = metadatas
        self._distances = distances

    def count(self):
        return len(self._ids)

    def query(self, query_texts, n_results):
        return {"ids": [self._ids], "metadatas": [self._metadatas], "distances": [self._distances]}


def _retriever_with_fake_collection(ids, metadatas, distances):
    import app.rag.retriever as retriever_module

    r = retriever_module.Retriever()
    r._collection = _FakeCollection(ids, metadatas, distances)
    return r


def _meta(domain="", difficulty=""):
    return {"title": "x", "source": "sih", "domain": domain, "technologies": "", "skills": "", "difficulty": difficulty}


def test_interest_match_boosts_a_result_above_a_near_tie():
    # a is very slightly more relevant than b before any boost (score gap
    # 0.01, well under the 0.03 boost) — b's domain matches the caller's
    # interests, a's doesn't.
    r = _retriever_with_fake_collection(
        ["a", "b"],
        [_meta(domain="Healthcare"), _meta(domain="FinTech")],
        [0.20, 0.21],
    )

    plain = r.retrieve("query", top_k=2)
    assert [c["id"] for c in plain] == ["a", "b"]

    boosted = r.retrieve("query", top_k=2, interests=["FinTech"])
    assert [c["id"] for c in boosted] == ["b", "a"]


def test_skill_level_match_boosts_a_result_above_a_near_tie():
    r = _retriever_with_fake_collection(
        ["a", "b"],
        [_meta(difficulty="advanced"), _meta(difficulty="beginner")],
        [0.20, 0.21],
    )

    boosted = r.retrieve("query", top_k=2, skill_level="beginner")
    assert [c["id"] for c in boosted] == ["b", "a"]
    # Matching is case-insensitive.
    boosted_upper = r.retrieve("query", top_k=2, skill_level="BEGINNER")
    assert [c["id"] for c in boosted_upper] == ["b", "a"]


def test_boost_never_overrides_a_genuine_relevance_gap():
    # a is much more relevant than b (score gap 0.40, far bigger than any
    # combination of the two boosts) — b matching every preference must
    # not be enough to leapfrog a.
    r = _retriever_with_fake_collection(
        ["a", "b"],
        [_meta(domain="Healthcare", difficulty="advanced"), _meta(domain="FinTech", difficulty="beginner")],
        [0.10, 0.50],
    )

    boosted = r.retrieve("query", top_k=2, interests=["FinTech"], skill_level="beginner")
    assert [c["id"] for c in boosted] == ["a", "b"]


def test_unscored_difficulty_never_matches_any_skill_level():
    """A problem whose difficulty was never set (None, not "") must not
    spuriously match an empty/falsy skill_level — skill_level is only
    ever a real value here since the route layer never forwards "" (see
    UserUpdate's clear-sentinel docstring), but the retriever itself
    should not special-case this into a match either."""
    r = _retriever_with_fake_collection(["a"], [_meta(difficulty="")], [0.20])

    results = r.retrieve("query", top_k=1, skill_level="beginner")
    assert results[0]["score"] == max(0.0, min(1.0, 1.0 - 0.20))  # unchanged — no boost applied


def test_no_candidate_domain_overlap_leaves_scores_unchanged():
    r = _retriever_with_fake_collection(
        ["a", "b"],
        [_meta(domain="Healthcare"), _meta(domain="FinTech")],
        [0.20, 0.21],
    )

    results = r.retrieve("query", top_k=2, interests=["Cybersecurity"])
    assert [c["id"] for c in results] == ["a", "b"]  # order unchanged — neither matched
