-- Lets the dashboard show *when* the next step (phone screen, take-home,
-- tech interview, ...) actually is, instead of just the bare status — the
-- Kanban board groups those three statuses into one "in process" column,
-- so this is how a card still says what/when the next step is.
alter table public.applications
  add column next_step_at timestamptz,
  add column next_step_note text;
