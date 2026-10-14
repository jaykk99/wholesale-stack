"""Database layer: Supabase (Postgres) when env is set, SQLite fallback for local dev.

Env:
  SUPABASE_URL, SUPABASE_KEY  -> use Supabase PostgREST via httpx
  otherwise                   -> local sqlite file wholesale.db
"""
import json
import os
import sqlite3
import time
from typing import Any

import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)

# Supabase shares the monico-agent project with other apps, so wholesale tables
# use a ws_ prefix there. Local SQLite keeps the bare names.
_P = "ws_" if USE_SUPABASE else ""
T_LEADS = _P + "leads"
T_OWNERS = _P + "owners"
T_DEALS = _P + "deals"
T_CALLS = _P + "calls"
T_NOTES = _P + "notes"
T_STAGE_HISTORY = _P + "stage_history"
T_CONTRACTS = _P + "contracts"
T_BUYERS = _P + "buyers"
T_BUYER_OUTREACH = _P + "buyer_outreach"

SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "..", "wholesale.db"))

# Deal types: each maps to playbook guidance, scripts, and contracts.
DEAL_TYPES = {
    "probate": {
        "label": "Probate / Inherited",
        "desc": "Owner passed away. Heirs want to sell fast.",
        "script": "cold_call",
        "contract": "purchase_agreement",
        "playbook": "/playbook#probate",
    },
    "pre_foreclosure": {
        "label": "Pre-Foreclosure",
        "desc": "Owner can't keep up with payments.",
        "script": "cold_call",
        "contract": "purchase_agreement",
        "playbook": "/playbook#pre-foreclosure",
    },
    "absentee": {
        "label": "Absentee Owner",
        "desc": "Owner doesn't live there. Often neglected.",
        "script": "cold_call",
        "contract": "assignment",
        "playbook": "/playbook",
    },
    "tired_landlord": {
        "label": "Tired Landlord",
        "desc": "Landlord done dealing with tenants.",
        "script": "follow_up",
        "contract": "assignment",
        "playbook": "/playbook",
    },
    "standard": {
        "label": "Standard",
        "desc": "Regular motivated seller.",
        "script": "cold_call",
        "contract": "purchase_agreement",
        "playbook": "/playbook",
    },
}


def payout_estimate(lead: dict) -> dict:
    """Wholesaling payout math: MAO = (ARV x 0.70) - repairs. Spread = MAO - asking."""
    try:
        arv = float(lead.get("arv_estimate") or 0)
        asking = float(lead.get("asking_price") or 0)
        repairs = float(lead.get("repair_estimate") or 0)
    except (TypeError, ValueError):
        return {"mao": 0, "spread": 0, "ready": False}
    if not arv:
        return {"mao": 0, "spread": 0, "ready": False}
    mao = arv * 0.70 - repairs
    spread = (mao - asking) if asking else 0
    return {"mao": round(mao), "spread": round(spread), "ready": True}

STAGES = ["new", "contacted", "appointment", "offer", "negotiation", "closed_won", "closed_lost"]
STAGE_LABELS = {
    "new": "New Lead",
    "contacted": "Contacted",
    "appointment": "Appointment Set",
    "offer": "Offer Made",
    "negotiation": "Negotiation",
    "closed_won": "Closed Won",
    "closed_lost": "Closed Lost",
}


def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def sb_get(table: str, params: dict | None = None) -> list[dict]:
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=_sb_headers(), params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


def sb_post(table: str, row: dict) -> dict:
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=_sb_headers(), json=row, timeout=20)
    r.raise_for_status()
    data = r.json()
    return data[0] if isinstance(data, list) and data else data


def sb_patch(table: str, match: dict, row: dict) -> list[dict]:
    params = {k: f"eq.{v}" for k, v in match.items()}
    r = httpx.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=_sb_headers(), params=params, json=row, timeout=20)
    r.raise_for_status()
    return r.json()


# ---------------- SQLite fallback ----------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  address TEXT NOT NULL, city TEXT DEFAULT 'Winnipeg', postal TEXT DEFAULT '',
  source TEXT DEFAULT 'manual', source_url TEXT DEFAULT '',
  tags TEXT DEFAULT '', asking_price REAL, arv_estimate REAL, repair_estimate REAL,
  motivation TEXT DEFAULT '', created_at REAL, updated_at REAL
);
CREATE TABLE IF NOT EXISTS owners (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL,
  name TEXT DEFAULT '', phone TEXT DEFAULT '', email TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS deals (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL UNIQUE,
  stage TEXT DEFAULT 'new', offer_amount REAL, created_at REAL, updated_at REAL
);
CREATE TABLE IF NOT EXISTS calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL,
  outcome TEXT DEFAULT '', notes TEXT DEFAULT '', duration_min INTEGER DEFAULT 0,
  called_at REAL
);
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL,
  body TEXT NOT NULL, created_at REAL
);
CREATE TABLE IF NOT EXISTS stage_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL,
  from_stage TEXT DEFAULT '', to_stage TEXT DEFAULT '', changed_at REAL
);
CREATE TABLE IF NOT EXISTS contracts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL,
  template_id TEXT NOT NULL, fields_json TEXT DEFAULT '{}', created_at REAL
);
CREATE TABLE IF NOT EXISTS buyers (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
  phone TEXT DEFAULT '', email TEXT DEFAULT '', company TEXT DEFAULT '',
  buyer_type TEXT DEFAULT 'cash_buyer', target_areas TEXT DEFAULT '',
  min_price REAL, max_price REAL, property_types TEXT DEFAULT '',
  notes TEXT DEFAULT '', created_at REAL, updated_at REAL
);
CREATE TABLE IF NOT EXISTS buyer_outreach (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL,
  buyer_id INTEGER NOT NULL, channel TEXT DEFAULT 'call', contacted_at REAL
);
"""


def _lite() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _now() -> float | str:
    # Supabase timestamptz columns need ISO strings; SQLite REAL columns take floats.
    if USE_SUPABASE:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    return time.time()


# ---------------- Unified API ----------------

def list_leads() -> list[dict]:
    if USE_SUPABASE:
        leads = sb_get(T_LEADS, {"order": "updated_at.desc"})
        deals = {d["lead_id"]: d for d in sb_get(T_DEALS)}
        for l in leads:
            l["stage"] = deals.get(l["id"], {}).get("stage", "new")
            l["owners"] = sb_get(T_OWNERS, {"lead_id": f"eq.{l['id']}"})
        return leads
    conn = _lite()
    rows = conn.execute(
        """SELECT l.*, COALESCE(d.stage,'new') AS stage, d.offer_amount
           FROM leads l LEFT JOIN deals d ON d.lead_id = l.id
           ORDER BY l.updated_at DESC"""
    ).fetchall()
    leads = [dict(r) for r in rows]
    for l in leads:
        l["owners"] = [dict(r) for r in conn.execute("SELECT * FROM owners WHERE lead_id=?", (l["id"],))]
    conn.close()
    return leads


def get_lead(lead_id: int) -> dict | None:
    if USE_SUPABASE:
        leads = sb_get(T_LEADS, {"id": f"eq.{lead_id}"})
        if not leads:
            return None
        lead = leads[0]
        deals = sb_get(T_DEALS, {"lead_id": f"eq.{lead_id}"})
        lead["stage"] = deals[0]["stage"] if deals else "new"
        lead["offer_amount"] = deals[0].get("offer_amount") if deals else None
        lead["owners"] = sb_get(T_OWNERS, {"lead_id": f"eq.{lead_id}"})
        lead["calls"] = sb_get(T_CALLS, {"lead_id": f"eq.{lead_id}", "order": "called_at.desc"})
        lead["notes"] = sb_get(T_NOTES, {"lead_id": f"eq.{lead_id}", "order": "created_at.desc"})
        lead["contracts"] = list_contracts(lead_id)
        return lead
    conn = _lite()
    row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        conn.close()
        return None
    lead = dict(row)
    deal = conn.execute("SELECT * FROM deals WHERE lead_id=?", (lead_id,)).fetchone()
    lead["stage"] = deal["stage"] if deal else "new"
    lead["offer_amount"] = deal["offer_amount"] if deal else None
    lead["owners"] = [dict(r) for r in conn.execute("SELECT * FROM owners WHERE lead_id=?", (lead_id,))]
    lead["calls"] = [dict(r) for r in conn.execute("SELECT * FROM calls WHERE lead_id=? ORDER BY called_at DESC", (lead_id,))]
    lead["notes"] = [dict(r) for r in conn.execute("SELECT * FROM notes WHERE lead_id=? ORDER BY created_at DESC", (lead_id,))]
    conn.close()
    lead["contracts"] = list_contracts(lead_id)
    return lead


def add_lead(data: dict) -> dict:
    row = {
        "address": data.get("address", "").strip(),
        "city": data.get("city", "Winnipeg").strip() or "Winnipeg",
        "postal": data.get("postal", "").strip(),
        "source": data.get("source", "manual"),
        "source_url": data.get("source_url", ""),
        "tags": data.get("tags", ""),
        "asking_price": _num(data.get("asking_price")),
        "arv_estimate": _num(data.get("arv_estimate")),
        "repair_estimate": _num(data.get("repair_estimate")),
        "motivation": data.get("motivation", ""),
        "created_at": _now(), "updated_at": _now(),
    }
    if USE_SUPABASE:
        lead = sb_post(T_LEADS, row)
        sb_post(T_DEALS, {"lead_id": lead["id"], "stage": "new", "created_at": _now(), "updated_at": _now()})
        owner_name = (data.get("owner_name") or "").strip()
        owner_phone = (data.get("owner_phone") or "").strip()
        if owner_name or owner_phone:
            sb_post(T_OWNERS, {"lead_id": lead["id"], "name": owner_name, "phone": owner_phone,
                               "email": (data.get("owner_email") or "").strip()})
        lead["stage"] = "new"
        return lead
    conn = _lite()
    cur = conn.execute(
        """INSERT INTO leads (address, city, postal, source, source_url, tags,
                              asking_price, arv_estimate, repair_estimate, motivation,
                              created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (row["address"], row["city"], row["postal"], row["source"], row["source_url"], row["tags"],
         row["asking_price"], row["arv_estimate"], row["repair_estimate"], row["motivation"],
         row["created_at"], row["updated_at"]),
    )
    lid = cur.lastrowid
    conn.execute("INSERT INTO deals (lead_id, stage, created_at, updated_at) VALUES (?,?,?,?)",
                 (lid, "new", _now(), _now()))
    if (data.get("owner_name") or "").strip() or (data.get("owner_phone") or "").strip():
        conn.execute("INSERT INTO owners (lead_id, name, phone, email) VALUES (?,?,?,?)",
                     (lid, (data.get("owner_name") or "").strip(),
                      (data.get("owner_phone") or "").strip(), (data.get("owner_email") or "").strip()))
    conn.commit()
    conn.close()
    lead = get_lead(lid)
    return lead


def move_stage(lead_id: int, to_stage: str) -> dict | None:
    if to_stage not in STAGES:
        raise ValueError(f"unknown stage: {to_stage}")
    lead = get_lead(lead_id)
    if not lead:
        return None
    from_stage = lead.get("stage", "new")
    if USE_SUPABASE:
        deals = sb_get(T_DEALS, {"lead_id": f"eq.{lead_id}"})
        if deals:
            sb_patch(T_DEALS, {"lead_id": lead_id}, {"stage": to_stage, "updated_at": _now()})
        else:
            sb_post(T_DEALS, {"lead_id": lead_id, "stage": to_stage, "created_at": _now(), "updated_at": _now()})
        sb_post(T_STAGE_HISTORY, {"lead_id": lead_id, "from_stage": from_stage, "to_stage": to_stage, "changed_at": _now()})
        sb_patch(T_LEADS, {"id": lead_id}, {"updated_at": _now()})
    else:
        conn = _lite()
        conn.execute("INSERT OR IGNORE INTO deals (lead_id, stage, created_at, updated_at) VALUES (?,?,?,?)",
                     (lead_id, to_stage, _now(), _now()))
        conn.execute("UPDATE deals SET stage=?, updated_at=? WHERE lead_id=?", (to_stage, _now(), lead_id))
        conn.execute("INSERT INTO stage_history (lead_id, from_stage, to_stage, changed_at) VALUES (?,?,?,?)",
                     (lead_id, from_stage, to_stage, _now()))
        conn.execute("UPDATE leads SET updated_at=? WHERE id=?", (_now(), lead_id))
        conn.commit()
        conn.close()
    return get_lead(lead_id)


def log_call(lead_id: int, outcome: str, notes: str, duration_min: int = 0) -> dict:
    row = {"lead_id": lead_id, "outcome": outcome, "notes": notes,
           "duration_min": duration_min, "called_at": _now()}
    if USE_SUPABASE:
        return sb_post(T_CALLS, row)
    conn = _lite()
    cur = conn.execute("INSERT INTO calls (lead_id, outcome, notes, duration_min, called_at) VALUES (?,?,?,?,?)",
                       (lead_id, outcome, notes, duration_min, _now()))
    cid = cur.lastrowid
    conn.execute("UPDATE leads SET updated_at=? WHERE id=?", (_now(), lead_id))
    conn.commit()
    conn.close()
    row["id"] = cid
    return row


def add_note(lead_id: int, body: str) -> dict:
    row = {"lead_id": lead_id, "body": body, "created_at": _now()}
    if USE_SUPABASE:
        return sb_post(T_NOTES, row)
    conn = _lite()
    cur = conn.execute("INSERT INTO notes (lead_id, body, created_at) VALUES (?,?,?)", (lead_id, body, _now()))
    nid = cur.lastrowid
    conn.execute("UPDATE leads SET updated_at=? WHERE id=?", (_now(), lead_id))
    conn.commit()
    conn.close()
    row["id"] = nid
    return row


def pipeline_counts() -> dict:
    counts = {s: 0 for s in STAGES}
    for l in list_leads():
        counts[l.get("stage", "new")] = counts.get(l.get("stage", "new"), 0) + 1
    return counts


def _num(v: Any) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def backend_name() -> str:
    return "supabase" if USE_SUPABASE else "sqlite-local"


def save_contract(lead_id: int, template_id: str, fields: dict) -> dict:
    payload = json.dumps(fields)
    row = {"lead_id": lead_id, "template_id": template_id, "fields_json": payload, "created_at": _now()}
    if USE_SUPABASE:
        return sb_post(T_CONTRACTS, row)
    conn = _lite()
    cur = conn.execute("INSERT INTO contracts (lead_id, template_id, fields_json, created_at) VALUES (?,?,?,?)",
                       (lead_id, template_id, payload, _now()))
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    row["id"] = cid
    row["fields"] = fields
    return row


def list_contracts(lead_id: int) -> list[dict]:
    if USE_SUPABASE:
        rows = sb_get(T_CONTRACTS, {"lead_id": f"eq.{lead_id}", "order": "created_at.desc"})
    else:
        conn = _lite()
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM contracts WHERE lead_id=? ORDER BY created_at DESC", (lead_id,))]
        conn.close()
    for r in rows:
        try:
            r["fields"] = json.loads(r.get("fields_json") or "{}")
        except Exception:
            r["fields"] = {}
    return rows


def list_all_contracts() -> list[dict]:
    if USE_SUPABASE:
        rows = sb_get(T_CONTRACTS, {"order": "created_at.desc", "limit": "100"})
    else:
        conn = _lite()
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM contracts ORDER BY created_at DESC LIMIT 100")]
        conn.close()
    for r in rows:
        try:
            r["fields"] = json.loads(r.get("fields_json") or "{}")
        except Exception:
            r["fields"] = {}
        # attach lead name for display
        try:
            lead = get_lead(r["lead_id"])
            r["lead_name"] = (lead or {}).get("address") or f"Lead {r['lead_id']}"
        except Exception:
            r["lead_name"] = f"Lead {r['lead_id']}"
    return rows


# ---------------- Buyers CRM ----------------

BUYER_TYPES = {
    "cash_buyer": "Cash Buyer",
    "landlord": "Landlord",
    "flipper": "Flipper",
    "hedge_fund": "Hedge Fund / iBuyer",
    "realtor_investor": "Investor Realtor",
    "other": "Other",
}

_buyers_ready: bool | None = None


def buyers_ready() -> bool:
    """True when the buyers tables exist (migration 0002 applied). Cached."""
    global _buyers_ready
    if _buyers_ready is not None:
        return _buyers_ready
    if USE_SUPABASE:
        try:
            sb_get(T_BUYERS, {"limit": "1"})
            _buyers_ready = True
        except Exception:
            _buyers_ready = False
    else:
        _buyers_ready = True  # sqlite schema auto-creates
    return _buyers_ready


def list_buyers() -> list[dict]:
    if not buyers_ready():
        return []
    if USE_SUPABASE:
        try:
            return sb_get(T_BUYERS, {"order": "name.asc"})
        except Exception:
            return []
    conn = _lite()
    rows = [dict(r) for r in conn.execute("SELECT * FROM buyers ORDER BY name")]
    conn.close()
    return rows


def get_buyer(buyer_id: int) -> dict | None:
    if not buyers_ready():
        return None
    if USE_SUPABASE:
        try:
            rows = sb_get(T_BUYERS, {"id": f"eq.{buyer_id}"})
        except Exception:
            return None
        return rows[0] if rows else None
    conn = _lite()
    row = conn.execute("SELECT * FROM buyers WHERE id=?", (buyer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_buyer(data: dict) -> dict | None:
    if not buyers_ready():
        return None
    row = {
        "name": (data.get("name") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "email": (data.get("email") or "").strip(),
        "company": (data.get("company") or "").strip(),
        "buyer_type": data.get("buyer_type") or "cash_buyer",
        "target_areas": (data.get("target_areas") or "").strip(),
        "min_price": _num(data.get("min_price")),
        "max_price": _num(data.get("max_price")),
        "property_types": (data.get("property_types") or "").strip(),
        "notes": (data.get("notes") or "").strip(),
        "created_at": _now(), "updated_at": _now(),
    }
    if USE_SUPABASE:
        return sb_post(T_BUYERS, row)
    conn = _lite()
    cur = conn.execute(
        """INSERT INTO buyers (name, phone, email, company, buyer_type, target_areas,
                               min_price, max_price, property_types, notes, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (row["name"], row["phone"], row["email"], row["company"], row["buyer_type"],
         row["target_areas"], row["min_price"], row["max_price"], row["property_types"],
         row["notes"], row["created_at"], row["updated_at"]))
    bid = cur.lastrowid
    conn.commit()
    conn.close()
    return get_buyer(bid)


def update_buyer(buyer_id: int, data: dict) -> dict | None:
    if not buyers_ready():
        return None
    row = {
        "name": (data.get("name") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "email": (data.get("email") or "").strip(),
        "company": (data.get("company") or "").strip(),
        "buyer_type": data.get("buyer_type") or "cash_buyer",
        "target_areas": (data.get("target_areas") or "").strip(),
        "min_price": _num(data.get("min_price")),
        "max_price": _num(data.get("max_price")),
        "property_types": (data.get("property_types") or "").strip(),
        "notes": (data.get("notes") or "").strip(),
        "updated_at": _now(),
    }
    if USE_SUPABASE:
        sb_patch(T_BUYERS, {"id": buyer_id}, row)
    else:
        conn = _lite()
        conn.execute(
            """UPDATE buyers SET name=?, phone=?, email=?, company=?, buyer_type=?,
                                target_areas=?, min_price=?, max_price=?, property_types=?,
                                notes=?, updated_at=? WHERE id=?""",
            (row["name"], row["phone"], row["email"], row["company"], row["buyer_type"],
             row["target_areas"], row["min_price"], row["max_price"], row["property_types"],
             row["notes"], row["updated_at"], buyer_id))
        conn.commit()
        conn.close()
    return get_buyer(buyer_id)


def delete_buyer(buyer_id: int) -> None:
    if not buyers_ready():
        return
    if USE_SUPABASE:
        try:
            httpx.delete(f"{SUPABASE_URL}/rest/v1/{T_BUYER_OUTREACH}",
                         headers=_sb_headers(), params={"buyer_id": f"eq.{buyer_id}"}, timeout=20)
            httpx.delete(f"{SUPABASE_URL}/rest/v1/{T_BUYERS}",
                         headers=_sb_headers(), params={"id": f"eq.{buyer_id}"}, timeout=20)
        except Exception:
            pass
    else:
        conn = _lite()
        conn.execute("DELETE FROM buyer_outreach WHERE buyer_id=?", (buyer_id,))
        conn.execute("DELETE FROM buyers WHERE id=?", (buyer_id,))
        conn.commit()
        conn.close()


def _csv_match(needles: str, haystack_csv: str) -> bool:
    """True if any comma-separated needle appears in the haystack csv (case-insensitive)."""
    if not haystack_csv or not haystack_csv.strip():
        return True  # no preference = matches everything
    hay = haystack_csv.lower()
    for n in (needles or "").split(","):
        n = n.strip().lower()
        if n and n in hay:
            return True
    return False


def match_buyers(lead: dict) -> list[dict]:
    """Buyers whose criteria fit this property. Sorted best-first."""
    buyers = list_buyers()
    if not buyers:
        return []
    try:
        price = float(lead.get("asking_price") or 0)
    except (TypeError, ValueError):
        price = 0
    city = (lead.get("city") or "").lower()
    ptype = (lead.get("motivation") or "").lower()
    scored = []
    for b in buyers:
        score = 0
        reasons = []
        # price
        try:
            lo = float(b.get("min_price")) if b.get("min_price") is not None else None
        except (TypeError, ValueError):
            lo = None
        try:
            hi = float(b.get("max_price")) if b.get("max_price") is not None else None
        except (TypeError, ValueError):
            hi = None
        if price and (lo is not None or hi is not None):
            if lo is not None and price < lo:
                continue
            if hi is not None and price > hi:
                continue
            score += 2
            reasons.append("price fits")
        # area
        areas = (b.get("target_areas") or "").strip()
        if areas:
            if not city or not _csv_match(city, areas):
                continue
            score += 2
            reasons.append("buys in this area")
        # property type
        ptypes = (b.get("property_types") or "").strip()
        if ptypes:
            if not ptype or not _csv_match(ptype, ptypes):
                continue
            score += 1
            reasons.append("wants this deal type")
        scored.append((score, b, reasons))
    scored.sort(key=lambda x: (-x[0], (x[1].get("name") or "").lower()))
    out = []
    for score, b, reasons in scored:
        b = dict(b)
        b["match_reasons"] = reasons or ["no filters set"]
        out.append(b)
    return out


def log_buyer_contact(lead_id: int, buyer_id: int, channel: str = "call") -> dict | None:
    if not buyers_ready():
        return None
    row = {"lead_id": lead_id, "buyer_id": buyer_id, "channel": channel, "contacted_at": _now()}
    if USE_SUPABASE:
        try:
            return sb_post(T_BUYER_OUTREACH, row)
        except Exception:
            return None
    conn = _lite()
    cur = conn.execute("INSERT INTO buyer_outreach (lead_id, buyer_id, channel, contacted_at) VALUES (?,?,?,?)",
                       (lead_id, buyer_id, channel, _now()))
    oid = cur.lastrowid
    conn.commit()
    conn.close()
    row["id"] = oid
    return row


def buyer_outreach_for_lead(lead_id: int) -> dict[int, list[dict]]:
    """buyer_id -> list of outreach rows, newest first."""
    if not buyers_ready():
        return {}
    if USE_SUPABASE:
        try:
            rows = sb_get(T_BUYER_OUTREACH, {"lead_id": f"eq.{lead_id}", "order": "contacted_at.desc"})
        except Exception:
            return {}
    else:
        conn = _lite()
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM buyer_outreach WHERE lead_id=? ORDER BY contacted_at DESC", (lead_id,))]
        conn.close()
    grouped: dict[int, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["buyer_id"], []).append(r)
    return grouped
