"""Automation engine: the CRM runs itself between Amanda's calls.

One cycle (run_cycle) does, in order:
  1. Scrape every working lead source and add only NEW properties (de-duplicated by listing URL
     and by normalized street address, so repeat runs never pile up copies).
  2. Read each listing's text and auto-tag the deal type (probate, pre-foreclosure, tired
     landlord, absentee) plus distress signals (as-is, fixer, price reduced, ...).
  3. Keep every open lead moving: if nothing happened within the stage's follow-up cadence and no
     follow-up date is set, it schedules one.
  4. Builds the "Today" action queue: call new sellers, find missing phone numbers, run the numbers
     on leads without an ARV, blast matched buyers once a deal is under offer, and review dead leads.
     Each task carries a ready-to-send text/email draft. Nothing is ever sent automatically —
     Amanda taps once to open it in her own Messages / Mail app.
  5. Logs what it did (Tools -> Automation shows the history).

Triggers: the built-in scheduler (on by default, every AUTOMATION_INTERVAL_HOURS), the
"Run now" button, or POST /cron/run with the CRON_SECRET (GitHub Actions pings it every 6 hours so
a sleeping free-tier host still runs).
"""
from __future__ import annotations

import logging
import re
import threading
import time
from datetime import date, timedelta
from urllib.parse import quote

from . import db
from .scrapers import SCRAPERS, run_scraper

log = logging.getLogger("wholesale.automation")

# Sources that return real listings unattended. Manual-checklist sources (probate) are not scraped.
AUTO_SOURCES = ("kijiji_winnipeg", "craigslist_winnipeg")

# ---------------------------------------------------------------- listing text -> deal type + tags
MOTIVATION_RULES = [
    ("probate", r"\b(estate sale|estate of|executor|executrix|inherit(ed|ance)|probate|deceased|passed away)\b"),
    ("pre_foreclosure", r"\b(power of sale|foreclos\w*|bank[- ]owned|behind on (payments|mortgage)|must sell|court ordered|mortgage arrears)\b"),
    ("tired_landlord", r"\b(tenant(s|ed)? (in place|occupied)|tenant[- ]occupied|rental (property|income)|income property|investor special|duplex|triplex|fourplex|rented)\b"),
    ("absentee", r"\b(vacant|out of (town|province|country)|relocat\w+|moved away|empty house|unoccupied)\b"),
]
DISTRESS_TAGS = [
    ("as-is", r"\bas[- ]is\b"),
    ("fixer", r"\b(fixer|handyman|tlc|needs (work|updating|repairs?|love)|renovat(e|or)'?s? (dream|special)|project)\b"),
    ("motivated", r"\b(motivated|must sell|quick (sale|close)|priced to sell|bring (all )?offers|obo)\b"),
    ("price-drop", r"\b(price (reduced|drop|improvement)|reduced|new price)\b"),
    ("cash-only", r"\b(cash (only|buyers?)|no financing)\b"),
    ("foundation", r"\b(foundation|structural)\b"),
]


def classify(text: str) -> tuple[str, list[str]]:
    """Deal type (or '' for standard) and distress tags found in listing text."""
    t = (text or "").lower()
    motivation = next((m for m, rx in MOTIVATION_RULES if re.search(rx, t)), "")
    tags = [name for name, rx in DISTRESS_TAGS if re.search(rx, t)]
    return motivation, tags


_STREET_WORDS = {"street": "st", "avenue": "ave", "av": "ave", "road": "rd", "drive": "dr", "boulevard": "blvd",
                 "crescent": "cres", "cr": "cres", "place": "pl", "court": "crt", "ct": "crt", "lane": "ln", "bay": "bay"}


def normalize_address(addr: str) -> str:
    """'123 Main Street, Winnipeg' == '123 main st' for de-duplication."""
    a = re.sub(r"[^a-z0-9 ]", " ", (addr or "").lower())
    a = re.sub(r"\b(winnipeg|manitoba|mb|canada|for sale|house|home|bungalow|unit)\b", " ", a)
    words = [_STREET_WORDS.get(w, w) for w in a.split()]
    return " ".join(words).strip()


# ---------------------------------------------------------------- ingest scraped leads
def ingest(found: list[dict], existing: list[dict] | None = None) -> dict:
    """Add scraped leads that aren't already in the CRM. Returns counts."""
    existing = existing if existing is not None else db.list_leads()
    seen_urls = {l.get("source_url") for l in existing if l.get("source_url")}
    seen_addr = {normalize_address(l.get("address", "")) for l in existing}
    added = dupes = skipped = 0
    for l in found:
        addr = (l.get("address") or "").strip()
        if not addr:
            skipped += 1
            continue
        key = normalize_address(addr)
        if (l.get("source_url") and l["source_url"] in seen_urls) or (key and key in seen_addr):
            dupes += 1
            continue
        motivation, tags = classify(" ".join(str(l.get(k) or "") for k in ("address", "tags", "description")))
        if motivation and not l.get("motivation"):
            l["motivation"] = motivation
        if tags:
            l["tags"] = ",".join(t for t in [l.get("tags", "")] + tags if t)
        db.add_lead(l)
        added += 1
        if l.get("source_url"):
            seen_urls.add(l["source_url"])
        seen_addr.add(key)
    return {"added": added, "duplicates": dupes, "skipped": skipped}


# ---------------------------------------------------------------- message drafts (never auto-sent)
def _tel(phone: str) -> str:
    return re.sub(r"[^\d+]", "", phone or "")


def _first(name: str) -> str:
    return (name or "").split(" ")[0] or "there"


def seller_text(lead: dict, sender: str = "Amanda") -> str:
    o = (lead.get("owners") or [{}])[0]
    stage = lead.get("stage", "new")
    addr = lead.get("address", "your property")
    if stage == "new":
        return (f"Hi {_first(o.get('name', ''))}, this is {sender}. I'm a local buyer and I'm interested in {addr}. "
                f"I can buy as-is, pay cash and close on your timeline with no agent fees. Would you be open to a quick chat?")
    if stage in ("offer", "negotiation"):
        return (f"Hi {_first(o.get('name', ''))}, {sender} here following up on my offer for {addr}. "
                f"Happy to answer any questions or adjust the closing date to suit you. When's a good time to talk?")
    return (f"Hi {_first(o.get('name', ''))}, {sender} here checking in about {addr}. "
            f"Are you still thinking about selling? I can still make a cash offer, as-is, no fees.")


def buyer_blast(lead: dict) -> str:
    pe = db.payout_estimate(lead)
    parts = [f"Off-market deal: {lead.get('address', '')}, {lead.get('city', 'Winnipeg')}."]
    if lead.get("asking_price") or lead.get("offer_amount"):
        price = lead.get("offer_amount") or lead.get("asking_price")
        parts.append(f"Price ${float(price):,.0f}.")
    if lead.get("arv_estimate"):
        parts.append(f"ARV ~${float(lead['arv_estimate']):,.0f}.")
    if lead.get("repair_estimate"):
        parts.append(f"Repairs ~${float(lead['repair_estimate']):,.0f}.")
    if pe.get("ready") and pe.get("mao"):
        parts.append("Numbers work at 70% rule.")
    parts.append("Cash/quick close. Reply if you want the address details and a walkthrough.")
    return " ".join(parts)


def sms_link(phone: str, body: str) -> str:
    # iOS and Android both accept ?&body= / ?body=; '?&' covers both
    return f"sms:{_tel(phone)}?&body={quote(body)}"


def mail_link(email: str, subject: str, body: str) -> str:
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"


# ---------------------------------------------------------------- task planning (pure)
# days without activity before a lead in each stage needs a touch
CADENCE_DAYS = {"new": 1, "contacted": 3, "appointment": 1, "offer": 2, "negotiation": 1}
STALE_DAYS = 45
OPEN = ("new", "contacted", "appointment", "offer", "negotiation")


def _has_phone(lead: dict) -> bool:
    return any((o.get("phone") or "").strip() for o in lead.get("owners") or [])


def plan(leads: list[dict], calls: dict[int, list[dict]], outreach: dict[int, int], buyers: int,
         today: date | None = None, now: float | None = None) -> tuple[list[dict], list[dict]]:
    """Decide tasks and follow-up dates. Pure: returns (tasks, followups) without writing anything.

    tasks:     [{lead_id, kind, title, detail, priority}]
    followups: [{lead_id, date, note}]
    """
    today = today or date.today()
    now = now or time.time()
    tasks: list[dict] = []
    followups: list[dict] = []
    for l in leads:
        stage = l.get("stage", "new")
        if stage not in OPEN:
            continue
        lid = l["id"]
        score = db.lead_score(l)["score"]
        lc = calls.get(lid, [])
        last_touch = max([db.ts_of(l.get("updated_at"))] + [db.ts_of(c.get("called_at")) for c in lc] + [0])
        idle_days = (now - last_touch) / 86400 if last_touch else 999
        addr = l.get("address", f"Lead {lid}")
        pe = db.payout_estimate(l)

        if stage == "new" and not _has_phone(l):
            tasks.append({"lead_id": lid, "kind": "find_contact", "priority": 40 + score // 4,
                          "title": f"Find the owner's number: {addr}",
                          "detail": "Listing sites hide seller phones. Message through the listing, check the city assessment roll, or ask the listing agent, then add the contact."})
        elif stage == "new" and not lc:
            tasks.append({"lead_id": lid, "kind": "call_seller", "priority": 60 + score // 3,
                          "title": f"Call the seller: {addr}",
                          "detail": "Use the Cold Call script. If no answer, tap the text draft."})

        if stage != "new" and not pe["ready"]:
            tasks.append({"lead_id": lid, "kind": "analyze", "priority": 45 + score // 4,
                          "title": f"Run the numbers: {addr}",
                          "detail": "Add the ARV and repair estimate (Analyze this deal) so the spread and buyer matches work."})

        if stage in ("offer", "negotiation") and buyers and not outreach.get(lid):
            tasks.append({"lead_id": lid, "kind": "blast_buyers", "priority": 75 + score // 5,
                          "title": f"Send to matched buyers: {addr}",
                          "detail": "Deal is under offer. Line up your buyer now so you can assign fast."})

        cadence = CADENCE_DAYS.get(stage, 3)
        if idle_days >= cadence and not (l.get("next_followup") or "").strip():
            due = today if idle_days >= cadence * 2 else today + timedelta(days=1)
            followups.append({"lead_id": lid, "date": due.isoformat(),
                              "note": f"Auto: no activity for {int(min(idle_days, 999))} days ({db.STAGE_LABELS.get(stage, stage)})"})

        if stage in ("new", "contacted") and idle_days >= STALE_DAYS and lc:
            tasks.append({"lead_id": lid, "kind": "review_stale", "priority": 20,
                          "title": f"Still alive? {addr}",
                          "detail": f"No progress in {int(idle_days)} days. One last check-in text, then mark Closed Lost to keep the list clean."})
    tasks.sort(key=lambda t: -t["priority"])
    return tasks, followups


# ---------------------------------------------------------------- one full cycle
_lock = threading.Lock()


def run_cycle(trigger: str = "manual", scrape: bool = True, sources: tuple[str, ...] = AUTO_SOURCES) -> dict:
    """Run the whole automation once. Safe to call from several triggers (overlaps are skipped)."""
    if not _lock.acquire(blocking=False):
        return {"skipped": "another run is in progress"}
    started = time.time()
    summary: dict = {"trigger": trigger, "sources": {}, "errors": []}
    ok = True
    try:
        leads = db.list_leads()
        if scrape:
            for name in sources:
                if name not in SCRAPERS:
                    continue
                try:
                    found = run_scraper(name)
                    res = ingest(found, leads)
                    summary["sources"][name] = {"found": len(found), **res}
                    if res["added"]:
                        leads = db.list_leads()
                except Exception as e:  # one blocked source never stops the cycle
                    summary["sources"][name] = {"error": str(e)[:200]}
        # tag older leads that never got a deal type
        retagged = 0
        for l in leads:
            if not l.get("motivation"):
                m, tags = classify(" ".join(str(l.get(k) or "") for k in ("address", "tags")))
                if m:
                    db.update_lead_fields(l["id"], {"motivation": m})
                    l["motivation"] = m
                    retagged += 1
        summary["retagged"] = retagged

        calls = db.calls_by_lead()
        outreach = db.outreach_by_lead()
        buyers = len(db.list_buyers())
        tasks, followups = plan(leads, calls, outreach, buyers)
        made = 0
        for t in tasks:
            if db.add_task(t["lead_id"], t["kind"], t["title"], t["detail"], t["priority"]):
                made += 1
        for f in followups:
            try:
                db.set_followup(f["lead_id"], f["date"], f["note"])
            except Exception as e:
                summary["errors"].append(f"followup {f['lead_id']}: {e}"[:200])
        summary.update({"leads": len(leads), "tasks_created": made, "tasks_planned": len(tasks),
                        "followups_set": len(followups), "buyers": buyers})
    except Exception as e:
        ok = False
        summary["errors"].append(str(e)[:300])
        log.exception("automation cycle failed")
    finally:
        summary["seconds"] = round(time.time() - started, 1)
        try:
            db.log_run(started, trigger, summary, ok)
        except Exception:
            log.exception("could not log automation run")
        _lock.release()
    return summary


def today_queue(limit: int = 15) -> list[dict]:
    """Open tasks joined with their lead, each with a one-tap text/email draft where possible."""
    tasks = db.list_tasks("open", 500)
    if not tasks:
        return []
    leads = {l["id"]: l for l in db.list_leads()}
    out = []
    for t in tasks:
        lead = leads.get(t.get("lead_id"))
        if t.get("lead_id") and not lead:
            db.set_task_status(t["id"], "dismissed")   # lead was deleted
            continue
        if lead and lead.get("stage") in ("closed_won", "closed_lost"):
            db.set_task_status(t["id"], "done")        # deal finished: nothing left to do
            continue
        item = dict(t)
        item["lead"] = lead
        if lead:
            o = next((o for o in lead.get("owners") or [] if (o.get("phone") or "").strip()), None)
            if o and t["kind"] in ("call_seller", "review_stale"):
                item["sms"] = sms_link(o["phone"], seller_text(lead))
                item["tel"] = "tel:" + _tel(o["phone"])
            if t["kind"] == "blast_buyers":
                item["blast"] = buyer_blast(lead)
                emails = ",".join(b["email"] for b in db.match_buyers(lead) if (b.get("email") or "").strip())
                if emails:
                    item["mail"] = mail_link(emails, f"Off-market deal: {lead.get('address', '')}", item["blast"])
        out.append(item)
        if len(out) >= limit:
            break
    return out


def digest() -> dict:
    """Numbers for the dashboard / JSON API."""
    leads = db.list_leads()
    scores = [db.lead_score(l) for l in leads if l.get("stage") in OPEN]
    pipeline_value = sum(max(0, db.payout_estimate(l)["spread"]) for l in leads if l.get("stage") in OPEN)
    runs = db.list_runs(1)
    try:
        followups_due = len(db.due_followups())
    except Exception:
        # A broken follow-ups query must never 500 the digest / automation page.
        log.exception("digest: due_followups failed, reporting 0")
        followups_due = 0
    return {
        "open_leads": len(scores),
        "hot": sum(1 for s in scores if s["band"] == "hot"),
        "warm": sum(1 for s in scores if s["band"] == "warm"),
        "pipeline_spread": round(pipeline_value),
        "open_tasks": len(db.list_tasks("open", 1000)),
        "followups_due": followups_due,
        "last_run": runs[0] if runs else None,
    }
