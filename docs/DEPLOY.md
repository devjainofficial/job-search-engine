# Deployment guide

Three pieces to deploy: the **worker** (FastAPI), the **web** app (Next.js), and
the **scheduler** (GitHub Actions). Supabase is already live.

## Environment variables (reference)

| Var | Worker | Web | Scheduler | Value |
|-----|:--:|:--:|:--:|-------|
| SUPABASE_URL | ✓ | ✓ | ✓ | https://yalikbisvkyjuenvdmhr.supabase.co |
| SUPABASE_SERVICE_ROLE_KEY | ✓ | ✓ | ✓ | service_role JWT |
| GEMINI_API_KEY | ✓ | | ✓ | AI Studio key |
| TELEGRAM_BOT_TOKEN | ✓ | | ✓ | BotFather token |
| ADZUNA_APP_ID / ADZUNA_APP_KEY | ✓ | | ✓ | Adzuna dev keys |
| TELEGRAM_WEBHOOK_SECRET | ✓ | | | any random string (optional) |
| WORKER_URL | | ✓ | | the deployed worker URL |
| NEXT_PUBLIC_TELEGRAM_BOT_USERNAME | | ✓ | | DevJainBot |

> Before going public, rotate the keys that were shared in chat (service_role,
> Gemini, Adzuna). The repo never contains secrets.

## 1. Worker — Fly.io (recommended)

```sh
# one-time
iwr https://fly.io/install.ps1 -useb | iex   # install flyctl (PowerShell)
fly auth login

cd worker
fly launch --no-deploy            # reuses fly.toml; pick a unique app name
fly secrets set \
  SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... GEMINI_API_KEY=... \
  TELEGRAM_BOT_TOKEN=... ADZUNA_APP_ID=... ADZUNA_APP_KEY=... \
  TELEGRAM_WEBHOOK_SECRET=...
fly deploy
fly status                        # note the URL: https://<app>.fly.dev
curl https://<app>.fly.dev/health # -> {"status":"ok"}
```

Scales to zero when idle (near-free), cold-starts in ~1-3s, hosted in Mumbai.

### Worker — Render (alternative, truly free, slow cold start)
New → Blueprint → select this repo (uses `render.yaml`). Add the env vars in the
dashboard. Free plan sleeps after ~15 min idle (first request then takes ~30-60s).

## 2. Web — Vercel

1. vercel.com → Add New → Project → import the repo.
2. **Root Directory: `web`** (Next.js auto-detected).
3. Environment Variables: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
   `WORKER_URL=https://<app>.fly.dev`, `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=DevJainBot`.
4. Deploy → note your site URL.

## 3. Telegram one-tap connect (after the worker is live)

```sh
cd worker
# .env must have TELEGRAM_BOT_TOKEN (and TELEGRAM_WEBHOOK_SECRET if you set one).
# Telegram must be reachable (use a VPN if your ISP blocks it).
python scripts/set_webhook.py --url https://<app>.fly.dev
```

## 4. Scheduler — GitHub Actions

Repo → Settings → Secrets and variables → Actions → add: `SUPABASE_URL`,
`SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`,
`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`.

The daily job (`.github/workflows/daily-digest.yml`) then runs at 08:00 IST. Run
it on demand from the Actions tab → daily-digest → Run workflow.

## Smoke test after deploy
1. `GET https://<worker>/health` → ok.
2. Open the Vercel site → upload a resume, consent, submit → see detected roles.
3. Tap **Connect Telegram** → press Start → you get a confirmation message.
4. Actions → run daily-digest → a digest arrives on Telegram.
5. Dashboard (`/dashboard/<id>`) shows the sent jobs.

## Notes / hardening (later)
- Endpoints are unauthenticated (trusted-caller model). Add auth before public scale.
- Consider Supabase RLS once clients talk to the DB directly.
- Supabase free DB pauses after 7 days idle; the daily run keeps it warm.
