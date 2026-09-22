from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import auth, favorites, health, search, plan, tracking

_BACKEND_DIR = Path(__file__).resolve().parents[1]  # app/main.py -> app/ -> backend/


def _run_migrations() -> None:
    """
    Applies any pending Alembic migrations (see migrations/) on startup,
    bringing the configured database (settings.database_url) up to date —
    real schema history with upgrade/downgrade support, not just
    Base.metadata.create_all()'s "create tables that don't exist yet".
    Absolute paths so this works regardless of the process's cwd.
    """
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


_run_migrations()

app = FastAPI(title="HackBase API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(search.router, prefix=settings.api_prefix, tags=["search"])
app.include_router(plan.router, prefix=settings.api_prefix, tags=["plan"])
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(favorites.router, prefix=settings.api_prefix)
app.include_router(tracking.router, prefix=settings.api_prefix, tags=["tracking"])


@app.get("/")
def root():
    return {"service": "HackBase API", "status": "running"}
