-- Automation engine: task queue + run log (matches the SQLite tables in app/db.py).
-- Run once in the Supabase SQL editor for the project the app's SUPABASE_URL points at.

create table if not exists ws_tasks (
  id bigint generated always as identity primary key,
  lead_id bigint references ws_leads(id) on delete cascade,
  kind text not null,
  title text not null,
  detail text default '',
  priority int default 50,
  status text default 'open',
  due date,
  created_at timestamptz default now(),
  done_at timestamptz
);
create index if not exists ws_tasks_open_idx on ws_tasks (status, priority desc);
create index if not exists ws_tasks_lead_idx on ws_tasks (lead_id);

create table if not exists ws_automation_runs (
  id bigint generated always as identity primary key,
  started_at timestamptz default now(),
  finished_at timestamptz,
  trigger text default 'manual',
  summary_json text default '{}',
  ok boolean default true
);

-- speed up the dashboard joins
create index if not exists ws_owners_lead_idx on ws_owners (lead_id);
create index if not exists ws_calls_lead_idx on ws_calls (lead_id, called_at desc);
create index if not exists ws_deals_lead_idx on ws_deals (lead_id);
