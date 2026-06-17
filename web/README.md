# Web (Next.js)

Resume-upload onboarding for the job digest. The browser posts the form to a
server route (service-role, no public bucket needed) that uploads the resume to
Supabase Storage, creates the user with explicit consent, then calls the worker
`/parse-resume` endpoint (parse-once lives in the Python service).

## Setup

```sh
cd web
npm install
cp .env.local.example .env.local   # fill in values
npm run dev                        # http://localhost:3000
```

`.env.local` needs:
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` (server only)
- `WORKER_URL` (the FastAPI worker, e.g. `http://localhost:8000`)
- `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` (for the connect link)

## Running the full flow locally
1. Start the worker: `cd worker && uvicorn app.main:app --port 8000`
2. Start the web app: `cd web && npm run dev`
3. Open http://localhost:3000, upload a resume, consent, submit.

Requires a Supabase Storage bucket named `resumes`.

## Deploy
Vercel (free Hobby). Set the same env vars in the Vercel project. Point
`WORKER_URL` at the deployed worker (Render/Railway).
