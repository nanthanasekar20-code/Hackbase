"""
Tests for Phase 7 MLflow tracking (app.core.tracking). tests/conftest.py's
autouse fixture already points settings.mlflow_tracking_uri at a per-test
tmp_path, so these exercise the real mlflow client against a throwaway
local store rather than mocking mlflow itself.
"""

import mlflow

from app.core.tracking import list_runs, track_run


def test_track_run_logs_params_and_success_status():
    with track_run("test_experiment", params={"batch_size": 8}) as run:
        run.log_metric("scored", 3)

    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("test_experiment")
    assert experiment is not None

    runs = client.search_runs([experiment.experiment_id])
    assert len(runs) == 1
    finished_run = runs[0]
    assert finished_run.data.params["batch_size"] == "8"
    assert finished_run.data.metrics["scored"] == 3.0
    assert "latency_seconds" in finished_run.data.metrics
    assert finished_run.data.tags["status"] == "success"


def test_track_run_tags_failure_and_reraises_original_exception():
    with_exception = None
    try:
        with track_run("test_experiment_failures") as run:
            run.log_metric("attempted", 1)
            raise ValueError("boom")
    except ValueError as exc:
        with_exception = exc

    assert with_exception is not None
    assert str(with_exception) == "boom"

    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("test_experiment_failures")
    runs = client.search_runs([experiment.experiment_id])
    assert len(runs) == 1
    assert runs[0].data.tags["status"] == "failed"
    assert "boom" in runs[0].data.tags["error"]


def test_track_run_keeps_most_of_a_long_error_message_not_just_250_chars():
    # Regression: this used to truncate to str(exc)[:250], which cut real
    # Gemini error messages off mid-sentence in the Tracking UI. MLflow
    # allows up to 5000 chars per tag value.
    long_message = "x" * 4000
    try:
        with track_run("test_experiment_long_errors") as run:
            raise ValueError(long_message)
    except ValueError:
        pass

    client = mlflow.tracking.MlflowClient()
    experiment = client.get_experiment_by_name("test_experiment_long_errors")
    runs = client.search_runs([experiment.experiment_id])
    assert len(runs[0].data.tags["error"]) > 250


def test_track_run_yields_working_tracker_even_if_mlflow_unavailable(monkeypatch):
    import app.core.tracking as tracking_module

    monkeypatch.setattr(tracking_module, "_MLFLOW_AVAILABLE", False)

    with track_run("unused_experiment") as run:
        # Must not raise even though nothing is actually being recorded.
        run.log_metric("x", 1)
        run.log_params({"y": 2})
        run.set_tag("z", "3")


def test_list_runs_returns_empty_list_for_unknown_experiment():
    assert list_runs("an_experiment_that_has_never_run") == []


def test_list_runs_returns_real_logged_run_data():
    with track_run("test_list_experiment", params={"batch_size": 8}) as run:
        run.log_metric("scored", 3)

    runs = list_runs("test_list_experiment")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"
    assert runs[0]["params"]["batch_size"] == "8"
    assert runs[0]["metrics"]["scored"] == 3.0
    assert runs[0]["error"] is None


def test_list_runs_surfaces_failure_and_error_tag():
    try:
        with track_run("test_list_experiment_failures") as run:
            run.log_metric("attempted", 1)
            raise ValueError("boom")
    except ValueError:
        pass

    runs = list_runs("test_list_experiment_failures")
    assert len(runs) == 1
    assert runs[0]["status"] == "failed"
    assert "boom" in runs[0]["error"]


def test_list_runs_returns_empty_list_if_mlflow_unavailable(monkeypatch):
    import app.core.tracking as tracking_module

    monkeypatch.setattr(tracking_module, "_MLFLOW_AVAILABLE", False)
    assert list_runs("unused_experiment") == []
