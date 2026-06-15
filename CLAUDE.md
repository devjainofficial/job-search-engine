# CLAUDE.md

## What we are building
A shareable, multi-user job-search automation service. A user uploads a resume, we extract their role, skills, and location into a structured profile, store it, run a daily job search across multiple sources, and push matched jobs (with the closest-to-apply link we can get) to them over Telegram. India-leaning, also covers remote and global roles. Free to users, so the build must stay near zero cost into the low hundreds of users.

Full strategy and source research lives in `docs/RESEARCH.md`. Read it before making any architectural decision.

## Stack (locked, do not swap without asking)
- Frontend and resume upload: Next.js (App Router) on Vercel
- Backend worker: Python and FastAPI on Render or Railway
- Database, file storage, auth: Supabase (Postgres, Storage)
- Scheduler: Supabase Cron (pg_cron) or GitHub Actions cron, calling a FastAPI `/run-daily` endpoint
- Resume parsing: Gemini 2.5 Flash-Lite via LiteLLM
- Notifications: Telegram Bot API first. Email (Resend) is a later phase. WhatsApp is out of scope for now.

## Non-negotiable constraints
1. API and ATS sources only. Do NOT scrape LinkedIn, Naukri, Indeed, Foundit, or any login-walled board. If a source needs scraping behind auth or fake accounts, it is out of scope.
2. Cost minimization is a feature. Prefer free tiers. Add a code comment anywhere a paid tier would eventually be required.
3. Personal data discipline (India DPDP Act). Collect explicit consent at upload. Store extracted keywords. Treat the raw resume file as deletable after parsing. Provide delete-my-data. Encrypt at rest. No personal data in URLs or logs.

## Three architectural rules to build in from day one
These are cheap now and painful to retrofit. Get them right in the schema and the worker design.
1. Parse once, cache forever. Parse each resume a single time and store the structured result. Never call the LLM on a daily run.
2. Dedup with a sent_jobs table. Key every job to a canonical id: lowercased company plus normalized title plus location, plus a fuzzy hash of the description. Store (user_id, canonical_key) in sent_jobs. Never send the same job to the same user twice, across sources or across days.
3. Batch by shared query. Do NOT loop per user per source. Group users by (role cluster plus location), fetch each distinct query once per day, cache it, then match cached jobs to users in memory. 500 users must not mean 5,000 API calls.

## Data model (starting point)
- users: id, auth info, telegram_chat_id, channel_prefs, consent_at, created_at
- profiles: user_id, role_titles[], skills[], years_experience, location, remote_pref, raw_resume_path (nullable after deletion), parsed_at
- saved_searches: id, user_id, query_terms, location, filters, active
- job_cache: canonical_key, source, title, company, location, apply_url, apply_url_type, posted_at, raw_payload, fetched_at
- sent_jobs: user_id, canonical_key, sent_at, channel

## Job sources (tiers)
1. Free, no key: Remotive, RemoteOK, Arbeitnow (remote and global)
2. Free key: Adzuna (India and global), Jooble, Careerjet
3. ATS public JSON (the apply-link backbone, all free, no auth). Apply-link field per source:
   - Greenhouse: absolute_url
   - Lever: applyUrl
   - Ashby: applyUrl
   - Workable: application_url
   - SmartRecruiters: applyUrl or jobAdUrl
   - Recruitee: careers_apply_url
4. Paid, only if needed: JSearch or SerpApi (Google Jobs, returns apply_options[]). Behind a flag, off by default.

## Apply-link fallback ladder
Always send the best available, and label which type it is:
1. Direct apply URL (ATS)
2. Job detail or posting page
3. Company careers page
4. Source search deep link

## Build order
Work in vertical slices, smallest first. Do not build a whole phase at once.
- Slice 1: repo scaffold, Supabase schema, one source (Remotive), resume parse, one Telegram digest end to end, sent_jobs dedup.
- Then: add ATS sources, add saved-search matching, add Adzuna for India.
- Then: email channel, consent flow and delete-my-data, shared-query batching at scale.
See `docs/RESEARCH.md` for the full phased plan.

## Coding conventions
- One source adapter per file, all returning the same canonical job shape and setting apply_url_type.
- Keep functions small and single-purpose.
- Type everything: TypeScript on the frontend, Python type hints and pydantic on the backend.
- Handle rate limits: back off on HTTP 429, respect documented limits (Lever about 10/s, Workable 10 per 10s).
- Write a test for the canonical-key dedup logic before trusting it.

## Style
- No em dashes anywhere: in code comments, docs, or commit messages. Use commas or parentheses.
- Commit messages: short, imperative, present tense.
- Comments explain why, not what.

## When unsure
Ask before: swapping any stack component, adding a paid dependency, adding a new field that holds personal data, or introducing scraping of any kind.
