"use client";

import { useState } from "react";

export type Job = {
  canonical_key: string;
  title: string;
  company: string;
  location: string | null;
  apply_url: string;
  apply_url_type: string;
  source: string;
  saved?: boolean;
  feedback?: "up" | "down" | null;
  status?: string | null;
};

const APPLY_LABEL: Record<string, string> = {
  direct_apply: "Apply", job_detail: "View posting", company_careers: "Careers", source_search: "Search",
};
const STATUSES = [
  { v: "", t: "Not applied" }, { v: "applied", t: "Applied" },
  { v: "interviewing", t: "Interviewing" }, { v: "offer", t: "Offer" }, { v: "rejected", t: "Rejected" },
];

export default function JobCard({ job }: { job: Job }) {
  const [saved, setSaved] = useState(!!job.saved);
  const [feedback, setFeedback] = useState<string | null>(job.feedback ?? null);
  const [status, setStatus] = useState<string>(job.status ?? "");
  const [assist, setAssist] = useState<{ cover_letter: string; answers: { q: string; a: string }[] } | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const snapshot = {
    title: job.title, company: job.company, location: job.location,
    apply_url: job.apply_url, apply_url_type: job.apply_url_type, source: job.source,
  };

  async function act(patch: Record<string, unknown>) {
    await fetch("/api/account/action", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ canonical_key: job.canonical_key, job: snapshot, ...patch }),
    }).catch(() => {});
  }

  function toggleSave() { const v = !saved; setSaved(v); act({ saved: v }); }
  function vote(f: "up" | "down") { const v = feedback === f ? null : f; setFeedback(v); act({ feedback: v }); }
  function setStat(v: string) { setStatus(v); act({ status: v || null }); }

  async function draft() {
    setDrafting(true); setErr(null);
    try {
      const res = await fetch("/api/account/assist", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ canonical_key: job.canonical_key }),
      });
      const d = await res.json();
      if (!res.ok) setErr(d.error ?? "Couldn't draft.");
      else setAssist(d);
    } catch { setErr("Network error."); }
    finally { setDrafting(false); }
  }

  return (
    <li className={`job ${feedback === "down" ? "muted" : ""}`}>
      <div className="job-main">
        <div className="job-title">{job.title}</div>
        <div className="job-meta">
          {job.company}{job.location ? ` · ${job.location}` : ""} · <span className="src">{job.source}</span>
        </div>
        <div className="job-row">
          <button className={`mini ${saved ? "on" : ""}`} onClick={toggleSave}>{saved ? "★ Saved" : "☆ Save"}</button>
          <button className={`mini ${feedback === "up" ? "on" : ""}`} onClick={() => vote("up")} aria-label="Good match">👍</button>
          <button className={`mini ${feedback === "down" ? "on" : ""}`} onClick={() => vote("down")} aria-label="Not relevant">👎</button>
          <select className="mini" value={status} onChange={(e) => setStat(e.target.value)}>
            {STATUSES.map((s) => <option key={s.v} value={s.v}>{s.t}</option>)}
          </select>
          <button className="mini" onClick={draft} disabled={drafting}>{drafting ? "Drafting…" : "✨ Draft application"}</button>
        </div>
        {err && <div className="msg err" style={{ marginTop: 8 }}>{err}</div>}
        {assist && (
          <div className="assist">
            <div className="assist-h">Cover letter <button className="mini" onClick={() => navigator.clipboard.writeText(assist.cover_letter)}>Copy</button></div>
            <p className="assist-body">{assist.cover_letter}</p>
            {assist.answers?.map((qa, i) => (
              <div key={i}><div className="assist-h">{qa.q}</div><p className="assist-body">{qa.a}</p></div>
            ))}
            <p className="hint">Review and personalise before sending.</p>
          </div>
        )}
      </div>
      <a className="apply" href={job.apply_url} target="_blank" rel="noreferrer">{APPLY_LABEL[job.apply_url_type] ?? "Open"}</a>
    </li>
  );
}
