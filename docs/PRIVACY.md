# Data retention and privacy (India DPDP Act)

This service processes resumes, which are personal data. We follow the DPDP Act
2023 principles: consent, purpose limitation, storage limitation, security, and
the right to erasure.

## What we collect and why
- **Resume file (raw):** only to extract a structured profile. Treated as
  deletable after parsing. Stored in Supabase Storage with a per-user path.
- **Extracted keywords** (role titles, skills, years, location, remote pref):
  the minimum needed to match jobs. Stored in `profiles`.
- **Telegram chat id:** to deliver the digest.
- **Sent-job history** (`sent_jobs`): canonical keys only, to avoid resending.

We do NOT put personal data in URLs or logs.

## Consent
Consent is captured explicitly at upload (a checkbox with a plain-language
notice) and recorded as `users.consent_at`. The daily run only processes users
with a parsed profile; activation requires consent.

## Retention
- **Raw resume file:** deletable immediately after parsing. The parsed profile
  is what we keep. (A future job can auto-purge raw files past N days.)
- **job_cache:** pruned automatically after `CACHE_TTL_DAYS` (default 14).
- **Profiles / searches / sent history:** kept while the account is active.

## Right to erasure (delete-my-data)
A user can request full deletion. This removes the user row and cascades to
profile, saved searches, and sent history, and removes the raw resume file from
Storage.
- API: `DELETE /users/{user_id}`
- CLI: `python scripts/delete_user.py --user-id <uuid>`

## Security
- Secrets live in `.env` (gitignored); resumes are gitignored.
- The worker uses the Supabase service-role key server-side only. RLS policies
  should be added before any client talks to the database directly.
- Region: prefer India-region Supabase hosting for India users.

## Caveats
DPDP Rules operational details (consent manager, breach reporting) are phasing in
toward the May 2027 deadline. Re-check before public launch. If you have EU/UK
users, GDPR applies and the Gemini free tier may not be used for EEA/UK end users
(use a paid key there).
