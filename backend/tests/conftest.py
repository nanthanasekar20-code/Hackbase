import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def _isolated_mlflow_tracking_dir(tmp_path, monkeypatch):
    """
    Tests exercise the Planning Agent and the enrichment script, both of
    which now open real MLflow runs (see app.core.tracking). Without this,
    every test run would write real runs into the project's ./mlflow
    store. Redirect tracking to a per-test tmp_path instead.
    """
    monkeypatch.setattr(settings, "mlflow_tracking_uri", str(tmp_path / "mlflow"))
