-- Phase 3: Gmail refresh tokens. Never exposed to any client, not even the
-- owning user — RLS is enabled with zero policies, so only the service-role
-- key (used exclusively by ai-service) can touch this table.

create table public.gmail_connections (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  refresh_token text not null,
  google_email text,
  last_synced_at timestamptz,
  needs_reconnect boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.gmail_connections enable row level security;
-- Intentionally no policies: RLS with zero policies denies all access to
-- anon/authenticated roles by default; only the service-role key bypasses RLS.
