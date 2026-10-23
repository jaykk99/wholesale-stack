"""Autopilot tests: classification, de-dupe, task planning, full cycle, routes. SQLite temp DB."""
import os
import sys
import tempfile
import time
from datetime import date

_tmp = tempfile.mkdtemp()
os.environ.setdefault("SQLITE_PATH", os.path.join(_tmp, "auto.db"))
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)
os.environ["CRON_SECRET"] = "test-secret"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import automation, db


# ---------- classify ----------

def test_classify_probate_and_tags():
    m, tags = automation.classify("Estate sale - 3 bed bungalow, sold AS IS, needs TLC, price reduced")
    assert m == "probate"
    assert {"as-is", "fixer", "price-drop"} <= set(tags)


def test_classify_landlord_and_absentee():
    assert automation.classify("Duplex with tenants in place")[0] == "tired_landlord"
    assert automation.classify("Vacant home, owner relocated out of province")[0] == "absentee"
    assert automation.classify("Power of sale! bring offers")[0] == "pre_foreclosure"
    assert automation.classify("Lovely family home")[0] == ""


def test_normalize_address():
    assert automation.normalize_address("123 Main Street, Winnipeg, MB") == automation.normalize_address("123 main st")
    assert automation.normalize_address("45 Oak Crescent") == "45 oak cres"


# ---------- ingest ----------

def test_ingest_dedupes_by_url_and_address():
    before = len(db.list_leads())
    found = [
        {"address": "900 Ingest Avenue", "source_url": "https://x/1", "tags": "kijiji", "source": "kijiji_winnipeg"},
        {"address": "900 Ingest Ave, Winnipeg", "source_url": "https://x/2", "source": "kijiji_winnipeg"},   # same house
        {"address": "901 Ingest Ave estate sale", "source_url": "https://x/3", "source": "kijiji_winnipeg"},
        {"address": "", "source_url": "https://x/4"},
    ]
    r = automation.ingest(found)
    assert r == {"added": 2, "duplicates": 1, "skipped": 1}
    r2 = automation.ingest(found)            # second run: nothing new
    assert r2["added"] == 0
    assert len(db.list_leads()) == before + 2
    tagged = [l for l in db.list_leads() if l["address"].startswith("901 Ingest")][0]
    assert tagged["motivation"] == "probate"


# ---------- planning ----------

def _lead(i, stage="new", phone="", arv=None, asking=None, updated=None, followup=""):
    return {"id": i, "address": f"{i} Plan St", "stage": stage, "owners": [{"name": "Sam Seller", "phone": phone}] if phone else [],
            "arv_estimate": arv, "asking_price": asking, "repair_estimate": 10000,
            "updated_at": updated if updated is not None else time.time(), "next_followup": followup, "motivation": "standard"}


def test_plan_new_lead_tasks():
    tasks, _ = automation.plan([_lead(1), _lead(2, phone="204-555-0101")], {}, {}, 0)
    kinds = {(t["lead_id"], t["kind"]) for t in tasks}
    assert (1, "find_contact") in kinds
    assert (2, "call_seller") in kinds


def test_plan_called_lead_no_call_task():
    tasks, _ = automation.plan([_lead(3, phone="204-555-0101")], {3: [{"called_at": time.time()}]}, {}, 0)
    assert not any(t["kind"] == "call_seller" for t in tasks)


def test_plan_analyze_and_blast():
    leads = [_lead(4, stage="contacted"), _lead(5, stage="offer", arv=250000, asking=120000)]
    tasks, _ = automation.plan(leads, {}, {}, buyers=3)
    kinds = {(t["lead_id"], t["kind"]) for t in tasks}
    assert (4, "analyze") in kinds
    assert (5, "blast_buyers") in kinds
    tasks2, _ = automation.plan(leads, {}, {5: 2}, buyers=3)   # already sent to buyers
    assert not any(t["kind"] == "blast_buyers" for t in tasks2)
    assert tasks[0]["kind"] == "blast_buyers"                 # highest priority first


def test_plan_followups_respect_cadence_and_existing():
    old = time.time() - 10 * 86400
    leads = [_lead(6, stage="contacted", updated=old), _lead(7, stage="contacted", updated=old, followup="2030-01-01"),
             _lead(8, stage="contacted"), _lead(9, stage="closed_lost", updated=old)]
    _, fus = automation.plan(leads, {}, {}, 0, today=date(2026, 10, 23))
    ids = {f["lead_id"] for f in fus}
    assert ids == {6}
    assert fus[0]["date"] == "2026-10-23" and fus[0]["note"].startswith("Auto:")


def test_plan_stale_review():
    old = time.time() - 60 * 86400
    tasks, _ = automation.plan([_lead(10, stage="contacted", updated=old, phone="1")], {10: [{"called_at": old}]}, {}, 0)
    assert any(t["kind"] == "review_stale" for t in tasks)


# ---------- drafts ----------

def test_drafts_are_links_not_sends():
    lead = {"address": "12 Draft St", "stage": "new", "owners": [{"name": "Pat Owner", "phone": "(204) 555-0199"}]}
    txt = automation.seller_text(lead)
    assert "Pat" in txt and "12 Draft St" in txt
    link = automation.sms_link("(204) 555-0199", txt)
    assert link.startswith("sms:2045550199?&body=") and " " not in link
    blast = automation.buyer_blast({"address": "12 Draft St", "city": "Winnipeg", "asking_price": 100000, "arv_estimate": 200000})
    assert "$100,000" in blast and "ARV" in blast


# ---------- tasks + full cycle ----------

def test_add_task_dedupes_open():
    lead = db.add_lead({"address": "77 Task Rd"})
    assert db.add_task(lead["id"], "call_seller", "Call") is not None
    assert db.add_task(lead["id"], "call_seller", "Call again") is None
    t = [t for t in db.list_tasks() if t["lead_id"] == lead["id"]][0]
    db.set_task_status(t["id"], "done")
    assert db.add_task(lead["id"], "call_seller", "Call") is not None   # can be planned again later


def test_run_cycle_without_scraping_builds_queue_and_logs():
    lead = db.add_lead({"address": "55 Cycle Blvd", "owner_name": "Chris", "owner_phone": "204-555-0111"})
    s = automation.run_cycle("test", scrape=False)
    assert not s["errors"], s
    assert s["tasks_created"] >= 1
    q = automation.today_queue(50)
    mine = [t for t in q if t["lead_id"] == lead["id"]]
    assert mine and mine[0]["kind"] == "call_seller" and mine[0]["sms"].startswith("sms:")
    runs = db.list_runs(5)
    assert runs and runs[0]["trigger"] == "test" and runs[0]["summary"]["tasks_created"] >= 1
    s2 = automation.run_cycle("test", scrape=False)          # idempotent: no duplicate tasks
    assert s2["tasks_created"] == 0


def test_run_cycle_survives_broken_source(monkeypatch):
    def boom(name, **kw):
        raise RuntimeError("blocked")
    monkeypatch.setattr(automation, "run_scraper", boom)
    s = automation.run_cycle("test", scrape=True, sources=("kijiji_winnipeg",))
    assert "error" in s["sources"]["kijiji_winnipeg"]
    assert "tasks_created" in s


def test_closed_lead_tasks_drop_out_of_queue():
    lead = db.add_lead({"address": "66 Closed Way", "owner_phone": "204-555-0122"})
    automation.run_cycle("test", scrape=False)
    db.move_stage(lead["id"], "closed_lost")
    assert all(t["lead_id"] != lead["id"] for t in automation.today_queue(100))


# ---------- db fixes ----------

def test_ts_of_handles_iso_and_float():
    assert db.ts_of(12.5) == 12.5
    assert abs(db.ts_of("2026-10-23T12:00:00+00:00") - 1792756800.0) < 1
    assert db.ts_of("") == 0 and db.ts_of("garbage") == 0


def test_stale_penalty_applies_to_iso_timestamps():
    fresh = db.lead_score({"stage": "new", "updated_at": time.time()})
    stale = db.lead_score({"stage": "new", "updated_at": "2020-01-01T00:00:00+00:00"})
    assert stale["score"] == fresh["score"] - 10


# ---------- routes ----------

def test_routes():
    from starlette.testclient import TestClient
    from app import main
    c = TestClient(main.app, raise_server_exceptions=True)
    db.add_lead({"address": "1 Route St", "owner_phone": "204-555-0133"})
    automation.run_cycle("test", scrape=False)
    r = c.get("/")
    assert r.status_code == 200 and "Today" in r.text
    assert c.get("/automation").status_code == 200
    assert c.post("/cron/run").status_code == 403
    r = c.post("/cron/run", headers={"X-Cron-Secret": "test-secret"})
    assert r.status_code == 200 and r.json()["ok"]
    assert c.get("/api/digest").json()["ok"]
    lead = db.list_leads()[0]
    assert "Ready-to-send" in c.get(f"/leads/{lead['id']}").text
    t = db.list_tasks()[0]
    r = c.post(f"/tasks/{t['id']}/done", data={"back": "/"}, follow_redirects=False)
    assert r.status_code == 303
    assert all(x["id"] != t["id"] for x in db.list_tasks())


def test_analyzer_saves_numbers_to_lead():
    from starlette.testclient import TestClient
    from app import main
    c = TestClient(main.app)
    lead = db.add_lead({"address": "3 Numbers Ln", "asking_price": "120000"})
    r = c.post(f"/analyzer?lead_id={lead['id']}", data={"arv": "250k", "asking": "120000", "repairs": "30000"})
    assert r.status_code == 200
    got = db.get_lead(lead["id"])
    assert got["arv_estimate"] == 250000 and got["repair_estimate"] == 30000
