"use client";

import { useState } from "react";

type Profile = { role_titles: string[]; skills: string[]; location: string | null };
type Success = { userId: string; connectUrl: string; parsed: boolean; profile?: Profile; warning?: string };
type Result = { ok: true; data: Success } | { ok: false; error: string };

export default function Home() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setResult(null);
    try {
      const res = await fetch("/api/submit", { method: "POST", body: new FormData(e.currentTarget) });
      const data = await res.json();
      if (!res.ok && res.status !== 202) setResult({ ok: false, error: data.error ?? "Something went wrong" });
      else setResult({ ok: true, data });
    } catch {
      setResult({ ok: false, error: "Network error. Is the server running?" });
    } finally {
      setBusy(false);
    }
  }

  if (result?.ok) return <SuccessView s={result.data} />;

  return (
    <main className="wrap">
      <h1>Daily Job Digest</h1>
      <p className="sub">
        Upload your resume once. Every day we match jobs across many sources (with direct apply
        links) and send the best ones to your Telegram. Free.
      </p>

      <div className="card">
        <form onSubmit={onSubmit}>
          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" required placeholder="you@example.com" />

          <label htmlFor="resume">Resume (PDF, DOCX, or TXT)</label>
          <input id="resume" name="resume" type="file" accept=".pdf,.docx,.doc,.txt" required />
          <p className="hint">We extract your role, skills, and location. Max 3 MB.</p>

          <label htmlFor="location_scope">Where do you want jobs?</label>
          <select id="location_scope" name="location_scope" defaultValue="mix">
            <option value="mix">Both, balanced (50/50)</option>
            <option value="in_country">Within my country (incl. remote)</option>
            <option value="outside_only">Outside my country (international)</option>
          </select>
          <p className="hint">Based on the location in your resume. You can change this later.</p>

          <label htmlFor="remote_mode">Remote work?</label>
          <select id="remote_mode" name="remote_mode" defaultValue="include_remote">
            <option value="include_remote">Include remote and onsite</option>
            <option value="only_remote">Only remote</option>
            <option value="no_remote">No remote (onsite only)</option>
          </select>

          <label htmlFor="preferred_locations">Preferred cities (optional)</label>
          <input id="preferred_locations" name="preferred_locations" type="text"
                 placeholder="e.g. Ahmedabad, Pune" />
          <p className="hint">
            If set, we show jobs in these cities (plus remote per your setting above) and ignore the
            broad location choice. Comma-separated, up to 5.
          </p>

          <div className="consent">
            <input id="consent" name="consent" type="checkbox" value="yes" required />
            <span>
              I consent to my resume being processed to extract role, skills, and location for job
              matching. The raw file is deletable after parsing, and I can delete my data anytime.
            </span>
          </div>

          <button type="submit" disabled={busy}>
            {busy ? "Processing your resume..." : "Continue"}
          </button>
        </form>
        {result && !result.ok && <div className="msg err">{result.error}</div>}
      </div>
    </main>
  );
}

function SuccessView({ s }: { s: Success }) {
  return (
    <main className="wrap">
      <h1>You're almost set</h1>
      <p className="sub">One last step: connect Telegram so we can send your daily digest.</p>

      <div className="card">
        <ol className="steps">
          <li className="done">Resume received{s.parsed ? " and parsed" : ""}</li>
          <li>
            <strong>Connect Telegram</strong> — tap below, then press <em>Start</em> in the app.
            <div>
              <a className="cta" href={s.connectUrl} target="_blank" rel="noreferrer">
                Connect Telegram
              </a>
            </div>
          </li>
          <li>Get your first matched jobs in the next daily run.</li>
        </ol>

        {s.warning && <div className="msg warn">{s.warning}</div>}

        {s.profile && (
          <div className="profile">
            <div className="profile-h">Detected roles</div>
            <div className="tags">
              {s.profile.role_titles.map((r) => <span className="tag" key={r}>{r}</span>)}
            </div>
            <div className="profile-h">Skills</div>
            <div className="tags">
              {s.profile.skills.slice(0, 14).map((x) => <span className="tag" key={x}>{x}</span>)}
            </div>
            {s.profile.location && <p className="hint">Location: {s.profile.location}</p>}
          </div>
        )}

        <div className="links">
          <a href="/account">Manage preferences &amp; view matches</a>
        </div>
        <p className="hint">Sign in on the account page with this email to edit preferences anytime.</p>
      </div>
    </main>
  );
}
