"""Regressions for the 2026-10-23 production errors:

1. The live Supabase project never got migration 0003, so ws_leads has no
   next_followup column. PostgREST 400s when due_followups() filters on it,
   which degraded the dashboard to an empty board and hard-500'd
   /automation and /api/digest.
2. The live ws_buyers table has UUID primary keys (repo migration 0002 says
   bigint). Buyer routes typed buyer_id as int, so every buyer link 422'd.

These tests simulate the live project's schema with a fake PostgREST layer.
"""
import os
import sys
import tempfile

import httpx
import pytest

_tmp = tempfile.mkdtemp()
os.environ["SQLITE_PATH"] = os.path.join(_tmp, "test.db")
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import db  # noqa: E402

UUID_BUYER = "91586247-253e-4ed4-be84-2a6618ffef8c"
LEAD = {"id": 1, "address": "1 Test St", "city": "Winnipeg", "postal": "",
        "source": "manual", "source_url": "", "tags": "", "asking_price": 100000,
        "arv_estimate": 200000, "repair_estimate": 10000, "motivation": "probate",
        "created_at": "2026-10-01T00:00:00Z", "updated_at": "2026-10-02T00:00:00Z"}
BUYER = {"id": UUID_BUYER, "name": "Aisha Bello", "phone": "204-555-0100",
         "email": "aisha@example.com", "company": "", "buyer_type": "cash_buyer",
         "target_areas": "", "min_price": None, "max_price": None,
         "property_types": "", "notes": "",
         "created_at": "2026-10-01T00:00:00Z", "updated_at": "2026-10-01T00:00:00Z"}


def _pg_error(msg):
    req = httpx.Request("GET", "https://fake.supabase.co/rest/v1/x")
    resp = httpx.Response(400, request=req, json={"code": "42703", "message": msg})
    return httpx.HTTPStatusError("400 Bad Request", request=req, response=resp)


@pytest.fixture()
def live_schema(monkeypatch):
    """db in Supabase mode against a project missing migration 0003 and
    whose ws_buyers uses UUID ids - i.e. production on 2026-10-23."""
    monkeypatch.setattr(db, "USE_SUPABASE", True)
    monkeypatch.setattr(db, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(db, "SUPABASE_KEY", "fake")
    for attr, val in [("T_LEADS", "ws_leads"), ("T_DEALS", "ws_deals"),
                      ("T_OWNERS", "ws_owners"), ("T_CALLS", "ws_calls"),
                      ("T_NOTES", "ws_notes"), ("T_CONTRACTS", "ws_contracts"),
                      ("T_BUYERS", "ws_buyers"), ("T_BUYER_OUTREACH", "ws_buyer_outreach"),
                      ("T_STAGE_HISTORY", "ws_stage_history"),
                      ("T_TASKS", "ws_tasks"), ("T_RUNS", "ws_automation_runs")]:
        if hasattr(db, attr):
            monkeypatch.setattr(db, attr, val)
    monkeypatch.setattr(db, "_buyers_ready", None)
    if hasattr(db, "_tasks_ready"):
        monkeypatch.setattr(db, "_tasks_ready", False)

    def fake_get(table, params=None):
        params = params or {}
        if "next_followup" in params:
            raise _pg_error("column ws_leads.next_followup does not exist")
        if table == "ws_leads":
            return [dict(LEAD)]
        if table == "ws_deals":
            return [{"lead_id": 1, "stage": "new", "offer_amount": None}]
        if table == "ws_buyers":
            if params.get("id", "").startswith("eq."):
                want = params["id"][3:]
                return [dict(BUYER)] if want == UUID_BUYER else []
            return [dict(BUYER)]
        return []

    monkeypatch.setattr(db, "sb_get", fake_get)
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_dashboard_renders_leads_despite_missing_followup_column(live_schema):
    r = live_schema.get("/")
    assert r.status_code == 200
    assert "temporarily unavailable" not in r.text
    assert "1 Test St" in r.text


def test_automation_page_not_500(live_schema):
    assert live_schema.get("/automation").status_code == 200


def test_digest_not_500(live_schema):
    r = live_schema.get("/api/digest")
    assert r.status_code == 200
    assert r.json()["followups_due"] == 0


def test_due_followups_falls_back(live_schema):
    assert db.due_followups() == []


def test_buyer_detail_accepts_uuid_id(live_schema):
    r = live_schema.get(f"/buyers/{UUID_BUYER}")
    assert r.status_code == 200
    assert "Aisha Bello" in r.text


def test_set_followup_missing_column_is_valueerror(live_schema, monkeypatch):
    def fake_patch(table, match, row):
        raise _pg_error("column ws_leads.next_followup does not exist")
    monkeypatch.setattr(db, "sb_patch", fake_patch)
    with pytest.raises(ValueError, match="not enabled"):
        db.set_followup(1, "2026-10-30", "call them")
