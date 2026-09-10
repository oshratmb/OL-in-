-- Phase 1: full schema (PRD §3.3) + RBAC + RLS.
-- Only `profiles` and `core_profiles` are used by Phase 1 application code;
-- the rest are created now so later phases don't need structural migrations.

create extension if not exists "pgcrypto";

create type public.user_role as enum ('regular', 'support', 'super_admin');

create type public.application_status as enum (
  'applied', 'phone_screen', 'homework', 'tech_interview', 'offer', 'rejected', 'on_hold'
);

-- profiles: extends auth.users 1:1 with app-specific fields Supabase doesn't hold.
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  name text,
  role public.user_role not null default 'regular',
  preferences jsonb not null default '{}'::jsonb,
  is_paused boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.core_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references public.profiles (id) on delete cascade,
  original_resume_url text,
  parsed_data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index core_profiles_user_id_idx on public.core_profiles (user_id);

create table public.jobs (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  company_name text not null,
  description text not null,
  url text,
  requirements jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  job_id uuid not null references public.jobs (id) on delete cascade,
  status public.application_status not null default 'applied',
  tailored_resume_url text,
  cover_letter_text text,
  applied_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index applications_user_id_idx on public.applications (user_id);
create index applications_job_id_idx on public.applications (job_id);

create table public.emails (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  application_id uuid references public.applications (id) on delete set null,
  gmail_message_id text unique,
  subject text,
  sender text,
  recipient text,
  body_content text,
  status_classified text,
  received_at timestamptz not null default now()
);
create index emails_user_id_idx on public.emails (user_id);
create index emails_application_id_idx on public.emails (application_id);

create table public.simulations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  application_id uuid not null references public.applications (id) on delete cascade,
  persona_details jsonb not null default '{}'::jsonb,
  chat_history jsonb not null default '[]'::jsonb,
  feedback_report text,
  created_at timestamptz not null default now()
);
create index simulations_user_id_idx on public.simulations (user_id);
create index simulations_application_id_idx on public.simulations (application_id);

-- Auto-create a profile row whenever a new auth user signs up.
create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, name)
  values (new.id, new.raw_user_meta_data ->> 'name');
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- keep updated_at current
create function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_set_updated_at before update on public.profiles
  for each row execute procedure public.set_updated_at();
create trigger core_profiles_set_updated_at before update on public.core_profiles
  for each row execute procedure public.set_updated_at();
create trigger applications_set_updated_at before update on public.applications
  for each row execute procedure public.set_updated_at();

-- RBAC helper: reads the caller's role without recursive RLS evaluation.
create function public.is_admin()
returns boolean
language sql
stable
security definer set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role in ('support', 'super_admin')
  );
$$;

create function public.is_super_admin()
returns boolean
language sql
stable
security definer set search_path = public
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'super_admin'
  );
$$;

-- RLS: owner-only by default, admin read-only where PRD §2.6 requires it.
alter table public.profiles enable row level security;
alter table public.core_profiles enable row level security;
alter table public.jobs enable row level security;
alter table public.applications enable row level security;
alter table public.emails enable row level security;
alter table public.simulations enable row level security;

create policy "own profile: select" on public.profiles for select using (auth.uid() = id or public.is_admin());
create policy "own profile: update" on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);

-- Supabase grants blanket UPDATE on all columns to `authenticated` by default;
-- RLS only scopes *rows*, not columns. Without this, the policy above would let
-- a user PATCH their own `role` to 'super_admin'. Only self-service columns are
-- grantable here — `role` changes go through the service-role ai-service backend.
revoke update on public.profiles from authenticated;
grant update (name, preferences, is_paused) on public.profiles to authenticated;

create policy "own core_profiles: all" on public.core_profiles for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "jobs: readable by authenticated" on public.jobs for select using (auth.role() = 'authenticated');
create policy "jobs: insert by authenticated" on public.jobs for insert with check (auth.role() = 'authenticated');

create policy "own applications: all" on public.applications for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own emails: all" on public.emails for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "own simulations: all" on public.simulations for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Storage: private per-user resume folders (resumes/{user_id}/...).
insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do nothing;

create policy "own resume files: all" on storage.objects for all
  using (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text);
