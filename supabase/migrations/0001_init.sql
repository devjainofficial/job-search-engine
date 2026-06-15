-- Slice 1 schema: users, profiles, saved_searches, job_cache, sent_jobs.
-- Worker connects with the service-role key, so RLS / per-user auth policies are
-- deferred to the web slice. Until then only trusted server code touches these tables.

create extension if not exists "pgcrypto";

create table if not exists users (
    id               uuid primary key default gen_random_uuid(),
    email            text unique,
    -- nullable: seeded manually in slice 1, captured via bot onboarding later
    telegram_chat_id text,
    channel_prefs    jsonb not null default '{"telegram": true}'::jsonb,
    -- DPDP: timestamp of explicit upload consent (set by web slice)
    consent_at       timestamptz,
    created_at       timestamptz not null default now()
);

create table if not exists profiles (
    user_id          uuid primary key references users(id) on delete cascade,
    role_titles      text[] not null default '{}',
    skills           text[] not null default '{}',
    years_experience int,
    location         text,
    remote_pref      text,
    -- nullable after the raw file is deleted post-parse (DPDP storage limitation)
    raw_resume_path  text,
    -- parse-once marker: when set, the daily run never re-parses or calls the LLM
    parsed_at        timestamptz
);

create table if not exists saved_searches (
    id          uuid primary key default gen_random_uuid(),
    user_id     uuid not null references users(id) on delete cascade,
    query_terms text[] not null default '{}',
    location    text,
    filters     jsonb not null default '{}'::jsonb,
    active      boolean not null default true
);

create index if not exists saved_searches_user_idx on saved_searches(user_id);

-- Shared cache so a given query is fetched once per day and matched to many users
-- in memory (batch-by-shared-query rule), never refetched per user.
create table if not exists job_cache (
    canonical_key  text primary key,
    source         text not null,
    title          text not null,
    company        text not null,
    location       text,
    apply_url      text not null,
    -- which rung of the apply-link fallback ladder this URL is (direct_apply,
    -- job_detail, company_careers, source_search)
    apply_url_type text not null,
    posted_at      timestamptz,
    raw_payload    jsonb,
    fetched_at     timestamptz not null default now()
);

create index if not exists job_cache_fetched_at_idx on job_cache(fetched_at);

-- Dedup ledger. Composite PK enforces "never send the same job to the same user
-- twice" at the database level, not just in application code.
create table if not exists sent_jobs (
    user_id       uuid not null references users(id) on delete cascade,
    canonical_key text not null,
    sent_at       timestamptz not null default now(),
    channel       text not null default 'telegram',
    primary key (user_id, canonical_key)
);

create index if not exists sent_jobs_user_idx on sent_jobs(user_id);
