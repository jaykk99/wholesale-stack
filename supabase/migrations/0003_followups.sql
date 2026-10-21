-- Follow-up reminders on leads (matches SQLite _ensure_columns).
alter table ws_leads add column if not exists next_followup date;
alter table ws_leads add column if not exists followup_note text default '';
