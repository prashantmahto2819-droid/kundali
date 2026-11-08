-- Kundali platform: multi-tenant core schema (Supabase / Postgres)
-- Every user gets a personal organization automatically. Astrologers/institutes
-- can create shared organizations with several members. All private tables are
-- protected by Row Level Security keyed on organization membership.
-- NOTE: written for review; apply to a staging project first.

create table public.organizations (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  kind       text not null default 'personal' check (kind in ('personal','astrologer','institute')),
  created_at timestamptz not null default now()
);

create table public.org_members (
  org_id     uuid not null references public.organizations(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       text not null default 'member' check (role in ('owner','admin','member')),
  created_at timestamptz not null default now(),
  primary key (org_id, user_id)
);
create index on public.org_members (user_id);

-- Membership helpers (SECURITY DEFINER avoids recursive RLS on org_members)
create or replace function public.is_org_member(o uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.org_members m where m.org_id = o and m.user_id = auth.uid());
$$;

create or replace function public.is_org_admin(o uuid) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.org_members m
                 where m.org_id = o and m.user_id = auth.uid() and m.role in ('owner','admin'));
$$;

-- Personal organization on sign-up
create or replace function public.handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
declare o uuid;
begin
  insert into public.organizations (name, kind)
  values (coalesce(new.raw_user_meta_data->>'full_name', new.email, 'Personal'), 'personal')
  returning id into o;
  insert into public.org_members (org_id, user_id, role) values (o, new.id, 'owner');
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users for each row execute function public.handle_new_user();

-- People whose charts we compute (self, family, clients)
create table public.persons (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  created_by    uuid references auth.users(id) on delete set null,
  full_name     text not null,
  gender        text,
  birth_date    date not null,
  birth_time    time,
  birth_tz      text not null default 'Asia/Kolkata',
  birth_place   text,
  lat           numeric(9,6),
  lon           numeric(9,6),
  time_accuracy text not null default 'exact' check (time_accuracy in ('exact','approx','unknown')),
  notes         text,
  created_at    timestamptz not null default now()
);
create index on public.persons (org_id);

create table public.charts (
  id             uuid primary key default gen_random_uuid(),
  org_id         uuid not null references public.organizations(id) on delete cascade,
  person_id      uuid not null references public.persons(id) on delete cascade,
  engine_version text not null,
  backend        text not null,
  ayanamsa       text not null default 'lahiri',
  result         jsonb not null,
  computed_at    timestamptz not null default now()
);
create index on public.charts (org_id, person_id);

-- Palm photos are biometric-like personal data: explicit consent + auto-expiry
create table public.palm_scans (
  id            uuid primary key default gen_random_uuid(),
  org_id        uuid not null references public.organizations(id) on delete cascade,
  person_id     uuid references public.persons(id) on delete cascade,
  hand          text not null check (hand in ('left','right')),
  storage_path  text not null,                 -- private bucket path (Cloudflare R2 / Supabase Storage)
  consent_at    timestamptz not null,          -- must be set: no consent, no row
  delete_after  timestamptz,                   -- scheduled purge date
  analysis      jsonb,
  created_at    timestamptz not null default now()
);
create index on public.palm_scans (org_id);

-- Reviewed knowledge shared by everyone (read-only for end users)
create table public.rules (
  id            text primary key,
  category      text not null,
  definition    jsonb not null,                -- the "when" condition + texts
  source        jsonb not null,                -- text, chapter, verse
  review_status text not null default 'draft' check (review_status in ('draft','reviewed','rejected')),
  updated_at    timestamptz not null default now()
);

create table public.knowledge_chunks (
  id        uuid primary key default gen_random_uuid(),
  source    text not null,
  lang      text not null default 'hi',
  content   text not null,
  meta      jsonb not null default '{}'::jsonb
  -- embedding vector(1024)  -- add with: create extension vector; when the RAG phase starts
);

-- Plans are modelled now, payments are wired later
create table public.subscriptions (
  org_id             uuid primary key references public.organizations(id) on delete cascade,
  plan               text not null default 'free' check (plan in ('free','pro','astrologer','institute')),
  status             text not null default 'active',
  current_period_end timestamptz,
  provider           text,
  provider_ref       text
);

-- ---------------------------------------------------------------- RLS
alter table public.organizations    enable row level security;
alter table public.org_members      enable row level security;
alter table public.persons          enable row level security;
alter table public.charts           enable row level security;
alter table public.palm_scans       enable row level security;
alter table public.rules            enable row level security;
alter table public.knowledge_chunks enable row level security;
alter table public.subscriptions    enable row level security;

create policy org_select on public.organizations for select using (public.is_org_member(id));
create policy org_update on public.organizations for update using (public.is_org_admin(id));

create policy mem_select on public.org_members for select
  using (user_id = auth.uid() or public.is_org_member(org_id));
create policy mem_admin_write on public.org_members for all
  using (public.is_org_admin(org_id)) with check (public.is_org_admin(org_id));

create policy persons_all on public.persons for all
  using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy charts_all on public.charts for all
  using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy palm_all on public.palm_scans for all
  using (public.is_org_member(org_id)) with check (public.is_org_member(org_id) and consent_at is not null);

create policy rules_read on public.rules for select to authenticated using (review_status <> 'rejected');
create policy kb_read on public.knowledge_chunks for select to authenticated using (true);
create policy sub_read on public.subscriptions for select using (public.is_org_member(org_id));
-- rules / knowledge_chunks / subscriptions are written only by the service role (server side).
