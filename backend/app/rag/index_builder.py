"""
Builds the vector index from the processed hackathon problem-statement
corpus.

Pipeline:
    data/raw/*        -> scrapers               (see app/scrapers/)
    data/processed/*  -> cleaned + tagged docs   (see app/ingestion/clean.py,
                                                    scripts/build_corpus.py)
    Chroma index       -> written here, to settings.chroma_persist_dir

Run as: python -m app.rag.index_builder

Each run does a full rebuild of the configured provider's collection (see
app/rag/embeddings.collection_name()) from data/processed/problems.json, so
the index always exactly matches the current processed corpus — no stale
entries left behind from a previous run with different data.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import settings
from app.rag.embeddings import collection_name, get_embedding_function, resolve_chroma_dir

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# index_builder.py lives at <project_root>/backend/app/rag/index_builder.py
# -> parents[0]=rag, [1]=app, [2]=backend, [3]=<project_root>. (One level
# deeper than scripts/build_corpus.py, which only needs parents[2] to reach
# the same project root from <project_root>/backend/scripts/.)
ROOT = Path(__file__).resolve().parents[3]
PROCESSED_PATH = ROOT / "data" / "processed" / "problems.json"

BATCH_SIZE = 200


def _load_processed() -> list[dict]:
    if not PROCESSED_PATH.exists():
        raise FileNotFoundError(
            f"{PROCESSED_PATH} does not exist — run `python scripts/build_corpus.py` "
            "first to build the processed corpus from raw/seed data."
        )
    data = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    if not data:
        raise ValueError(
            f"{PROCESSED_PATH} is empty — the corpus has no problems to index."
        )
    return data


def _embed_text(problem: dict) -> str:
    """The text actually embedded per problem: title + summary carries the
    real semantic content without the full (often long) problem statement,
    which keeps embedding fast and avoids diluting the vector with
    boilerplate sections (constraints, submission instructions, etc.)."""
    title = problem.get("title", "")
    summary = problem.get("summary", "")
    return f"{title}. {summary}".strip()


RESUME_VALUE_FIELDS = ("resume_value_score", "industry_relevance_score", "technical_depth_score")


def _metadata(problem: dict) -> dict:
    """Chroma metadata values must be str/int/float/bool (no lists/None),
    so list fields are joined into comma-separated strings here and parsed
    back out in the retriever."""
    metadata = {
        "title": problem.get("title") or "",
        "source": problem.get("source") or "",
        "hackathon_name": problem.get("hackathon_name") or "",
        "domain": ",".join(problem.get("domain") or []),
        "technologies": ",".join(problem.get("technologies") or []),
        "skills": ",".join(problem.get("skills") or []),
        "difficulty": problem.get("difficulty") or "",
        "summary": problem.get("summary") or "",
    }
    # Resume Value enrichment scores (scripts/enrich_resume_value.py) — a
    # problem that hasn't been scored yet has these as None, and Chroma
    # metadata can't hold None, so the key is omitted entirely rather than
    # written as a fake 0. The retriever reads it back with plain dict.get,
    # which is already None-safe for a missing key.
    for field in RESUME_VALUE_FIELDS:
        value = problem.get(field)
        if value is not None:
            metadata[field] = float(value)
    return metadata


def build_index():
    import chromadb

    problems = _load_processed()
    name = collection_name()
    ef = get_embedding_function()

    chroma_dir = resolve_chroma_dir()
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))

    # Full rebuild: drop any existing collection under this name so the
    # index never carries stale records from a prior run.
    try:
        client.delete_collection(name)
        logger.info("dropped existing collection %r before rebuild", name)
    except Exception:
        pass  # didn't exist yet — nothing to drop

    collection = client.create_collection(
        name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [p["id"] for p in problems]
    documents = [_embed_text(p) for p in problems]
    metadatas = [_metadata(p) for p in problems]

    for start in range(0, len(problems), BATCH_SIZE):
        end = start + BATCH_SIZE
        collection.add(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
        logger.info("indexed %d/%d", min(end, len(problems)), len(problems))

    logger.info(
        "built collection %r (provider=%s) with %d documents at %s",
        name,
        settings.embedding_provider,
        collection.count(),
        chroma_dir,
    )
    return collection.count()


if __name__ == "__main__":
    build_index()
