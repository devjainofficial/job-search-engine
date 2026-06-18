# QA test plan

Live URLs:
- Web: https://jobsearch-web-devjain2309s-projects.vercel.app
- Worker health: https://job-search-worker-jkrh.onrender.com/health

> Note: the worker is on a free tier that sleeps after ~15 min idle. The FIRST
> action after an idle period (upload / find-now / Telegram connect) can take
> ~50s. This is expected, not a bug. Subsequent actions are fast.

App is now **login-first**: nothing (including résumé upload) is accessible without signing in. Email login is hidden (needs a custom domain); **Google is the only sign-in**.

## 1. Landing + login (`/`)
| # | Steps | Expected |
|---|-------|----------|
| 1.1 | Open `/` logged out | Welcome hero + "Continue with Google" only (no upload, no email field) |
| 1.2 | Click "Continue with Google" | Google consent → returns signed in |
| 1.3 | Open `/` while already logged in | Auto-redirects to onboarding (or dashboard if already set up) |
| 1.4 | Hit `/api/onboarding` or `/api/account` logged out | 401 |

## 2. Onboarding wizard (`/onboarding`, first-time, one step at a time)
| # | Steps | Expected |
|---|-------|----------|
| 2.1 | Welcome → Get started | Moves to upload step; progress bar advances |
| 2.2 | Upload step: continue with no file / no consent | Button disabled / "Attach your résumé and accept consent" |
| 2.3 | Upload >3 MB or .png/.zip | Friendly size/type error |
| 2.4 | Upload valid résumé + consent | "Reading your résumé…" then roles/skills pre-filled from it |
| 2.5 | Roles/Skills/Cities steps | Chip input: type + Enter/comma adds a bubble; × or Backspace removes |
| 2.6 | Location & Remote steps | Tap a card → auto-saves and advances |
| 2.7 | Cities step → Skip | Advances with no cities |
| 2.8 | Back button on any step | Returns to previous step, keeps data |
| 2.9 | Telegram step → Connect → Finish | Lands on `/account`; revisiting `/onboarding` now redirects to `/account` |
| 2.10 | Scanned/image-only PDF (no text) | Proceeds; roles/skills empty to fill manually |

## 3. Telegram connect
| # | Steps | Expected |
|---|-------|----------|
| 3.1 | Tap "Connect Telegram", press Start | "Connected" message in Telegram |
| 3.2 | Connect link with a tampered token | "That link looks invalid…" |
| 3.3 | Send the bot a plain message | Friendly help reply |

## 3b. Login / session (`/account`)
| # | Steps | Expected |
|---|-------|----------|
| 3b.1 | "Continue with Google" | Logs in, shows account hub |
| 3b.2 | Visit `/account` logged out | Sign-in screen (Google only), not data |
| 3b.3 | Hit `/api/account` logged out | 401 |

## 4. Account hub (logged in)
| # | Steps | Expected |
|---|-------|----------|
| 4.1 | Edit target roles / skills, Save profile | "Saved. Applies on your next search." |
| 4.2 | Change location / remote / cities | "Saved. Applies on the next daily run." |
| 4.3 | Click "Find new jobs now" | "Found N new job(s)!" and the list refreshes |
| 4.4 | Click "Find now" again immediately | "Please wait Ns…" (60s cooldown) |
| 4.5 | Find now repeatedly over time | Always NEW jobs, never a repeat |
| 4.6 | Sign out, then back in | Session ends / resumes correctly |
| 4.7 | Delete my account (confirm) | All data + resume removed; signed out |

## 5. Digest / matching sanity
- A user with city "Ahmedabad" + "No remote" should receive only Ahmedabad onsite roles.
- "Within my country" should exclude foreign-onsite roles.
- "Only remote" should return only remote roles.
- No internship/new-grad roles for a user with 3+ years experience.
- No more than 2 jobs from the same company per digest.

## Known limitations (not bugs)
- OTP emails use Supabase's built-in mailer (rate-limited, may hit spam). Google
  login avoids this.
- First request after idle is slow (worker cold start ~50s).
- "Find now" returns up to 20; the daily Telegram digest is capped at 10.
