"""Shared pytest fixtures and helpers for the backend test suite.

- Unit tests run in-process against the shared module and per-service helpers
  (no database, no network).
- Integration tests drive the running local stack over HTTP (LocalStack Lambdas
  via the dev proxy on :3001) — start it with `./bin/start-dev.sh`. They are
  skipped automatically when the API is not reachable.

Run:  pip install -r backend/tests/requirements.txt
      pytest backend/tests
"""

import importlib.util
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]
SHARED = BACKEND / "_shared"

# Make `import shared...` resolve, and provide a stable secret for token tests.
sys.path.insert(0, str(SHARED))
os.environ.setdefault("IS_LOCAL", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests")

API_BASE = os.environ.get("TEST_API_BASE", "http://localhost:3001/api")
ADMIN_EMAIL = "admin@coding-workshop.local"
ADMIN_PASSWORD = "ChangeMe123!"


def load_source(service: str, module: str):
    """Load backend/<service>/<module>.py under a unique name (avoids the
    function/models/repository name collisions across services)."""
    path = BACKEND / service / f"{module}.py"
    spec = importlib.util.spec_from_file_location(f"{service}_{module}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def loader():
    """Fixture wrapper around load_source for use in unit tests."""
    return load_source


# --- HTTP helpers for integration tests --------------------------------------

def api(method: str, path: str, token: str = None, body: dict = None):
    """Call the running API; returns (status_code, parsed_json_or_None)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        return exc.code, (json.loads(raw) if raw else None)


def _api_reachable() -> bool:
    try:
        api("POST", "/auth/login", body={"email": "x@y.z", "password": "x"})
        return True
    except (urllib.error.URLError, OSError):
        return False


@pytest.fixture(scope="session")
def requires_stack():
    """Skip integration tests when the local stack isn't running."""
    if not _api_reachable():
        pytest.skip("local stack not reachable on :3001 (run ./bin/start-dev.sh)")


@pytest.fixture(scope="session")
def admin_token(requires_stack):
    status, body = api("POST", "/auth/login", body={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if status != 200:
        pytest.skip(f"admin login failed ({status}); seed the local admin first")
    return body["access_token"]


@pytest.fixture
def http(requires_stack):
    """The API caller, for integration tests."""
    return api
