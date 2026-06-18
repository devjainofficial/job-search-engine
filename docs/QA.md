# QA test plan

Live URLs:
- Web: https://jobsearch-web-devjain2309s-projects.vercel.app
- Worker health: https://job-search-worker-jkrh.onrender.com/health

> Note: the worker is on a free tier that sleeps after ~15 min idle. The FIRST
> action after an idle period (upload / find-now / Telegram connect) can take
> ~50s. This is expected, not a bug. Subsequent actions are fast.

## 1. Sign-up / upload (home page, no login needed)
| # | Steps | Expected |
|---|-------|----------|
| 1.1 | Upload a valid PDF/DOCX/TXT, tick consent, submit | "You're almost set" + detected roles/skills; Connect Telegram button |
| 1.2 | Submit with no email / bad email | "Please enter a valid email address." |
| 1.3 | Submit without ticking consent | "Please tick the consent box…" |
| 1.4 | Submit with no file | "Please attach your resume to continue." |
| 1.5 | Upload a >3 MB file | "That file is over 3 MB…" |
| 1.6 | Upload a .png / .zip | "Please upload a PDF, DOCX, or TXT file." |
| 1.7 | Upload a scanned/image-only PDF (no text) | Signed up + friendly "couldn't read your resume… we'll retry" |
| 1.8 | Re-upload with the SAME email | Reuses the same account (no duplicate); profile updates |
| 1.9 | Same email different case (Foo@x.com vs foo@x.com) | Treated as one account |

## 2. Telegram connect
| # | Steps | Expected |
|---|-------|----------|
| 2.1 | Tap "Connect Telegram", press Start in Telegram | "Connected" message in Telegram |
| 2.2 | Open a connect link with a tampered token | "That link looks invalid…" |
| 2.3 | Send the bot a plain message | Friendly help reply |

## 3. Login (/account)
| # | Steps | Expected |
|---|-------|----------|
| 3.1 | "Continue with Google" | Logs in, shows account |
| 3.2 | Email -> "Email me a code" -> enter code | Logs in |
| 3.3 | Enter wrong/expired code | "That code didn't work — request a new one." |
| 3.4 | Log in with an email that never signed up | "No profile found… upload first" |
| 3.5 | Visit /account when logged out | Sign-in screen (not data) |
| 3.6 | Hit /api/account directly when logged out | 401 |

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
