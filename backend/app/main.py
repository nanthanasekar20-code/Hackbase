from pathlib import Path

from alembic import command
from alembic.config import Config
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import auth, favorites, health, live_hackathons, problems, search, plan, tracking

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
app.include_router(live_hackathons.router, prefix=settings.api_prefix, tags=["live-hackathons"])
app.include_router(problems.router, prefix=settings.api_prefix, tags=["problems"])


# --- Live hackathon recommendations (see app/services/refresh_job.py) ---
# Runs the scrape -> rebuild -> reindex pipeline on a timer instead of
# requiring someone to run scripts/run_scrapers.py, scripts/build_corpus.py
# and `python -m app.rag.index_builder` by hand. First run fires one
# interval after startup, not immediately, so a restart doesn't always
# kick off a scrape. Disable with AUTO_REFRESH_ENABLED=false in .env (e.g.
# for local dev where you don't want a background job periodically hitting
# scraper sites).
_scheduler = BackgroundScheduler()

if settings.auto_refresh_enabled:
    from app.services.refresh_job import run_refresh

    _scheduler.add_job(
        run_refresh,
        "interval",
        hours=settings.auto_refresh_interval_hours,
        id="refresh_dataset",
        # Don't pile up overlapping runs if one refresh (a slow scrape) is
        # still going when the next is due.
        max_instances=1,
        coalesce=True,
    )

# --- Live Hackathons feed (see app/services/live_hackathons_job.py) ---
# A second, separate scheduled job — refreshes data/processed/
# live_hackathons.json (hackathon name/source/official-link, scraped from
# 10 external platforms) on its own timer. Deliberately independent from
# the problem-corpus refresh job above: different data, different sites,
# different schedule — one's settings/failures never affect the other.
# Disable with LIVE_HACKATHONS_REFRESH_ENABLED=false in .env.
if settings.live_hackathons_refresh_enabled:
    from app.services.live_hackathons_job import run_live_hackathons_refresh

    _scheduler.add_job(
        run_live_hackathons_refresh,
        "interval",
        hours=settings.live_hackathons_refresh_interval_hours,
        id="refresh_live_hackathons",
        max_instances=1,
        coalesce=True,
    )

if settings.auto_refresh_enabled or settings.live_hackathons_refresh_enabled:
    _scheduler.start()


@app.on_event("shutdown")
def _shutdown_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


@app.get("/")
def root():
    return {"service": "HackBase API", "status": "running"}
