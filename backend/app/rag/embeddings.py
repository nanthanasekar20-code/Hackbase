"""
Embedding function factory for the vector index.

Two providers are supported, selected via `settings.embedding_provider`:

- "sentence-transformers" (default): a locally-run sentence-transformer
  model (settings.sentence_transformer_model, default "all-MiniLM-L6-v2").
  Best quality, no API key required — but it downloads its weights from
  huggingface.co the first time it runs, so it needs that host to be
  reachable at least once.
- "spacy": locally-run averaged word vectors (settings.spacy_model_name,
  default "en_core_web_md"). Lower semantic quality than a trained
  sentence encoder, but a genuine fallback for environments where
  huggingface.co is unreachable — spaCy's model installs as a normal
  package (via pip / spaCy's own GitHub release), so no runtime download
  is needed at query/index time at all.

Both are real, deterministic, local models — never an API call, never a
random/fabricated vector. Each provider resolves to its own named Chroma
collection (see collection_name()) so switching `embedding_provider` can
never silently mix vectors from two different embedding spaces in the same
collection — you either query a matching, populated collection, or an
empty-but-correctly-named one (never garbage results from a mismatch).
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import settings

# embeddings.py lives at <project_root>/backend/app/rag/embeddings.py, the
# same depth as index_builder.py -> parents[3] is <project_root>.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def resolve_chroma_dir() -> Path:
    """
    settings.chroma_persist_dir defaults to a relative path
    ("./data/processed/chroma"); resolving it against the current working
    directory (the naive default) means the index silently lands in a
    different place depending on where the process happens to be launched
    from — e.g. inside backend/data/... if uvicorn is started from
    backend/, disconnected from the project's real top-level data/
    directory where data/processed/problems.json actually lives. Always
    resolving relative paths against the project root keeps the index
    builder and the retriever (and any launch directory) pointed at the
    same, correct location. An absolute path in settings is left as-is.
    """
    p = Path(settings.chroma_persist_dir)
    return p if p.is_absolute() else PROJECT_ROOT / p


def collection_name() -> str:
    """
    A collection name that encodes exactly which model produced its
    vectors. Used by both the index builder and the retriever so they
    always agree on which collection to read/write.
    """
    if settings.embedding_provider == "spacy":
        return f"hackbase_problems__spacy__{settings.spacy_model_name}"
    return f"hackbase_problems__st__{settings.sentence_transformer_model}"


def get_embedding_function():
    """
    Returns a chromadb-compatible embedding function for the currently
    configured provider (an object implementing
    __call__(list[str]) -> list[list[float]]).
    """
    if settings.embedding_provider == "spacy":
        return _SpacyEmbeddingFunction(settings.spacy_model_name)

    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    return SentenceTransformerEmbeddingFunction(model_name=settings.sentence_transformer_model)


class _SpacyEmbeddingFunction:
    """
    Chroma embedding function backed by spaCy's static word vectors
    (mean-pooled per document by spaCy itself via Doc.vector). Real,
    local, deterministic — used as the fallback provider when
    huggingface.co is unreachable.
    """

    def __init__(self, model_name: str):
        import spacy

        # Only the vectors are needed; excluding the rest of the pipeline
        # (tagger/parser/ner/...) makes loading and encoding much faster.
        self._nlp = spacy.load(
            model_name,
            exclude=["tagger", "parser", "ner", "lemmatizer", "attribute_ruler"],
        )

    def __call__(self, input):  # noqa: A002 - chromadb's EmbeddingFunction protocol names this `input`
        return [self._nlp(text).vector.tolist() for text in input]
