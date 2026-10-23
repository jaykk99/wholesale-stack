# Wholesale Stack

## Live URL

https://wholesale-stack.onrender.com

A wholesaling CRM for closing real estate deals from your phone. Lead scraping, pipeline tracking, call scripts, fillable contracts, and n8n automation, all in one place.

## What it does

- **Lead scraping engine** (`app/scrapers/`): polite, config-driven scrapers (Craigslist Winnipeg, Kijiji Winnipeg, Manitoba probate checklist, US county stub). Respects robots.txt, rate-limits, never logs in anywhere. Run on demand from the Scrapers page or on a schedule.
- **CRM** (FastAPI + phone-friendly pages): lead list with contact name + tap-to-call phone numbers, lead detail, pipeline stages (New Lead through Closed Won/Lost), call log, notes, tags.
- **Call scripts library**: cold call, follow-up, four objection handlers (price too low, just looking, spouse approval, timeline), making the offer, closing. The right script shows automatically on each lead page based on its pipeline stage.
- **Contracts**: fillable purchase agreement, assignment of contract, and earnest money receipt. Fields auto-fill from the deal (seller, property, price). Printable from the phone.
- **Deal Analyzer** (`/analyzer`, `app/analyzer.py`): interactive MAO calculator — ARV, asking, repairs, closing/holding costs, target fee → max offer, spread, and a deal/thin/tight/no-deal verdict with the full math shown. Prefills from any lead via "Analyze this deal".
- **Lead scoring**: every lead gets a 0-100 hot/warm/cold score (motivation + spread + phone + stage progress - stale penalty); `/leads?sort=score` sorts hottest first.
- **Follow-up reminders**: set a date + note on any lead; overdue follow-ups surface on the dashboard.
- **Automation**: docker-compose bundles n8n (Community Edition) with two example workflows (daily scrape to CRM, stale-lead follow-up reminders). No-Docker fallback: the app has its own tiny scheduler (`ENABLE_SCHEDULER=1`).
- **Tests**: `python3 -m pytest tests/` — 47 tests (access gate, crash reporting, analyzer math, payout, scoring, follow-ups, buyer matching, exit strategies).

## Lead sources (honest status, tested 2026-10-14)

- **Kijiji Winnipeg (house-for-sale category): WORKS.** Returns real listings with addresses, prices, and listing URLs. Respects robots.txt (category pages are allowed; individual ad pages and phone-lookup endpoints are disallowed and are never touched).
- **Craigslist Winnipeg: BLOCKED from datacenter IPs.** Returns 403 from server hosting IPs, and the HTML search is JS-rendered with no listings in markup. The module is kept because it may work from a home IP; it fails gracefully.
- **Manitoba probate / pre-foreclosure: MANUAL.** There is no reliable public scrapeable feed. The module returns a weekly manual checklist instead of fake leads.
- **US county records: STUB.** Set `WHOLESALE_US_COUNTY` and implement the county's search pattern to activate.

Note: listing sites do not publish seller names or phone numbers publicly. Scraped leads carry property details; mom adds the contact name/number when she reaches the seller, and every lead page shows them prominently with tap-to-call from then on.

## Where mom clicks

1. Open the app on her phone. The home screen shows the pipeline at a glance.
2. **Leads**: every lead shows the seller's name and a big green **Call** button that dials from her phone.
3. Open a lead: read the **script for this stage** right on the page, tap through pipeline stage buttons as the deal moves.
4. **Contracts**: pick a template, check the pre-filled fields, hit Generate, then Print / Save PDF.
5. **Scripts** tab: the full library anytime.

## Setup

### Quick local run

```bash
cd wholesale-stack
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # optional; blank .env = local SQLite mode
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000.

### Supabase backend (recommended)

1. In the Supabase dashboard for the **monico-agent** project, open the SQL editor and run `supabase/migrations/0001_wholesale.sql`.
2. In `.env`, set `SUPABASE_URL` and `SUPABASE_KEY` (service_role key, server-side only).
3. Restart the app. The footer shows `DB: supabase`.

### Docker + n8n

```bash
cp .env.example .env
docker compose up -d
```

App: http://localhost:8000. n8n: http://localhost:5678 (admin / changeme, change it).
Import the example workflows: n8n -> Workflows -> Import from file -> `n8n/workflows/*.json`.

### Deploy

- **Render**: new Web Service from this repo, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add `SUPABASE_URL` / `SUPABASE_KEY` in Render env vars. Free tier sleeps when idle.
- **Vercel**: this app is a long-running server, so Vercel's serverless model is a poor fit. Prefer Render (or any VPS) for this one.

## What Jay still needs to supply

- **Supabase project ref + service_role key** for the monico-agent project (for the hosted DB; local mode works without it).
- **WHOLESALE_BUYER_NAME / WHOLESALE_BUYER_COMPANY** in `.env` so contracts pre-fill the buyer side.
- **WHOLESALE_US_COUNTY** if the US county module should target a real county (otherwise it stays an inactive stub).
- A local lawyer should review the contract templates before real use. They are standard wholesaling templates, not legal advice.

## Notes

- No Twilio, no dialer hardware: the app shows tap-to-call `tel:` links so mom calls from her own phone. Call outcomes get logged back into the CRM manually.
- No Composio, no new paid services, no new API keys.

## Protecting the app and reporting crashes

- `APP_PASSWORD` (optional): turns on an HTTP Basic login for everything except `/health`, `/cron/run` and static files. Any username works.
- `ERROR_INBOX_URL` + `ERROR_INBOX_KEY` (optional): unhandled exceptions are sent to Error Inbox (`POST /api/v1/errors`, repo `jaykk99/wholesale-stack`), de-duped per crash site, max 20 per hour. Visitors see a plain "something went wrong" page instead of a stack trace.
