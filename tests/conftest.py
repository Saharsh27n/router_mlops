"""Test configuration.

The environment is set up *before* any gateway module is imported, because
`gateway.config` builds its Settings singleton at import time. Tests run against the
local joblib artifact and the mock provider so they never touch MLflow or the network.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="smartroute-tests-"))

os.environ["MODEL_SOURCE"] = "local"
os.environ["FORCE_MOCK"] = "true"
os.environ["FAST_MOCK"] = "true"
os.environ["DB_PATH"] = str(_TMP / "gateway.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from gateway.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """TestClient as a context manager so FastAPI's lifespan actually runs.

    The demo API key is set once here as a default header, so every existing
    `client.post("/v1/chat", ...)` call site authenticates without being rewritten.
    """
    with TestClient(app) as test_client:
        test_client.headers.update({"X-API-Key": "demo-key-smartroute"})
        yield test_client


@pytest.fixture(scope="session")
def client_no_auth(client):
    """Same running app, but without the default auth header -- for tests that
    specifically exercise rejection paths."""
    bare = TestClient(app)
    bare.headers.pop("X-API-Key", None)
    return bare


def pytest_sessionfinish(session, exitstatus):
    """Ensure immediate process exit on Windows to avoid lingering daemon thread hangs."""
    import os

    if os.name == "nt":
        os._exit(exitstatus)
