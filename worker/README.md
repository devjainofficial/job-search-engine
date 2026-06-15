# Worker (FastAPI)

Slice 1 backend: parse a resume once, fetch Remotive, match jobs to a user, dedup
via `sent_jobs`, and push a Telegram digest. No web UI yet (worker-first).

## Setup

```sh
cd worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # PowerShell
pip install -r requirements.txt
```

Create `worker/.env` from the repo-root `.env.example` and fill in:
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`.

## Apply the schema

Run `supabase/migrations/0001_init.sql` against your Supabase project
(SQL editor or `psql`). Confirm 5 tables: `users`, `profiles`, `saved_searches`,
`job_cache`, `sent_jobs`.

## Seed yourself (slice 1, manual)

1. Message your Telegram bot once (so it can DM you), then get your `chat_id`
   (e.g. via `https://api.telegram.org/bot<token>/getUpdates`).
2. Insert a user with that `telegram_chat_id`:
   ```sql
   insert into users (email, telegram_chat_id) values ('you@example.com', '<chat_id>');
   ```
3. (Optional) Add a saved search; otherwise the query is derived from your
   resume's first role title:
   ```sql
   insert into saved_searches (user_id, query_terms)
   values ('<user_id>', array['python','backend']);
   ```

## Run

```sh
# 1. Tests (dedup logic)
pytest

# 2. Parse a resume once -> profiles row
python scripts/parse_resume.py --file path\to\resume.pdf --user-id <user_id>

# 3. Daily run -> caches jobs, sends digest, records sent_jobs
python scripts/run_daily.py

# Or serve the API and POST /run-daily
uvicorn app.main:app --reload
```

Run `run_daily.py` twice: the second run should send nothing (dedup working).
