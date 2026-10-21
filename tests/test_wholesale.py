"""Wholesale Stack test battery: analyzer math, payout, scoring, follow-ups,
buyer matching, exit strategies. SQLite temp DB via SQLITE_PATH. Run: pytest."""
import os
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["SQLITE_PATH"] = os.path.join(_tmp, "test.db")
# Force sqlite backend even if env has Supabase vars in CI.
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import analyzer, db
from app import exits


# ---------- analyzer.parse_money ----------

def test_parse_money_plain():
    assert analyzer.parse_money("185000") == 185000.0
    assert analyzer.parse_money(185000) == 185000.0


def test_parse_money_shorthand():
    assert analyzer.parse_money("250k") == 250000.0
    assert analyzer.parse_money("$185,000") == 185000.0
    assert analyzer.parse_money("1.2m") == 1_200_000.0


def test_parse_money_junk():
    assert analyzer.parse_money("") == 0.0
    assert analyzer.parse_money(None) == 0.0
    assert analyzer.parse_money("n/a") == 0.0


# ---------- analyzer.analyze ----------

def test_analyze_deal_verdict():
    r = analyzer.analyze(arv=250000, asking=120000, repairs=30000)
    assert r["ready"] is True
    assert r["mao"] == 145000  # 250k*0.7 - 30k
    assert r["spread"] == 25000
    assert r["verdict"] == "deal"
    assert r["offer_for_fee"] == 135000


def test_analyze_thin():
    r = analyzer.analyze(arv=250000, asking=140000, repairs=30000, desired_fee=10000)
    assert r["verdict"] == "thin"  # 5k spread < 10k fee, >= 5k


def test_analyze_tight_and_no_deal():
    r = analyzer.analyze(arv=250000, asking=143000, repairs=30000, desired_fee=10000)
    assert r["verdict"] == "tight"
    r = analyzer.analyze(arv=250000, asking=150000, repairs=30000)
    assert r["verdict"] == "no-deal"
    assert r["spread"] == -5000


def test_analyze_needs_arv():
    r = analyzer.analyze(arv=0, asking=120000)
    assert r["ready"] is False
    assert r["verdict"] == "need-arv"


def test_analyze_costs_reduce_mao():
    base = analyzer.analyze(arv=200000, asking=100000, repairs=20000)
    with_costs = analyzer.analyze(arv=200000, asking=100000, repairs=20000,
                                  closing_costs=5000, holding_costs=3000)
    assert with_costs["mao"] == base["mao"] - 8000


def test_analyze_lines_show_math():
    r = analyzer.analyze(arv=200000, asking=100000, repairs=20000)
    labels = [label for label, _ in r["lines"]]
    assert "Maximum allowable offer" in labels
    assert "Spread (room for your fee)" in labels


def test_fmt():
    assert analyzer.fmt(185000) == "$185,000"
    assert analyzer.fmt(-5000) == "-$5,000"


# ---------- db.payout_estimate ----------

def test_payout_estimate():
    p = db.payout_estimate({"arv_estimate": 200000, "asking_price": 100000, "repair_estimate": 20000})
    assert p == {"mao": 120000, "spread": 20000, "ready": True}


def test_payout_not_ready_without_arv():
    p = db.payout_estimate({"asking_price": 100000})
    assert p["ready"] is False


# ---------- db.lead_score ----------

def _lead(**kw):
    base = {"motivation": "standard", "owners": [], "stage": "new",
            "asking_price": None, "arv_estimate": None, "repair_estimate": None,
            "updated_at": None}
    base.update(kw)
    return base


def test_score_motivation_weight():
    assert db.lead_score(_lead(motivation="probate"))["score"] > db.lead_score(_lead())["score"]


def test_score_spread_adds():
    hot = _lead(motivation="probate", arv_estimate=300000, asking_price=100000, repair_estimate=10000,
                owners=[{"phone": "204-555-0100"}])
    s = db.lead_score(hot)
    assert s["score"] == 25 + 30 + 15  # motivation + capped spread + phone
    assert s["band"] == "hot"
    assert any("spread" in r for r in s["reasons"])


def test_score_phone_and_band():
    s = db.lead_score(_lead(owners=[{"phone": "204-555-0100"}]))
    assert s["score"] == 10 + 15  # standard motivation + phone
    assert s["band"] == "cold"


def test_score_capped_at_100():
    s = db.lead_score(_lead(motivation="probate", arv_estimate=500000,
                            asking_price=100000, repair_estimate=10000,
                            owners=[{"phone": "1"}], stage="negotiation"))
    assert s["score"] <= 100


# ---------- follow-ups (real SQLite) ----------

def test_followup_roundtrip_and_due():
    lead = db.add_lead({"address": "1 Test St", "city": "Winnipeg"})
    assert db.due_followups() == []
    db.set_followup(lead["id"], "2000-01-01", "old reminder")
    due = db.due_followups()
    assert len(due) == 1 and due[0]["id"] == lead["id"]
    assert due[0]["followup_note"] == "old reminder"
    # future date is not due
    db.set_followup(lead["id"], "2999-01-01", "")
    assert db.due_followups() == []
    # clearing works
    db.set_followup(lead["id"], "", "")
    got = db.get_lead(lead["id"])
    assert not got["next_followup"]


def test_followup_bad_date_rejected():
    lead = db.add_lead({"address": "2 Test St"})
    with pytest.raises(ValueError):
        db.set_followup(lead["id"], "not-a-date")


def test_closed_leads_excluded_from_due():
    lead = db.add_lead({"address": "3 Test St"})
    db.set_followup(lead["id"], "2000-01-01", "")
    db.move_stage(lead["id"], "closed_lost")
    assert all(l["id"] != lead["id"] for l in db.due_followups())


# ---------- buyers ----------

def test_match_buyers_price_window():
    assert db.buyers_ready() is True
    b = db.add_buyer({"name": "Cash Buyer", "min_price": "50000", "max_price": "150000",
                      "target_areas": "winnipeg"})
    assert b is not None
    matched = db.match_buyers({"asking_price": 100000, "city": "Winnipeg", "motivation": "standard"})
    assert any(m["name"] == "Cash Buyer" for m in matched)
    matched2 = db.match_buyers({"asking_price": 500000, "city": "Winnipeg", "motivation": "standard"})
    assert all(m["name"] != "Cash Buyer" for m in matched2)


# ---------- exits ----------

def test_exit_strategies_count():
    xs = exits.exit_strategies({"arv_estimate": 200000, "asking_price": 120000, "repair_estimate": 20000})
    assert len(xs) == 8
    assert xs[0]["id"] == "assignment"


def test_exit_strategies_need_arv():
    assert exits.exit_strategies({"asking_price": 120000}) == []
