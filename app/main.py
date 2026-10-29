"""Wholesale Stack - FastAPI CRM for real-estate wholesaling. Phone-friendly."""
import base64
import hmac
import logging
import os
import threading
import time
from urllib.parse import urlencode

from fastapi import FastAPI, Form, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from . import crypto_checkout
from . import analyzer as deal_analyzer
from . import automation, call_scripts, contracts, error_report, exits, training_md
from .scrapers import SCRAPERS, run_scraper

log = logging.getLogger("wholesale")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = FastAPI(title="Wholesale Stack")


@app.middleware("http")
async def _vercel_path_fix(request: Request, call_next):
    """Vercel's rewrite sends the rewritten path (/api/index...); restore the
    original from the __path query param so routes match. No-op elsewhere."""
    qp = request.query_params.get("__path")
    if qp:
        scope = request.scope
        scope["path"] = qp
        scope["raw_path"] = qp.encode()
        # drop __path from the query string (keep the remaining pairs percent-encoded)
        q = urlencode([(k, v) for k, v in request.query_params.multi_items() if k != "__path"])
        scope["query_string"] = q.encode()
    elif scope_path := request.scope.get("path", ""):
        if scope_path == "/api/index":
            request.scope["path"] = "/"
            request.scope["raw_path"] = b"/"
        elif scope_path.startswith("/api/index/"):
            np = scope_path[len("/api/index"):]
            request.scope["path"] = np
            request.scope["raw_path"] = np.encode()
    return await call_next(request)


# Open paths: health probe and the cron trigger (which checks its own secret).
_OPEN_PATHS = ("/health", "/cron/run", "/static/")


@app.middleware("http")
async def _access_gate(request: Request, call_next):
    """Optional HTTP Basic gate. Set APP_PASSWORD to protect the CRM (seller names
    and phone numbers); any username works. Unset = open, as before."""
    password = os.environ.get("APP_PASSWORD", "")
    path = request.scope.get("path", "")
    if password and not any(path == p or path.startswith(p) for p in _OPEN_PATHS):
        given = ""
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("basic "):
            try:
                given = base64.b64decode(auth[6:]).decode().partition(":")[2]
            except Exception:
                given = ""
        if not hmac.compare_digest(given.encode(), password.encode()):
            return JSONResponse({"ok": False, "error": "login required"}, status_code=401,
                                headers={"WWW-Authenticate": 'Basic realm="Wholesale Stack"'})
    return await call_next(request)


@app.middleware("http")
async def _report_crashes(request: Request, call_next):
    """Last line of defence: report the crash to Error Inbox and show a friendly page."""
    try:
        return await call_next(request)
    except Exception as exc:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        error_report.report(exc, request.method, request.url.path)
        return HTMLResponse("<h2>Something went wrong.</h2><p>It has been logged. "
                            "<a href='/'>Back to the dashboard</a></p>", status_code=500)


app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def _tab_for(path: str) -> str:
    if path.startswith("/scripts"):
        return "scripts"
    if path.startswith("/scrapers"):
        return "tools"
    if path.startswith("/contracts"):
        return "contracts"
    if path.startswith("/buyers"):
        return "buyers"
    if path.startswith("/training"):
        return "training"
    if path.startswith("/automation"):
        return "tools"
    if path.startswith("/playbook"):
        return "tools"
    if path.startswith("/analyzer"):
        return "tools"
    if path.startswith("/leads"):
        return "leads"
    return "home"


def ctx(request: Request, **kw):
    base = {"request": request, "stages": db.STAGES, "stage_labels": db.STAGE_LABELS,
            "backend": db.backend_name(), "tab": _tab_for(request.url.path),
            "deal_types": db.DEAL_TYPES}
    base.update(kw)
    return base


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    # The dashboard must never 500 because one backend query is slow/down
    # (e.g. Supabase REST timing out): degrade to an empty board and log it.
    try:
        counts = db.pipeline_counts()
        leads = db.list_leads()
        due = db.due_followups()
        data_error = ""
    except Exception:
        log.exception("dashboard: backend query failed, rendering degraded board")
        counts, leads, due = {}, [], []
        data_error = "Live data temporarily unavailable — showing an empty board."
    # the automation queue is a bonus: never let it take the dashboard down
    try:
        queue = automation.today_queue(12)
        runs = db.list_runs(1)
    except Exception:
        log.exception("dashboard: automation queue failed")
        queue, runs = [], []
    hot = []
    for l in leads:
        if l.get("stage") in automation.OPEN:
            sc = db.lead_score(l)
            if sc["band"] == "hot":
                hot.append({**l, "score": sc})
    hot.sort(key=lambda l: -l["score"]["score"])
    return templates.TemplateResponse(request, "index.html", ctx(
        request, counts=counts, leads=leads, due=due, data_error=data_error,
        queue=queue, last_run=runs[0] if runs else None, hot=hot[:5],
        tasks_ready=db.tasks_ready()))


@app.get("/leads", response_class=HTMLResponse)
def leads_page(request: Request, stage: str = "", sort: str = ""):
    leads = db.list_leads()
    if stage in db.STAGES:
        leads = [l for l in leads if l.get("stage") == stage]
    for l in leads:
        l["payout"] = db.payout_estimate(l)
        l["score"] = db.lead_score(l)
        dt = db.DEAL_TYPES.get(l.get("motivation") or "standard", db.DEAL_TYPES["standard"])
        l["deal_label"] = dt["label"]
    if sort == "score":
        leads.sort(key=lambda l: l["score"]["score"], reverse=True)
    return templates.TemplateResponse(request, "leads.html", ctx(
        request, leads=leads, active_stage=stage, sort=sort))


@app.get("/leads/new", response_class=HTMLResponse)
def new_lead_form(request: Request):
    return templates.TemplateResponse(request, "lead_new.html", ctx(request))


@app.get("/leads/{lead_id}", response_class=HTMLResponse)
def lead_detail(request: Request, lead_id: int):
    lead = db.get_lead(lead_id)
    if not lead:
        return HTMLResponse("Lead not found", status_code=404)
    dt = db.DEAL_TYPES.get(lead.get("motivation") or "standard", db.DEAL_TYPES["standard"])
    return templates.TemplateResponse(request, "lead_detail.html", ctx(
        request, lead=lead,
        scripts=call_scripts.scripts_for_stage(lead.get("stage", "new")),
        contract_templates=contracts.TEMPLATES,
        deal_type=dt,
        payout=db.payout_estimate(lead),
        matched_buyers=db.match_buyers(lead),
        outreach=db.buyer_outreach_for_lead(lead_id),
        exits=exits.exit_strategies(lead),
        buyers_ready=db.buyers_ready(),
        drafts=_drafts_for(lead),
        score=db.lead_score(lead),
    ))


def _drafts_for(lead: dict) -> dict:
    """Ready-to-send seller text / buyer blast for the lead page (opened in the phone's own apps)."""
    out = {"seller_text": automation.seller_text(lead), "buyer_blast": automation.buyer_blast(lead)}
    o = next((o for o in lead.get("owners") or [] if (o.get("phone") or "").strip()), None)
    if o:
        out["seller_sms"] = automation.sms_link(o["phone"], out["seller_text"])
    em = next((o for o in lead.get("owners") or [] if (o.get("email") or "").strip()), None)
    if em:
        out["seller_mail"] = automation.mail_link(em["email"], f"About {lead.get('address', 'your property')}", out["seller_text"])
    return out


@app.post("/leads/new")
def create_lead(
    address: str = Form(...), city: str = Form("Winnipeg"), postal: str = Form(""),
    owner_name: str = Form(""), owner_phone: str = Form(""), owner_email: str = Form(""),
    asking_price: str = Form(""), tags: str = Form(""), motivation: str = Form(""),
    source: str = Form("manual"),
):
    if not motivation:
        motivation, _ = automation.classify(f"{address} {tags}")
    lead = db.add_lead({
        "address": address, "city": city, "postal": postal, "source": source,
        "owner_name": owner_name, "owner_phone": owner_phone, "owner_email": owner_email,
        "asking_price": asking_price, "tags": tags, "motivation": motivation,
    })
    return RedirectResponse(f"/leads/{lead['id']}", status_code=303)


@app.post("/leads/{lead_id}/stage")
def change_stage(lead_id: int, to_stage: str = Form(...)):
    db.move_stage(lead_id, to_stage)
    _safe(db.close_tasks_for_lead, lead_id, ("call_seller", "find_contact") if to_stage != "new" else ())
    if to_stage in ("closed_won", "closed_lost"):
        _safe(db.close_tasks_for_lead, lead_id, ("call_seller", "find_contact", "analyze", "blast_buyers", "review_stale"))
    return RedirectResponse(f"/leads/{lead_id}", status_code=303)


def _safe(fn, *a):
    try:
        fn(*a)
    except Exception:
        log.exception("automation side effect failed: %s", getattr(fn, "__name__", fn))


@app.post("/leads/{lead_id}/calls")
def add_call(lead_id: int, outcome: str = Form(...), notes: str = Form(""), duration_min: int = Form(0)):
    db.log_call(lead_id, outcome, notes, duration_min)
    _safe(db.close_tasks_for_lead, lead_id, ("call_seller", "review_stale"))
    # a call satisfies an automatic follow-up reminder; manual reminders stay until changed
    lead = db.get_lead(lead_id) or {}
    if (lead.get("followup_note") or "").startswith("Auto:"):
        _safe(db.set_followup, lead_id, "", "")
    return RedirectResponse(f"/leads/{lead_id}", status_code=303)


@app.post("/leads/{lead_id}/notes")
def add_note(lead_id: int, body: str = Form(...)):
    db.add_note(lead_id, body.strip())
    return RedirectResponse(f"/leads/{lead_id}", status_code=303)


@app.post("/leads/{lead_id}/followup")
def set_followup(lead_id: int, next_followup: str = Form(""), followup_note: str = Form("")):
    try:
        db.set_followup(lead_id, next_followup, followup_note)
    except ValueError:
        # Bad date, or follow-ups not enabled on the DB yet (migration 0003):
        # back to the lead page either way, never a raw 500.
        log.exception("set_followup rejected for lead %s", lead_id)
    return RedirectResponse(f"/leads/{lead_id}", status_code=303)


# ---------------- Deal analyzer ----------------

@app.get("/analyzer", response_class=HTMLResponse)
def analyzer_page(request: Request, lead_id: int = 0):
    prefill = {}
    if lead_id:
        lead = db.get_lead(lead_id)
        if lead:
            prefill = {
                "arv": lead.get("arv_estimate") or "",
                "asking": lead.get("asking_price") or "",
                "repairs": lead.get("repair_estimate") or "",
                "address": lead.get("address") or "",
                "lead_id": lead_id,
            }
    return templates.TemplateResponse(request, "analyzer.html", ctx(
        request, prefill=prefill, result=None, fmt=deal_analyzer.fmt))


@app.post("/analyzer", response_class=HTMLResponse)
def analyzer_run(
    request: Request,
    arv: str = Form(""), asking: str = Form(""), repairs: str = Form(""),
    closing_costs: str = Form(""), holding_costs: str = Form(""),
    desired_fee: str = Form("10000"), address: str = Form(""),
):
    result = deal_analyzer.analyze(arv, asking, repairs, closing_costs, holding_costs, desired_fee)
    lead_id = int(request.query_params.get("lead_id") or 0)
    if lead_id and deal_analyzer.parse_money(arv):
        # remember the numbers on the lead so scoring, buyer matching and the queue use them
        _safe(db.update_lead_fields, lead_id, {k: v for k, v in {
            "arv_estimate": deal_analyzer.parse_money(arv) or None,
            "repair_estimate": deal_analyzer.parse_money(repairs) or None,
            "asking_price": deal_analyzer.parse_money(asking) or None}.items() if v})
        _safe(db.close_tasks_for_lead, lead_id, ("analyze",))
    prefill = {"arv": arv, "asking": asking, "repairs": repairs,
               "closing_costs": closing_costs, "holding_costs": holding_costs,
               "desired_fee": desired_fee, "address": address, "lead_id": lead_id}
    return templates.TemplateResponse(request, "analyzer.html", ctx(
        request, prefill=prefill, result=result, fmt=deal_analyzer.fmt))


@app.get("/scripts", response_class=HTMLResponse)
def scripts_library(request: Request):
    return templates.TemplateResponse(request, "scripts.html", ctx(request, scripts=call_scripts.SCRIPTS))


@app.get("/leads/{lead_id}/contracts/{template_id}", response_class=HTMLResponse)
def contract_form(request: Request, lead_id: int, template_id: str):
    lead = db.get_lead(lead_id)
    tmpl = contracts.get_template(template_id)
    if not lead or not tmpl:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(request, "contract_form.html", ctx(
        request, lead=lead, tmpl=tmpl, values=contracts.autofill_values(tmpl, lead)))


@app.post("/leads/{lead_id}/contracts/{template_id}", response_class=HTMLResponse)
async def contract_generate(request: Request, lead_id: int, template_id: str):
    lead = db.get_lead(lead_id)
    tmpl = contracts.get_template(template_id)
    if not lead or not tmpl:
        return HTMLResponse("Not found", status_code=404)
    form = await request.form()
    values = {f["name"]: form.get(f["name"], "") for f in tmpl["fields"]}
    db.save_contract(lead_id, template_id, values)
    html = contracts.render_contract(tmpl, values)
    return templates.TemplateResponse(request, "contract_print.html", ctx(
        request, lead=lead, tmpl=tmpl, contract_html=html, values=values))


@app.get("/contracts", response_class=HTMLResponse)
def contracts_page(request: Request):
    allc = db.list_all_contracts()
    return templates.TemplateResponse(request, "contracts.html", ctx(
        request, contracts=allc,
        grouped=contracts.templates_by_category(),
        template_count=len(contracts.TEMPLATES)))


@app.get("/contracts/new/{template_id}", response_class=HTMLResponse)
def contract_pick_lead(request: Request, template_id: str):
    tmpl = contracts.get_template(template_id)
    if not tmpl:
        return HTMLResponse("Not found", status_code=404)
    leads = db.list_leads()
    return templates.TemplateResponse(request, "contract_pick_lead.html", ctx(
        request, tmpl=tmpl, leads=leads))


@app.get("/playbook", response_class=HTMLResponse)
def playbook_page(request: Request):
    return templates.TemplateResponse(request, "playbook.html", ctx(request))


@app.get("/training", response_class=HTMLResponse)
def training_page(request: Request):
    guide_path = os.path.join(BASE_DIR, "AMANDA_TRAINING_GUIDE.md")
    try:
        with open(guide_path, encoding="utf-8") as f:
            md = f.read()
    except OSError:
        md = "# Training Guide\n\nGuide file not found."
    return templates.TemplateResponse(request, "training.html",
                                      ctx(request, guide_html=training_md.render(md)))


@app.get("/scrapers", response_class=HTMLResponse)
def scrapers_page(request: Request):
    info = []
    for name, cls in SCRAPERS.items():
        inst = cls()
        info.append({"name": name, "active": True,
                     "note": getattr(inst, "target_county", None) == "" and name == "us_county_stub"
                             and "needs WHOLESALE_US_COUNTY" or ""})
    return templates.TemplateResponse(request, "scrapers.html", ctx(request, scrapers=info))


@app.post("/scrapers/{name}/run")
async def run_scraper_endpoint(request: Request, name: str):
    form = await request.form()
    try:
        found = run_scraper(name, **{k: v for k, v in form.items()})
    except Exception as e:
        log.exception("scraper %s failed", name)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)
    automation.ingest(found)   # de-dupes by URL and address, auto-tags deal type
    return RedirectResponse("/leads?stage=new", status_code=303)


@app.get("/health")
def health():
    return {"ok": True, "backend": db.backend_name(), "scrapers": list(SCRAPERS.keys())}


# ---------------- Crypto checkout (vendored paywatch) ----------------

def _crypto_watcher():
    return crypto_checkout.get_watcher()


def _crypto_error(exc):
    return JSONResponse(crypto_checkout.watcher_error_payload(exc),
                        status_code=getattr(exc, "status_code", 400))


@app.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request):
    watcher = _crypto_watcher()
    plans = [p.as_dict() for p in watcher.plans.values()]
    assets = []
    try:
        import sys
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        from paywatch.assets import get_asset, supported_assets
        for key in supported_assets():
            spec = get_asset(key)
            assets.append({"key": key, "symbol": spec.symbol,
                           "name": spec.display_name,
                           "confirmations": spec.default_confirmations,
                           "pool_size": len(watcher.pool_for(key))})
    except Exception:
        log.exception("checkout page: asset registry failed")
    return templates.TemplateResponse(request, "checkout.html", ctx(
        request, plans=plans, assets=assets,
        placeholder=crypto_checkout.plans_are_placeholder(watcher.plans)))


@app.get("/api/crypto/plans")
def api_crypto_plans():
    watcher = _crypto_watcher()
    return {
        "plans": [p.as_dict() for p in watcher.plans.values()],
        "placeholder_pricing": crypto_checkout.plans_are_placeholder(watcher.plans),
        "assets": [{"asset": key, "pool_size": len(watcher.pool_for(key))}
                   for key in ("btc", "eth", "bnb", "sol")],
        "invoice_minutes": 60, "tolerance_pct": 1.0,
    }


@app.get("/api/crypto/assets")
def api_crypto_assets():
    # Live availability: probes price and chain providers per asset.
    return {"assets": _crypto_watcher().asset_statuses()}


@app.post("/api/crypto/orders")
async def api_crypto_create_order(request: Request):
    from paywatch.watcher import WatcherError
    body = await request.json()
    try:
        order = _crypto_watcher().create_order(
            body["plan_id"], body["payer_address"],
            buyer_ref=body.get("buyer_ref", ""),
            asset=body.get("asset", "btc"))
    except WatcherError as exc:
        return _crypto_error(exc)
    except KeyError as exc:
        return JSONResponse({"error": f"missing field: {exc}"}, status_code=400)
    return order.public()


@app.get("/api/crypto/orders/{order_id}")
def api_crypto_get_order(order_id: str):
    order = _crypto_watcher().get_order(order_id)
    if order is None:
        return JSONResponse({"error": f"unknown order: {order_id}"}, status_code=404)
    return order.public()


@app.post("/api/crypto/orders/{order_id}/check")
def api_crypto_check_order(order_id: str):
    from paywatch.watcher import WatcherError
    try:
        return _crypto_watcher().check_order(order_id)
    except WatcherError as exc:
        return _crypto_error(exc)


@app.post("/api/crypto/orders/{order_id}/approve")
async def api_crypto_approve_order(request: Request, order_id: str):
    from paywatch.watcher import WatcherError
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    try:
        return _crypto_watcher().approve_order(
            order_id, owner_secret=(body or {}).get("owner_secret"))
    except WatcherError as exc:
        return _crypto_error(exc)


@app.post("/api/crypto/sweep")
def api_crypto_sweep():
    return _crypto_watcher().sweep()


@app.get("/api/crypto/entitlements")
def api_crypto_entitlements():
    return {"entitlements": crypto_checkout.list_entitlements()}


# ---------------- Buyers CRM ----------------

@app.get("/buyers", response_class=HTMLResponse)
def buyers_page(request: Request):
    return templates.TemplateResponse(request, "buyers.html", ctx(
        request, buyers=db.list_buyers(), buyers_ready=db.buyers_ready(),
        buyer_types=db.BUYER_TYPES))


@app.get("/buyers/new", response_class=HTMLResponse)
def new_buyer_form(request: Request):
    return templates.TemplateResponse(request, "buyer_form.html", ctx(
        request, buyer=None, buyer_types=db.BUYER_TYPES))


@app.post("/buyers/new")
def create_buyer(
    name: str = Form(...), phone: str = Form(""), email: str = Form(""),
    company: str = Form(""), buyer_type: str = Form("cash_buyer"),
    target_areas: str = Form(""), min_price: str = Form(""), max_price: str = Form(""),
    property_types: str = Form(""), notes: str = Form(""),
):
    b = db.add_buyer({"name": name, "phone": phone, "email": email, "company": company,
                      "buyer_type": buyer_type, "target_areas": target_areas,
                      "min_price": min_price, "max_price": max_price,
                      "property_types": property_types, "notes": notes})
    if b:
        return RedirectResponse(f"/buyers/{b['id']}", status_code=303)
    return RedirectResponse("/buyers", status_code=303)


@app.get("/buyers/{buyer_id}", response_class=HTMLResponse)
def buyer_detail(request: Request, buyer_id: str):
    b = db.get_buyer(buyer_id)
    if not b:
        return HTMLResponse("Buyer not found", status_code=404)
    return templates.TemplateResponse(request, "buyer_form.html", ctx(
        request, buyer=b, buyer_types=db.BUYER_TYPES))


@app.post("/buyers/{buyer_id}/edit")
def edit_buyer(
    buyer_id: str, name: str = Form(...), phone: str = Form(""), email: str = Form(""),
    company: str = Form(""), buyer_type: str = Form("cash_buyer"),
    target_areas: str = Form(""), min_price: str = Form(""), max_price: str = Form(""),
    property_types: str = Form(""), notes: str = Form(""),
):
    db.update_buyer(buyer_id, {"name": name, "phone": phone, "email": email, "company": company,
                               "buyer_type": buyer_type, "target_areas": target_areas,
                               "min_price": min_price, "max_price": max_price,
                               "property_types": property_types, "notes": notes})
    return RedirectResponse(f"/buyers/{buyer_id}", status_code=303)


@app.post("/buyers/{buyer_id}/delete")
def remove_buyer(buyer_id: str):
    db.delete_buyer(buyer_id)
    return RedirectResponse("/buyers", status_code=303)


@app.post("/leads/{lead_id}/buyers/{buyer_id}/contact")
def contact_buyer(lead_id: int, buyer_id: str, channel: str = Form("call")):
    db.log_buyer_contact(lead_id, buyer_id, channel)
    return RedirectResponse(f"/leads/{lead_id}", status_code=303)


# ---------------- Automation ----------------

@app.get("/automation", response_class=HTMLResponse)
def automation_page(request: Request, ran: str = ""):
    return templates.TemplateResponse(request, "automation.html", ctx(
        request, runs=db.list_runs(15), digest=automation.digest(), tasks_ready=db.tasks_ready(),
        interval=_interval_h(), enabled=_scheduler_on(), cron_set=bool(os.environ.get("CRON_SECRET")),
        sources=automation.AUTO_SOURCES, ran=ran))


@app.post("/automation/run")
def automation_run_now(scrape: str = Form("1")):
    s = automation.run_cycle("manual", scrape=scrape == "1")
    return RedirectResponse("/automation?ran=1" if "skipped" not in s else "/automation?ran=busy", status_code=303)


@app.post("/tasks/{task_id}/done")
def task_done(task_id: int, back: str = Form("/")):
    db.set_task_status(task_id, "done")
    return RedirectResponse(back if back.startswith("/") else "/", status_code=303)


@app.post("/tasks/{task_id}/dismiss")
def task_dismiss(task_id: int, back: str = Form("/")):
    db.set_task_status(task_id, "dismissed")
    return RedirectResponse(back if back.startswith("/") else "/", status_code=303)


@app.post("/cron/run")
async def cron_run(request: Request):
    """External trigger (GitHub Actions / n8n / any cron). Needs the CRON_SECRET."""
    secret = os.environ.get("CRON_SECRET", "")
    given = request.headers.get("x-cron-secret") or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not secret or given != secret:
        return JSONResponse({"ok": False, "error": "forbidden"}, status_code=403)
    summary = await run_in_threadpool(automation.run_cycle, "cron")
    return {"ok": True, "summary": summary}


@app.get("/api/digest")
def api_digest():
    d = automation.digest()
    return {"ok": True, **d}


# ---------- built-in scheduler (on by default; the app runs the automation itself) ----------

def _interval_h() -> float:
    try:
        return max(0.5, float(os.environ.get("AUTOMATION_INTERVAL_HOURS") or os.environ.get("SCRAPE_INTERVAL_HOURS") or 6))
    except ValueError:
        return 6.0


def _scheduler_on() -> bool:
    # new name AUTOMATION, old name ENABLE_SCHEDULER; default on
    v = os.environ.get("AUTOMATION", os.environ.get("ENABLE_SCHEDULER", "1"))
    return v not in ("0", "false", "off", "")


def _scheduler_loop():
    time.sleep(90)  # let the app finish booting
    while True:
        try:
            automation.run_cycle("scheduler")
        except Exception:
            log.exception("scheduled automation failed")  # scheduler never crashes the app
        time.sleep(_interval_h() * 3600)


if _scheduler_on() and not os.environ.get("VERCEL") and not os.environ.get("PYTEST_CURRENT_TEST") and "pytest" not in os.sys.modules:
    threading.Thread(target=_scheduler_loop, daemon=True, name="automation").start()
