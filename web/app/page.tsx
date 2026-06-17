"use client";

import { useState } from "react";

type Result =
  | { ok: true; parsed: boolean; profile?: { role_titles: string[]; skills: string[]; location: string | null }; warning?: string }
  | { ok: false; error: string };

const BOT = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "";

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
      if (!res.ok && res.status !== 202) {
        setResult({ ok: false, error: data.error ?? "Something went wrong" });
      } else {
        setResult({ ok: true, parsed: data.parsed, profile: data.profile, warning: data.warning });
      }
    } catch {
      setResult({ ok: false, error: "Network error. Is the server running?" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="wrap">
      <h1>Daily Job Digest</h1>
      <p className="sub">
        Upload your resume once. Each day we match jobs across many sources and send the best ones,
        with apply links, to your Telegram. Free.
      </p>

      <div className="card">
        <form onSubmit={onSubmit}>
          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" required placeholder="you@example.com" />

          <label htmlFor="telegram_chat_id">Telegram chat id</label>
          <input id="telegram_chat_id" name="telegram_chat_id" type="text" placeholder="e.g. 1275547695" />
          <p className="hint">
            {BOT ? (
              <>
                Message <a href={`https://t.me/${BOT}`} target="_blank" rel="noreferrer">@{BOT}</a> first, then get your
                id from the bot. Optional for now; needed to receive the digest.
              </>
            ) : (
              <>Optional for now; needed to receive the digest.</>
            )}
          </p>

          <label htmlFor="resume">Resume (PDF, DOCX, or TXT)</label>
          <input id="resume" name="resume" type="file" accept=".pdf,.docx,.doc,.txt" required />

          <div className="consent">
            <input id="consent" name="consent" type="checkbox" value="yes" required />
            <span>
              I consent to my resume being processed to extract role, skills, and location for job
              matching. The raw file is deletable after parsing, and I can request deletion anytime.
            </span>
          </div>

          <button type="submit" disabled={busy}>
            {busy ? "Processing..." : "Start my daily digest"}
          </button>
        </form>

        {result && result.ok && (
          <div className={`msg ${result.warning ? "warn" : "ok"}`}>
            {result.warning ? (
              <>{result.warning}</>
            ) : (
              <>
                <strong>You are set up.</strong>
                {result.profile && (
                  <>
                    <div style={{ marginTop: 8 }}>Detected roles:</div>
                    <div className="tags">
                      {result.profile.role_titles.map((r) => (
                        <span className="tag" key={r}>{r}</span>
                      ))}
                    </div>
                    <div style={{ marginTop: 8 }}>Skills:</div>
                    <div className="tags">
                      {result.profile.skills.slice(0, 12).map((s) => (
                        <span className="tag" key={s}>{s}</span>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}
        {result && !result.ok && <div className="msg err">{result.error}</div>}
      </div>
    </main>
  );
}
