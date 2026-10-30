import os
import subprocess
import sys
from pathlib import Path

import pytest

# A fake secret for testing only. The real one is never written in code.
os.environ.setdefault("SECRET_KEY", "test_only_not_a_real_secret")

from app import app  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


@pytest.mark.parametrize("good_name", [
    "Muskan",
    "Ada Lovelace",
    "a" * 50,
])
def test_valid_names_are_accepted(client, good_name):
    response = client.get("/greet", query_string={"name": good_name})
    assert response.status_code == 200
    assert f"Hello, {good_name}!".encode() in response.data


@pytest.mark.parametrize("bad_name", [
    "<script>alert(1)</script>",
    "a" * 51,
    "Muskan\n",
    "",
    "' OR 1=1 --",
    "../etc/passwd",
])

def test_bad_names_are_rejected(client, bad_name):
    response = client.get("/greet", query_string={"name": bad_name})
    assert response.status_code == 400


def test_debug_mode_is_off():
    assert app.debug is False


def test_app_refuses_to_start_without_secret():
    env = {k: v for k, v in os.environ.items() if k != "SECRET_KEY"}
    result = subprocess.run(
        [sys.executable, "-c", "import app"],
        env=env, cwd=PROJECT_ROOT, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr