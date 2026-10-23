"""Access gate, crash reporting, and path-fix query handling."""
import base64
import os
import sys
import tempfile

os.environ.setdefault("SQLITE_PATH", os.path.join(tempfile.mkdtemp(), "h.db"))
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from app import error_report
from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def _basic(pw):
    return {"Authorization": "Basic " + base64.b64encode(f"u:{pw}".encode()).decode()}


def test_gate_open_by_default(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert client.get("/health").status_code == 200
    assert client.get("/leads").status_code == 200


def test_gate_blocks_and_allows(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    assert client.get("/leads").status_code == 401
    assert client.get("/leads", headers=_basic("wrong")).status_code == 401
    assert client.get("/leads", headers=_basic("s3cret")).status_code == 200
    assert client.get("/health").status_code == 200  # probe stays open


def test_path_fix_keeps_encoded_query(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    r = client.get("/api/index?__path=/leads&stage=new&sort=score")
    assert r.status_code == 200


def test_report_dedupes_and_is_off_without_env(monkeypatch):
    monkeypatch.delenv("ERROR_INBOX_URL", raising=False)
    assert error_report.report(ValueError("x"), "GET", "/a") is False
    monkeypatch.setenv("ERROR_INBOX_URL", "http://x")
    monkeypatch.setenv("ERROR_INBOX_KEY", "eibx_k")
    sent = []
    monkeypatch.setattr(error_report, "_post", lambda t: sent.append(t))
    error_report._seen.clear(); error_report._sent.clear()
    try:
        raise ValueError("boom")
    except ValueError as e:
        assert error_report.report(e, "GET", "/a") is True
        assert error_report.report(e, "GET", "/a") is False  # deduped


def test_crash_returns_friendly_500(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    monkeypatch.delenv("ERROR_INBOX_URL", raising=False)
    from app import db
    monkeypatch.setattr(db, "list_leads", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("db down")))
    r = client.get("/leads")
    assert r.status_code == 500 and "Something went wrong" in r.text
