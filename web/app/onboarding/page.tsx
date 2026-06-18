"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { supabaseBrowser } from "@/lib/supabaseBrowser";
import TagInput from "@/components/TagInput";

const STEPS = ["welcome", "upload", "roles", "skills", "location", "remote", "cities", "telegram"] as const;

const SCOPE = [
  { v: "mix", t: "Both, balanced", s: "A 50/50 mix of local and international roles" },
  { v: "in_country", t: "Within my country", s: "Local + remote roles you can do from here" },
  { v: "outside_only", t: "Outside my country", s: "International roles only" },
];
const REMOTE = [
  { v: "include_remote", t: "Remote & onsite", s: "Show me everything" },
  { v: "only_remote", t: "Only remote", s: "Work-from-anywhere roles" },
  { v: "no_remote", t: "Onsite only", s: "No remote roles" },
];

export default function Onboarding() {
  const supabase = supabaseBrowser();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [i, setI] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [consent, setConsent] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [over, setOver] = useState(false);
  const [roles, setRoles] = useState<string[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [cities, setCities] = useState<string[]>([]);
  const [scope, setScope] = useState("mix");
  const [remote, setRemote] = useState("include_remote");
  const [connectUrl, setConnectUrl] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    (async () => {
      const { data } = await supabase.auth.getUser();
      if (!data.user) { router.replace("/"); return; }
      const res = await fetch("/api/account");
      if (res.ok) {
        const d = await res.json();
        if (d.onboarded) { router.replace("/account"); return; }
        if (d.prefs?.location_scope) setScope(d.prefs.location_scope);
        if (d.prefs?.remote_mode) setRemote(d.prefs.remote_mode);
        if (d.connectUrl) setConnectUrl(d.connectUrl);
      }
      setReady(true);
    })();
  }, [supabase, router]);

  async function save(body: Record<string, unknown>) {
    try { await fetch("/api/account", { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }); } catch {}
  }
  const next = () => setI((n) => Math.min(n + 1, STEPS.length - 1));
  const back = () => setI((n) => Math.max(n - 1, 0));

  async function upload() {
    if (!file || !consent) { setError("Attach your résumé and accept consent."); return; }
    setBusy(true); setError(null);
    try {
      const fd = new FormData(); fd.set("resume", file); fd.set("consent", "yes");
      const res = await fetch("/api/onboarding", { method: "POST", body: fd });
      const d = await res.json();
      if (!res.ok && res.status !== 202) { setError(d.error ?? "Upload failed."); setBusy(false); return; }
      if (d.connectUrl) setConnectUrl(d.connectUrl);
      if (d.profile) {
        setRoles(d.profile.role_titles ?? []);
        setSkills(d.profile.skills ?? []);
      }
      setBusy(false); next();
    } catch { setError("Network error. Please try again."); setBusy(false); }
  }

  async function chooseScope(v: string) { setScope(v); await save({ location_scope: v }); next(); }
  async function chooseRemote(v: string) { setRemote(v); await save({ remote_mode: v }); next(); }

  if (!ready) return <main className="wiz"><div className="wiz-step"><p className="sub">Loading…</p></div></main>;

  const step = STEPS[i];
  const pct = Math.round((i / (STEPS.length - 1)) * 100);

  return (
    <main className="wiz">
      <div className="wiz-bar"><span style={{ width: `${pct}%` }} /></div>
      {i > 0 && <div className="wiz-count">Step {i} of {STEPS.length - 1}</div>}

      <div className="wiz-step" key={step}>
        {step === "welcome" && (
          <>
            <h1 className="wiz-q">Let's set up your daily job hunt 👋</h1>
            <p className="wiz-help">Takes about a minute. We'll read your résumé, confirm a few preferences, and connect Telegram.</p>
            <div className="wiz-actions"><button onClick={next}>Get started</button></div>
          </>
        )}

        {step === "upload" && (
          <>
            <h1 className="wiz-q">Upload your résumé</h1>
            <p className="wiz-help">PDF, DOCX, or TXT, up to 3 MB. We extract your roles, skills, and location.</p>
            <div className={`drop ${over ? "over" : ""}`} onClick={() => fileRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); }}>
              <div className="big">{file ? file.name : "Drop your résumé here, or click to browse"}</div>
            </div>
            <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt" style={{ display: "none" }}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            <label className="consent" style={{ marginTop: 16 }}>
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>I consent to my résumé being processed to extract role, skills, and location for job matching (deletable anytime).</span>
            </label>
            {error && <div className="msg err">{error}</div>}
            <div className="wiz-actions">
              <button className="wiz-back" onClick={back}>Back</button>
              <button onClick={upload} disabled={busy || !file || !consent}>{busy ? "Reading your résumé…" : "Continue"}</button>
            </div>
          </>
        )}

        {step === "roles" && (
          <>
            <h1 className="wiz-q">Your target roles</h1>
            <p className="wiz-help">We pre-filled these from your résumé. Add or remove to taste — type and press Enter.</p>
            <TagInput value={roles} onChange={setRoles} placeholder="e.g. Full-Stack Developer" max={8} />
            <div className="wiz-actions">
              <button className="wiz-back" onClick={back}>Back</button>
              <button onClick={async () => { await save({ role_titles: roles }); next(); }}>Continue</button>
            </div>
          </>
        )}

        {step === "skills" && (
          <>
            <h1 className="wiz-q">Your skills</h1>
            <p className="wiz-help">These sharpen your matches. Type and press Enter to add each one.</p>
            <TagInput value={skills} onChange={setSkills} placeholder="e.g. React, Node.js, Python" max={30} />
            <div className="wiz-actions">
              <button className="wiz-back" onClick={back}>Back</button>
              <button onClick={async () => { await save({ skills }); next(); }}>Continue</button>
            </div>
          </>
        )}

        {step === "location" && (
          <>
            <h1 className="wiz-q">Where do you want jobs?</h1>
            <p className="wiz-help">You can change this anytime.</p>
            <div className="choices">
              {SCOPE.map((o) => (
                <button key={o.v} className={`choice ${scope === o.v ? "sel" : ""}`} onClick={() => chooseScope(o.v)}>
                  <div className="c-title">{o.t}</div><div className="c-sub">{o.s}</div>
                </button>
              ))}
            </div>
            <div className="wiz-actions"><button className="wiz-back" onClick={back}>Back</button></div>
          </>
        )}

        {step === "remote" && (
          <>
            <h1 className="wiz-q">Remote work?</h1>
            <div className="choices">
              {REMOTE.map((o) => (
                <button key={o.v} className={`choice ${remote === o.v ? "sel" : ""}`} onClick={() => chooseRemote(o.v)}>
                  <div className="c-title">{o.t}</div><div className="c-sub">{o.s}</div>
                </button>
              ))}
            </div>
            <div className="wiz-actions"><button className="wiz-back" onClick={back}>Back</button></div>
          </>
        )}

        {step === "cities" && (
          <>
            <h1 className="wiz-q">Any preferred cities?</h1>
            <p className="wiz-help">Optional. If set, we focus on these cities (plus remote). Type and press Enter.</p>
            <TagInput value={cities} onChange={setCities} placeholder="e.g. Ahmedabad, Pune" max={5} />
            <div className="wiz-actions">
              <button className="wiz-back" onClick={back}>Back</button>
              <button onClick={async () => { await save({ preferred_locations: cities }); next(); }}>Continue</button>
              <button className="wiz-skip" onClick={async () => { await save({ preferred_locations: [] }); next(); }}>Skip</button>
            </div>
          </>
        )}

        {step === "telegram" && (
          <>
            <h1 className="wiz-q">Last step — connect Telegram 🎉</h1>
            <p className="wiz-help">That's where your daily digest arrives. Tap below, press Start in Telegram, then finish.</p>
            {connectUrl && <a className="cta" href={connectUrl} target="_blank" rel="noreferrer">Connect Telegram</a>}
            <div className="wiz-actions">
              <button className="wiz-back" onClick={back}>Back</button>
              <button onClick={() => router.push("/account")}>Finish — go to my dashboard</button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
