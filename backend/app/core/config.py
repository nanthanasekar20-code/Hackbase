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

    # --- Live refresh (see app/services/refresh_job.py) ---
    # When enabled, a background job runs scripts/run_scrapers.py ->
    # scripts/build_corpus.py -> app/rag/index_builder.py on a timer
    # instead of requiring someone to run those three scripts by hand.
    # On by default; set to false in .env for local dev if you don't want
    # a background job periodically hitting scraper sites and rebuilding
    # the index. Deliberately does NOT include the Gemini resume-value
    # enrichment pass — see refresh_job.py's docstring for why that stays
    # a lazy, per-save trigger instead (app/api/routes/favorites.py).
    auto_refresh_enabled: bool = True
    auto_refresh_interval_hours: int = 24

    # --- Live Hackathons refresh (see app/services/live_hackathons_job.py) ---
    # A separate, unrelated background job — refreshes
    # data/processed/live_hackathons.json (hackathon name/source/link,
    # scraped from external platforms) on its own timer. Nothing here
    # touches the problem-statement corpus or its own refresh job above.
    live_hackathons_refresh_enabled: bool = True
    live_hackathons_refresh_interval_hours: int = 6

    # --- Email (password reset — see app/core/email.py) ---
    # Blank host means "not configured": forgot-password requests then fail
    # with a clear 503 instead of silently pretending an email was sent.
    # Any real SMTP provider works (Gmail with an app password, SendGrid,
    # Mailgun's SMTP endpoint, etc.).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    # Where the emailed reset link points — the Vite dev server by default.
    frontend_base_url: str = "http://localhost:5173"


settings = Settings()
