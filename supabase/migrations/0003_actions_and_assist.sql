-- Per-user-per-job state: save, thumbs feedback, and application status.
-- Snapshot the display fields so saved/applied jobs still render after the
-- shared job_cache is pruned. Keyed by canonical_key (the dedup identity).
create table if not exists job_actions (
    user_id        uuid not null references users(id) on delete cascade,
    canonical_key  text not null,
    saved          boolean not null default false,
    feedback       text,   -- 'up' | 'down' | null
    status         text,   -- null | 'applied' | 'interviewing' | 'rejected' | 'offer'
    title          text,
    company        text,
    location       text,
    apply_url      text,
    apply_url_type text,
    source         text,
    updated_at     timestamptz not null default now(),
    primary key (user_id, canonical_key)
);

create index if not exists job_actions_user_idx on job_actions(user_id);

-- Store the description so AI apply-assist can use it without re-fetching.
alter table job_cache add column if not exists description text;

-- Monthly counters to keep paid/free API tiers (JSearch, SerpApi) under cap.
create table if not exists api_usage (
    provider text not null,
    yyyymm   text not null,
    count    integer not null default 0,
    primary key (provider, yyyymm)
);
