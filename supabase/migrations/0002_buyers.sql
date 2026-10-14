-- Buyers CRM for Wholesale Stack (monico-agent project).
-- Run once in the Supabase SQL editor.

create table if not exists ws_buyers (
  id bigint generated always as identity primary key,
  name text not null,
  phone text default '',
  email text default '',
  company text default '',
  buyer_type text default 'cash_buyer',
  target_areas text default '',
  min_price numeric,
  max_price numeric,
  property_types text default '',
  notes text default '',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists ws_buyer_outreach (
  id bigint generated always as identity primary key,
  lead_id bigint not null references ws_leads(id) on delete cascade,
  buyer_id bigint not null references ws_buyers(id) on delete cascade,
  channel text default 'call',
  contacted_at timestamptz default now()
);

create index if not exists ws_buyer_outreach_lead_idx on ws_buyer_outreach (lead_id);
