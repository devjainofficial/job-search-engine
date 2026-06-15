# Building a Shareable, Multi-User Job-Search Automation Service: Architecture, Costs, and Execution Plan

## TL;DR
- **Build a small custom cloud backend (Next.js + Python/FastAPI worker + Supabase Postgres), not n8n or a browser extension.** n8n is single-tenant by design and breaks logically as a multi-user public product; a browser extension or desktop app cannot run server-side daily searches because they only execute when the user's own machine is on. A scheduled FastAPI worker that fans out per-user searches is the only approach that scales cheaply from 10 to 500+ users.
- **Start notifications with Telegram, not WhatsApp or email.** Telegram's Bot API is free at any volume, set up in under two minutes via @BotFather with no approval process, and users connect with a one-tap deep link. WhatsApp Cloud API requires Meta business verification, template approval, and per-conversation fees, making it the hardest to start with. Add email (Resend) as the second channel.
- **The "exact apply link" feature is genuinely achievable for ATS-sourced jobs (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee), which return a direct apply-URL field, and for Google-Jobs aggregator APIs (JSearch/SerpApi), which return an `apply_options` array. It is NOT reliably achievable for LinkedIn/Indeed/Naukri without scraping. Use a tiered fallback: direct apply URL → job detail page → company careers page → source search deep link.**

## Key Findings

### Job data sources: a layered strategy
No single source covers India + global + remote with clean apply links. Use four tiers:
1. **Free no-key remote APIs** (Remotive, RemoteOK, Arbeitnow) for remote/global jobs — instant, free, include apply links.
2. **Free-key aggregator APIs** (Adzuna, Jooble, Careerjet) for broad India + global coverage.
3. **ATS public JSON APIs** (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee) — free, no auth, and crucially return a **direct apply URL** per job. This is the backbone of the exact-apply-link feature.
4. **Google-Jobs-via-RapidAPI/SerpApi** (JSearch, SerpApi) as a paid aggregator returning `apply_options` arrays with multiple apply links per job, covering LinkedIn/Indeed/Glassdoor indirectly and legally.

Indeed's Publisher/Job Search API is deprecated and not available for new integrations; its remaining APIs are sponsorship-spend-gated (per Indeed's own developer and partner docs, the Sponsored Jobs API charges for usage and the Publisher "Get Job/Job Search" endpoints are marked deprecated). LinkedIn has no public job-search API at any price — its Jobs API is posting-only for ATS partners. Both are off-limits except indirectly via Google Jobs aggregators. Naukri/Foundit/Instahyre/Internshala have no official public APIs; their data is only available via paid scrapers (Apify actors).

### Resume parsing: use a cheap LLM, not pure NLP libraries
For keyword extraction (role, skills, experience, location), an LLM like Gemini 2.5 Flash-Lite is more accurate and far less maintenance than spaCy/pyresparser pipelines, and is essentially free at this scale. pyresparser is effectively unmaintained and brittle on multi-column and Indian-format resumes.

### Execution architecture: custom backend wins decisively
n8n, Activepieces, and Windmill are single-tenant automation tools — great for automating *your own* workflows, wrong for a product where each of hundreds of users has their own profile, schedule, and "already-sent" state. A FastAPI worker + Postgres + scheduled cron is the right primitive.

### Notifications: Telegram first
Telegram is free, instant to set up, and reliable for automated pushes. WhatsApp is hardest (verification, templates, per-conversation fees). Email is a strong second channel.

## Details

### A) Job data sources

**Free, no-key remote/global APIs (use first):**
- **Remotive** — `https://remotive.com/api/remote-jobs`, free, no key. Returns job `url`, title, company, category, salary, candidate_required_location, and full HTML description. Per Remotive's API legal notice, poll a maximum of ~4×/day (more than 2×/minute is blocked), you must link back and attribute Remotive, and jobs are delayed 24h. Good for remote roles.
- **RemoteOK** — public JSON API, free, includes direct apply links plus salary/tags; ~30,000+ remote listings.
- **Arbeitnow** — free job board API (also on RapidAPI), Europe-leaning remote.

**Free-key aggregator APIs (broad coverage incl. India):**
- **Adzuna** — `https://api.adzuna.com/v1/api/jobs/in/search/1?app_id=...&app_key=...`. Free developer tier, supports India (`in`) plus 18 other countries. Caution: Adzuna's Terms of Service state that free API use is for displaying ad listings, that "any other use … by a commercial … organisation … is permitted subject to a 14 day trial period," after which "a licence agreement may be required," and that rate limits are enforced (raised by request). Returns a `redirect_url` that routes through Adzuna to the source, not always a clean apply page.
- **Jooble** — REST API by request (POST with API key), keyword + location, broad global incl. India; returns a Jooble redirect link.
- **Careerjet** — public partner API, free with key, JSON/XML, global incl. India; rate-limited (raise by request).
- **The Muse, Reed (UK), USAJobs (US gov), Findwork, Jobicy, Himalayas** — all free/freemium niche supplements.

**ATS public JSON APIs — the apply-link backbone (all free, no auth):**
| ATS | Public endpoint | Apply-link field | Notes |
|-----|----------------|------------------|-------|
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | `absolute_url` | Job Board API is explicitly NOT rate-limited; pagination via `Link` header |
| Lever | `api.lever.co/v0/postings/{company}?mode=json` | `applyUrl` (also `hostedUrl`) | ~10 req/s, 429 on exceed; supports team/location filters |
| Ashby | `api.ashbyhq.com/posting-api/job-board/{slug}` | `applyUrl` (also `jobUrl`) | Filter on `isListed`; ~100/min unofficial |
| Workable | `apply.workable.com/api/v1/widget/accounts/{acct}` (public widget); SPI v3 for full data | `application_url` (SPI v3); apply link in widget JSON | 10 requests / 10 seconds documented |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/{id}/postings` | `applyUrl` / `jobAdUrl` | Posting API is officially no-auth; adaptive throttling |
| Recruitee | `{company}.recruitee.com/api/offers` | `careers_apply_url` | Careers Site API needs no authorization |

Discovery of company tokens/slugs: harvest from Common Crawl (regex on ATS URL patterns), Google dorks (`site:boards.greenhouse.io`, `site:jobs.ashbyhq.com`), or reuse open-source slug registries. Open-source aggregators to fork/learn from: **kalil0321/ats-scrapers** ("jobhive", MIT-licensed, canonical schema with an `apply_url` field, covers 20+ ATS), **Feashliaa/job-board-aggregator** (1M+ jobs, 20k+ companies, daily GitHub Actions, Common Crawl slug discovery), **outscal/OpenJobs** (~12,000 company slugs + an ATS prober), and **adgramigna/job-board-scraper**.

**Google Jobs aggregators (paid, return apply_options):**
- **JSearch (OpenWeb Ninja, via RapidAPI)** — real-time Google-for-Jobs data covering LinkedIn/Indeed/Glassdoor/ZipRecruiter. Returns `job_apply_link`, `job_apply_is_direct`, and an `apply_options[]` array of {publisher, apply_link}. Free tier is 500 requests/month on the RapidAPI BASIC plan; paid tiers start around $15/mo for ~50k requests. Supports India (`country=in`).
- **SerpApi Google Jobs** — `apply_options` is available on the main `google_jobs` engine. Free plan is ~250 searches/month; the first paid plan is ~$25/mo for ~1,000 searches. Reliable but pricier per call. Note: the separate `google_jobs_listing` endpoint lost `apply_options` after a Google change — use the main `google_jobs` engine.

**Scraping legality (be careful):** In *hiQ v. LinkedIn*, the Ninth Circuit (April 2022) held that scraping *publicly available* data likely does not violate the CFAA. But per The National Law Review (Dec 2022), on December 7, 2022 the parties agreed to a stipulation entering a **$500,000 judgment against hiQ for (1) breach of contract based on LinkedIn's user agreement and (2) a CFAA violation** tied to hiQ's data-collection practices and use of fake accounts; the court's Nov 4, 2022 summary judgment (Case 17-cv-03301-EMC, N.D. Cal.) found hiQ breached the user agreement via scraping and fake profiles, and hiQ accepted a permanent injunction. Takeaway: scraping public pages is not criminal hacking, but it can still breach a site's ToS and create civil liability; scraping behind logins or with fake accounts is clearly risky. Pragmatic stance for a public product: rely on official APIs and ATS endpoints; treat LinkedIn/Naukri/Indeed scraping as out of scope.

### B) Resume parsing
Recommended pipeline: extract text with a PDF/DOCX parser (pdfplumber/PyMuPDF + python-docx), then send to **Gemini 2.5 Flash-Lite** with a structured-output prompt returning JSON {role titles, skills[], years_experience, location, remote_pref}. Per Google's Developers Blog (Gemini 2.5 Flash-Lite GA, model ID `gemini-2.5-flash-lite`, released July 22, 2025), it is "our lowest-cost 2.5 model yet, priced at $0.10 / 1M input tokens and $0.40 output tokens." A typical resume is ~1–2k tokens, so cost per parse is a fraction of a cent. Google AI Studio's free tier (as of April 2026) gives Flash models 1,500 requests/day, which covers small scale entirely; note Gemini 2.5 Pro is paid-only as of April 1, 2026 (50 RPD free cap) and the free tier may not be used for EEA/UK end users. This LLM approach beats pyresparser/spaCy on messy multi-column and Indian-format resumes with near-zero maintenance. Keep a deterministic skills dictionary as a fallback/augmentation for keyword matching, and **parse once per resume (cache the result), never on every daily run** — this is the single biggest cost control.

### C) Execution architecture comparison
| Approach | Multi-user fit | Setup | Maintenance | Cost at scale | Verdict |
|----------|---------------|-------|-------------|---------------|---------|
| Self-hosted n8n | Poor (single-tenant; per-user state awkward) | Medium | High at scale (idles ~300-500MB, spikes 1-2GB) | VPS ~$5-15/mo flat but breaks logically | No |
| Browser extension | No (client-side; can't run daily server pushes) | Medium | High (per-browser) | N/A | No |
| Desktop app (Electron/Tauri) | No (runs only when user's machine is on) | High | High | N/A | No |
| **Custom cloud backend** | **Excellent** | Medium | Low | Scales cheaply | **Yes** |
| Activepieces/Windmill | Same single-tenant limitation as n8n | Medium | Medium | Flat VPS | No (for a product) |

A browser extension or desktop app cannot deliver a daily-search-and-push model because they only run while the user's machine/browser is active. n8n and its open-source cousins (Activepieces is MIT-licensed; Windmill is AGPLv3) are excellent for automating *your own* workflows but model "one workflow," not "N users each with persistent profiles, dedup state, and notification preferences" — you would end up rebuilding a database-backed app inside them. The custom backend is both simpler and more scalable for this product.

### D) Concrete cheap tech stack (aligned to your skillset)
- **Frontend + resume upload:** Next.js on Vercel (free Hobby tier).
- **File storage:** Supabase Storage for resume files.
- **Database:** Supabase Postgres. Free tier: 500MB DB, 1GB file storage, 50k MAU, 500k Edge Function invocations/month — but projects pause after 7 days of inactivity, so keep alive with a cron ping. Add pgvector later if you want semantic matching.
- **Parsing + matching + fetch worker:** Python/FastAPI on Railway or Render. Railway has no permanent free tier (Hobby includes a $5/mo credit, billed per-second); Render has a free tier (with sleep).
- **Scheduler:** Supabase Cron (pg_cron — free; runs SQL/HTTP/Edge Functions; Supabase recommends ≤8 concurrent jobs, each ≤10 min) to call your FastAPI `/run-daily` endpoint; OR GitHub Actions cron (free for public repos; counts against Actions minutes for private repos).
- **Notifications:** Telegram Bot API (free) first; Resend for email later.
- **LLM:** Gemini 2.5 Flash-Lite via LiteLLM (fits your existing stack); add Langfuse for observability if useful.

**Rough monthly cost:**
- **~10 users:** **$0.** All free tiers (Vercel, Supabase free, Render free or Railway's $5 credit, Telegram free, Gemini free tier, JSearch free 500/mo).
- **~100 users:** **~$5–25/mo.** You may outgrow Supabase free (Pro at $25 removes the inactivity pause and raises limits) or stay free with care. The real email constraint is Resend's free-tier daily cap (see below): ~100 daily-email users sits right at the limit. Lean on free ATS + Adzuna + Remotive and batch shared queries so JSearch/SerpApi free tiers are not exhausted.
- **~500+ users:** **~$50–150/mo.** Supabase Pro ($25), a paid compute instance ($10–20), a paid email tier (Resend Pro $20 for 50k, or AWS SES at $0.10/1k = pennies but more setup), and a paid Google-Jobs API tier only if needed. Telegram stays free. The dominant cost driver is per-user-per-source API calls — controlled with shared-query batching and daily caching (see edge cases).

### E) Notification channels
| Channel | Setup | Cost | Reliability | User connect | Verdict |
|---------|-------|------|-------------|--------------|---------|
| **Telegram** | <2 min via @BotFather, no approval | **Free, any volume** | High; Telegram queues messages up to 24h if your webhook is down | One-tap deep link, then `/start` | **Start here** |
| Email (Resend) | Minutes; domain verify (SPF/DKIM/DMARC) | Free 3,000/mo capped 100/day, 1 domain; Pro $20/mo for 50k (removes daily cap) | High if auth configured | Just an address | Second channel |
| WhatsApp Cloud API | Days–weeks; Meta business verification + template approval | Per-conversation $0.005–$0.08 + BSP fees | High | Phone number | Last; hardest |

Telegram cannot initiate a conversation until the user messages the bot once, so onboarding is: user clicks your bot deep link, taps Start, and you capture their `chat_id` and link it to their profile. Per Resend's own "New Free Tier" announcement, the free plan lets you "send up to 3,000 emails a month (100 per day)" on a single domain, with Pro at $20/mo for 50,000 emails removing the daily cap; at high volume Amazon SES is ~9x cheaper than Resend's $0.90/1,000 overage at $0.10 per 1,000 emails. WhatsApp's template-approval and per-message billing make it unsuitable as a starting channel; avoid unofficial WhatsApp libraries — they violate Meta's ToS and get numbers banned. Expansion path: **Telegram → Email → (only on real demand) WhatsApp.**

### F) Edge cases and hard problems
- **Exact apply link reliability:** High for ATS sources (direct `applyUrl`/`absolute_url`/`careers_apply_url`); medium for Google-Jobs aggregators (use the `apply_options` array, prefer entries where `job_apply_is_direct` is true); low for Adzuna/Jooble (redirect URLs); impossible-without-scraping for LinkedIn/Naukri. **Fallback ladder:** (1) direct apply URL → (2) job detail/posting page → (3) company careers page → (4) a pre-filled Google Jobs / source search deep link. Always label which type of link you are sending.
- **Login-walled / expiring apply links:** Some apply pages require login (e.g., Internshala's "Apply" needs a student account — return the canonical detail-page URL instead). Treat every link as best-effort and, where feasible, verify an HTTP 200 before sending.
- **Dedup across sources and days:** Normalize each job to a canonical key (lowercased company + normalized title + location, plus a fuzzy hash of the description). Store a `sent_jobs` table keyed by (user_id, canonical_key) so the same job appearing across multiple boards or on repeat days is never sent twice. This per-user state is exactly what n8n handles poorly and a database handles trivially.
- **Stale/filled listings:** Prefer APIs with recency filters (date_posted); optionally HEAD-check the apply URL before sending.
- **Rate limits / IP bans:** Official APIs avoid most of this. For ATS endpoints, throttle (Workable 10/10s, Lever ~10/s) and back off on HTTP 429. Avoid scraping at scale; if you ever must, residential proxies cost real money (priced per GB) and add maintenance — another reason to stay API-first.
- **Scaling N users × M sources:** Do NOT run a naive per-user-per-source loop. **Batch by shared query:** group users by (role cluster + location), fetch each distinct query once, cache results for the day, then match cached jobs to each user in memory. This turns 500 users × 10 sources into a few hundred cached queries instead of 5,000 API calls. Use a queue (Postgres-backed or lightweight) and process in batches to avoid timeouts.
- **Privacy/compliance (India DPDP Act 2023 + GDPR):** Resumes are personal data. The DPDP Act requires consent that is free, specific, and informed; purpose limitation; storage limitation (erase when the purpose is served or consent is withdrawn); reasonable security safeguards; and breach notification. Per EY India and DLA Piper, the DPDP Rules 2025 were notified by MeitY on November 13, 2025, with full compliance required by **13 May 2027**, and failure to notify the Data Protection Board and affected Data Principals of a breach carries penalties up to ₹200 crore (overall DPDP penalties cap at ₹250 crore); breaches must be reported to the Board, with a detailed report due within 72 hours. Practical steps: an explicit consent checkbox at upload with a plain-language notice; collect only what you need (store extracted keywords; consider deleting the raw resume file after parsing); provide delete-my-data and withdraw-consent controls; encrypt at rest; prefer India-region hosting; and publish a data-retention policy. If you have any EU users, GDPR applies similarly (and the Gemini API free tier cannot be used for EEA/UK end users — use the paid tier there).
- **Anti-abuse:** Require email/Telegram verification before activating daily runs; rate-limit signups; cap resumes per account; validate uploads are real resumes (size, MIME type, plus an LLM sanity check) to reject junk; apply soft caps on saved searches.
- **Cost blowups if free-to-users:** The two killers are LLM calls (mitigated by parsing once per resume, not daily) and per-user job-API calls (mitigated by shared-query batching + daily caching). Telegram and ATS APIs are free, so a well-batched design stays near-zero cost into the low hundreds of users.

### G) Competitive / prior-art landscape
- **Auto-appliers:** LoopCV (auto-applies across LinkedIn/Indeed/30+ boards, free to start, advertises 50,000+ job seekers), Sonara, AIApply, LazyApply (Chrome extension, high-volume blasting), Jobright.ai (AI copilot + autofill). These *apply* for you; yours *finds and notifies* — a lighter, less ToS-risky niche.
- **Autofill/tracking:** Simplify.jobs (Chrome extension autofill on 100+ sites), Huntr (application tracker), JobScan (resume-vs-JD keyword optimization).
- **Built-in alerts:** LinkedIn and Indeed already email job-alert matches — your differentiation is cross-source aggregation, exact apply links, Telegram delivery, and India focus.
- **Open-source to fork/learn:** jobright-ai's public new-grad job-list repos, the ATS aggregators above (jobhive, job-board-aggregator, OpenJobs, levergreen's scraper), and GitHub's `job-search-automation` topic. The gap your tool fills: a **free, multi-source, India-leaning daily digest with clean apply links delivered over Telegram** — none of the incumbents do exactly this for free.

## Recommendations

**Phase 0 (MVP, ~1–2 weeks):** Next.js upload page on Vercel + Supabase (Postgres + Storage) + a FastAPI worker on Render/Railway. Parse resumes with Gemini 2.5 Flash-Lite. Pull jobs from **free sources only**: Remotive + RemoteOK + Arbeitnow + Adzuna (India) + a starter set of Greenhouse/Lever/Ashby company boards. Match by keyword (role + skills + location). Push a daily Telegram digest with the best apply link per job. Dedup via a `sent_jobs` table. Trigger with Supabase Cron or GitHub Actions cron. Target: works for you and ~10 friends at $0/mo.

**Phase 1 (broaden + harden):** Add email (Resend) as a second channel. Expand ATS coverage using an open-source slug registry / Common Crawl discovery. Add JSearch's free tier for LinkedIn/Indeed-sourced jobs via `apply_options`. Implement shared-query batching and daily caching. Add the consent flow, delete-my-data, and a retention policy for DPDP.

**Phase 2 (scale to hundreds):** Upgrade Supabase to Pro ($25) when you hit storage/MAU/pause limits. Add a job queue and batch processing. Add a paid Google-Jobs tier only if coverage demands it. Consider AWS SES for cheap email at volume. Add WhatsApp only if users explicitly ask and you are ready for verification, templates, and fees.

**Thresholds that change the plan:**
- A single free job API's rate limit is hit during daily runs → switch that query to batched/cached shared queries before paying.
- Resend's 100/day cap is reached (~100 daily-email users) → move email to AWS SES ($0.10/1k).
- Supabase free DB hits 500MB or the 7-day pause hurts real users → upgrade to Pro ($25).
- Users demand LinkedIn/Indeed-specific apply links → adopt the JSearch/SerpApi paid tier rather than scraping.
- You ever consider scraping Naukri/LinkedIn at scale → don't, for a public product; the ToS/civil-liability and proxy-cost risks outweigh the benefit.

## Caveats
- API free tiers and pricing change frequently; verify current limits before launch (especially JSearch/SerpApi request caps, Supabase free-tier terms, Resend's daily cap, and Gemini free-tier rules including the EEA/UK restriction).
- The unauthenticated Workable widget endpoint is semi-official; SmartRecruiters' clean `applyUrl`/`jobAdUrl` fields are most clearly documented on its partner publications feed, while the public Posting API returns objects from which you construct the URL — validate both against live responses.
- Adzuna's ToS restricts aggregation and commercial reuse beyond a 14-day trial without a licence; review carefully before relying on it as a core source for a public product.
- "Exact apply link" success rate varies sharply by source; set user expectations explicitly and always provide a graceful fallback link.
- Indeed and LinkedIn provide no viable official job-search API path; any coverage of their listings comes indirectly via Google Jobs aggregators.
- DPDP Rules operational details (consent manager registration, breach reporting mechanics) are still phasing in toward the May 2027 deadline; treat compliance as an evolving target and re-check before public launch.