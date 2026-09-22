"""
Phase 7: real MLflow experiment tracking for Gemini-backed calls — the
Planning Agent (app.agents.planning_agent) and the Resume Value enrichment
script (scripts/enrich_resume_value.py).

Every call opens a real MLflow run under settings.mlflow_tracking_uri and
logs actual params/metrics from that call (latency, outcome, response
shape) — nothing here is simulated or pre-filled. Tracking is pure
observability, not a dependency the app can be blocked by: if mlflow isn't
installed, or a tracking call itself fails (e.g. the store is unwritable),
callers still run normally and get a no-op tracker instead of an error.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    # Reproduced on Windows: if mlflow is imported into a process before
    # onnxruntime (used by chromadb's default embedding function — see
    # app/rag/embeddings.py) has loaded its native module, onnxruntime's
    # subsequent import fails with "DLL load failed while importing
    # onnxruntime_pybind11_state" — a load-order conflict between mlflow's
    # dependencies and onnxruntime's native bindings, not a logic bug.
    # Importing onnxruntime first (if installed) avoids it regardless of
    # what order the rest of the app happens to import things in.
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        pass

    import mlflow

    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False


class _NullTracker:
    """Used when mlflow isn't installed or a run failed to start — every call is a no-op."""

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        pass

    def log_params(self, params: dict) -> None:
        pass

    def set_tag(self, key: str, value: str) -> None:
        pass


class _MlflowTracker:
    """Wraps the active mlflow run. Never lets a logging call raise into the caller."""

    def log_metric(self, key: str, value: float, step: int | None = None) -> None:
        try:
            mlflow.log_metric(key, value, step=step)
        except Exception:
            logger.exception("mlflow.log_metric(%r) failed", key)

    def log_params(self, params: dict) -> None:
        try:
            mlflow.log_params(params)
        except Exception:
            logger.exception("mlflow.log_params failed")

    def set_tag(self, key: str, value: str) -> None:
        try:
            mlflow.set_tag(key, value)
        except Exception:
            logger.exception("mlflow.set_tag(%r) failed", key)


_NULL_TRACKER = _NullTracker()

_MAX_ERROR_TAG_LENGTH = 5000

PLANNING_AGENT_EXPERIMENT = "planning_agent"
RESUME_VALUE_ENRICHMENT_EXPERIMENT = "resume_value_enrichment"
ARTICLE_INGEST_EXPERIMENT = "article_ingest"
TRACKED_EXPERIMENTS = (PLANNING_AGENT_EXPERIMENT, RESUME_VALUE_ENRICHMENT_EXPERIMENT, ARTICLE_INGEST_EXPERIMENT)


def _resolve_tracking_uri(uri: str) -> str:
    """
    Normalizes a local filesystem path (relative, e.g. "./mlflow", or
    absolute) into a proper file:// URI. Needed on Windows: mlflow parses
    the tracking URI by scheme, and an absolute Windows path like
    "C:\\...\\mlflow" is misread as scheme "c" (the drive letter), which
    mlflow doesn't recognize — it fails, silently, into our no-op tracker.
    Already-real URIs (http://, sqlite://, databricks, ...) pass through.
    """
    scheme = urlparse(uri).scheme
    if scheme == "" or (len(scheme) == 1 and scheme.isalpha()):
        return Path(uri).resolve().as_uri()
    return uri


@contextmanager
def track_run(experiment: str, run_name: str | None = None, params: dict | None = None):
    """
    Context manager wrapping one real unit of work (one Planning Agent
    call, one enrichment script run) as one MLflow run. Yields a tracker
    to call .log_metric/.log_params/.set_tag on. Always records
    latency_seconds and a success/failed status tag from what actually
    happened — re-raises the caller's exception unchanged after tagging
    the run as failed, it never swallows errors.
    """
    if not _MLFLOW_AVAILABLE:
        yield _NULL_TRACKER
        return

    try:
        mlflow.set_tracking_uri(_resolve_tracking_uri(settings.mlflow_tracking_uri))
        mlflow.set_experiment(experiment)
        mlflow.start_run(run_name=run_name)
    except Exception:
        logger.exception("could not start mlflow run for experiment=%r; continuing without tracking", experiment)
        yield _NULL_TRACKER
        return

    tracker = _MlflowTracker()
    if params:
        tracker.log_params(params)

    start = time.perf_counter()
    try:
        yield tracker
    except Exception as exc:
        tracker.set_tag("status", "failed")
        # MLflow tag values allow up to 5000 chars — truncate only enough
        # to stay under that, not the arbitrary 250 this used to be, which
        # was cutting real error messages off mid-sentence in the UI.
        tracker.set_tag("error", str(exc)[:_MAX_ERROR_TAG_LENGTH])
        raise
    else:
        tracker.set_tag("status", "success")
    finally:
        tracker.log_metric("latency_seconds", time.perf_counter() - start)
        try:
            mlflow.end_run()
        except Exception:
            logger.exception("mlflow.end_run failed")


def list_runs(experiment: str, limit: int = 20) -> list[dict]:
    """
    Returns real recorded runs for `experiment`, most recent first — each
    with its status/error tags, params, and metrics exactly as logged by
    track_run(). Returns [] (never fabricated data) if mlflow isn't
    installed, the tracking store doesn't exist yet, or the experiment has
    no runs.
    """
    if not _MLFLOW_AVAILABLE:
        return []

    try:
        mlflow.set_tracking_uri(_resolve_tracking_uri(settings.mlflow_tracking_uri))
        client = mlflow.tracking.MlflowClient()
        experiment_obj = client.get_experiment_by_name(experiment)
        if experiment_obj is None:
            return []
        runs = client.search_runs(
            [experiment_obj.experiment_id],
            order_by=["start_time DESC"],
            max_results=limit,
        )
    except Exception:
        logger.exception("failed to list mlflow runs for experiment=%r", experiment)
        return []

    return [
        {
            "run_id": run.info.run_id,
            "status": run.data.tags.get("status", "unknown"),
            "start_time_ms": run.info.start_time,
            "params": dict(run.data.params),
            "metrics": dict(run.data.metrics),
            "error": run.data.tags.get("error"),
        }
        for run in runs
    ]
