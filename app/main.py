"""Wholesale Stack - FastAPI CRM for real-estate wholesaling. Phone-friendly."""
import os
import threading
import time

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db
from . import call_scripts, contracts
from .scrapers import SCRAPERS, run_scraper

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
        # drop __path from the query string
        q = "&".join(f"{k}={v}" for k, vs in request.query_params.multi_items()
                     for v in [vs] if k != "__path")
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


app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def _tab_for(path: str) -> str:
    if path.startswith("/scripts"):
        return "scripts"
    if path.startswith("/scrapers"):
        return "tools"
    if path.startswith("/contracts"):
        return "contracts"
    if path.startswith("/playbook"):
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
    return templates.TemplateResponse(request, "index.html", ctx(
        request, counts=db.pipeline_counts(), leads=db.list_leads()))


@app.get("/leads", response_class=HTMLResponse)
def leads_page(request: Request, stage: str = ""):
    leads = db.list_leads()
    if stage in db.STAGES:
        leads = [l for l in leads if l.get("stage") == stage]
    for l in leads:
        l["payout"] = db.payout_estimate(l)
        dt = db.DEAL_TYPES.get(l.get("motivation") or "standard", db.DEAL_TYPES["standard"])
        l["deal_label"] = dt["label"]
    return templates.TemplateResponse(request, "leads.html", ctx(request, leads=leads, active_stage=stage))


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
    ))


@app.post("/leads/new")
def create_lead(
    address: str = Form(...), city: str = Form("Winnipeg"), postal: str = Form(""),
    owner_name: str = Form(""), owner_phone: str = Form(""), owner_email: str = Form(""),
    asking_price: str = Form(""), tags: str = Form(""), motivation: str = Form(""),
    source: str = Form("manual"),
):
    lead = db.add_lead({
        "address": address, "city": city, "postal": postal, "source": source,
        "owner_name": owner_name, "owner_phone": owner_phone, "owner_email": owner_email,
        "asking_price": asking_price, "tags": tags, "motivation": motivation,
    })
    return RedirectResponse(f"/leads/{lead['id']}", status_code=303)


@app.post("/leads/{lead_id}/stage")
def change_stage(lead_id: int, to_stage: str = Form(...)):
    db.move_stage(lead_id, to_stage)
    return RedirectResponse(f"/leads/{lead_id}", status_code=303)


@app.post("/leads/{lead_id}/calls")
def add_call(lead_id: int, outcome: str = Form(...), notes: str = Form(""), duration_min: int = Form(0)):
    db.log_call(lead_id, outcome, notes, duration_min)
    return RedirectResponse(f"/leads/{lead_id}", status_code=303)


@app.post("/leads/{lead_id}/notes")
def add_note(lead_id: int, body: str = Form(...)):
    db.add_note(lead_id, body.strip())
    return RedirectResponse(f"/leads/{lead_id}", status_code=303)


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
        return {"ok": False, "error": str(e)}
    added = 0
    seen_urls = {l.get("source_url") for l in db.list_leads() if l.get("source_url")}
    for l in found:
        if l.get("address") and l.get("source_url") not in seen_urls:
            db.add_lead(l)
            added += 1
            if l.get("source_url"):
                seen_urls.add(l["source_url"])
    return RedirectResponse("/leads?stage=new", status_code=303)


@app.get("/health")
def health():
    return {"ok": True, "backend": db.backend_name(), "scrapers": list(SCRAPERS.keys())}


# ---------- built-in fallback scheduler (no-Docker mode) ----------

def _scheduler_loop():
    interval_h = float(os.environ.get("SCRAPE_INTERVAL_HOURS", "24"))
    while True:
        time.sleep(interval_h * 3600)
        for name in ("craigslist_winnipeg", "kijiji_winnipeg"):
            try:
                for l in run_scraper(name):
                    if l.get("address"):
                        db.add_lead(l)
            except Exception:
                pass  # scheduler never crashes the app


if os.environ.get("ENABLE_SCHEDULER", "0") == "1":
    threading.Thread(target=_scheduler_loop, daemon=True).start()
