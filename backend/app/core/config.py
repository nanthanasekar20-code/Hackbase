from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    # "gemini-flash-latest" is Google's generic alias for the newest Flash
    # model release, so this doesn't need bumping by hand as new model
    # versions ship — see https://ai.google.dev/gemini-api/docs/models.
    gemini_model_name: str = "gemini-flash-latest"
    # SQLite by default — zero setup, no server to install/run. Swap to a
    # real postgresql:// URL in .env for production; app/db/session.py
    # handles both transparently.
    database_url: str = "sqlite:///./hackbase.db"

    # --- Auth (see app/core/security.py) ---
    # CHANGE THIS in .env for any real deployment — this default is only
    # safe for local dev. Generate a real one with:
    #   python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret_key: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    vector_store_provider: str = "chroma"
    chroma_persist_dir: str = "./data/processed/chroma"

    # --- Embeddings (see app/rag/embeddings.py) ---
    # "sentence-transformers" (default) is a locally-run sentence-transformer
    # model — best quality, no API key, but downloads its weights from
    # huggingface.co the first time it runs. "spacy" is a fully-local
    # fallback (averaged word vectors) for environments where
    # huggingface.co is unreachable, since its model installs as a normal
    # pip package with no runtime download. Each provider writes to its own
    # named Chroma collection, so switching providers never silently mixes
    # incompatible embedding spaces — see app/rag/embeddings.collection_name().
    embedding_provider: str = "sentence-transformers"
    sentence_transformer_model: str = "all-MiniLM-L6-v2"
    spacy_model_name: str = "en_core_web_md"

    mlflow_tracking_uri: str = "./mlflow"

    app_env: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- Data pipeline ---
    # Year suffix for the live SIH problem-statement release, e.g.
    # https://sih.gov.in/sih2025PS. Bump this each year SIH publishes a
    # new release.
    sih_year: str = "2025"


settings = Settings()
