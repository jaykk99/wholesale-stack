-- Wholesale Stack schema for Supabase (monico-agent project).
-- Run in the Supabase SQL editor.

create table if not exists leads (
  id bigint generated always as identity primary key,
  address text not null,
  city text default 'Winnipeg',
  postal text default '',
  source text default 'manual',
  source_url text default '',
  tags text default '',
  asking_price numeric,
  arv_estimate numeric,
  repair_estimate numeric,
  motivation text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists owners (
  id bigint generated always as identity primary key,
  lead_id bigint not null references leads(id) on delete cascade,
  name text default '',
  phone text default '',
  email text default ''
);

create table if not exists deals (
  id bigint generated always as identity primary key,
  lead_id bigint not null unique references leads(id) on delete cascade,
  stage text default 'new'
    check (stage in ('new','contacted','appointment','offer','negotiation','closed_won','closed_lost')),
  offer_amount numeric,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists calls (
  id bigint generated always as identity primary key,
  lead_id bigint not null references leads(id) on delete cascade,
  outcome text default '',
  notes text default '',
  duration_min integer default 0,
  called_at timestamptz default now()
);

create table if not exists notes (
  id bigint generated always as identity primary key,
  lead_id bigint not null references leads(id) on delete cascade,
  body text not null,
  created_at timestamptz default now()
);

create table if not exists stage_history (
  id bigint generated always as identity primary key,
  lead_id bigint not null references leads(id) on delete cascade,
  from_stage text default '',
  to_stage text default '',
  changed_at timestamptz default now()
);

create table if not exists contracts (
  id bigint generated always as identity primary key,
  lead_id bigint not null references leads(id) on delete cascade,
  template_id text not null,
  fields_json jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create index if not exists leads_updated_idx on leads (updated_at desc);
create index if not exists deals_stage_idx on deals (stage);
create index if not exists owners_lead_idx on owners (lead_id);
create index if not exists calls_lead_idx on calls (lead_id);
create index if not exists notes_lead_idx on notes (lead_id);
create index if not exists contracts_lead_idx on contracts (lead_id);

-- The app talks to Supabase with the service_role key server-side,
-- which bypasses RLS. Enable RLS so anon keys get nothing by default.
alter table leads enable row level security;
alter table owners enable row level security;
alter table deals enable row level security;
alter table calls enable row level security;
alter table notes enable row level security;
alter table stage_history enable row level security;
alter table contracts enable row level security;
