-- Phase 5: error logging for the admin Error Monitoring Grid, an indexed
-- `profiles.role` for the admin user directory, and a denormalized email on
-- `profiles` (PostgREST doesn't expose `auth.users`, and the admin user
-- directory needs to show emails without a second GoTrue admin-API round trip).

create table public.error_logs (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  message text not null,
  created_at timestamptz not null default now()
);

alter table public.error_logs enable row level security;
-- Intentionally no policies — service-role only, same pattern as gmail_connections.

create index profiles_role_idx on public.profiles (role);

alter table public.profiles add column email text;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, name, email)
  values (new.id, new.raw_user_meta_data ->> 'name', new.email);
  return new;
end;
$$;

-- Backfill existing rows (harmless no-op on a fresh project with no users yet).
update public.profiles p
set email = u.email
from auth.users u
where p.id = u.id and p.email is null;
