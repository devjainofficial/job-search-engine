"use client";

import { useCallback, useEffect, useState } from "react";
import { supabaseBrowser } from "@/lib/supabaseBrowser";
import TagInput from "@/components/TagInput";
import JobCard, { type Job } from "@/components/JobCard";

type Profile = { role_titles: string[]; skills: string[]; location: string | null; years_experience: number | null } | null;
type Prefs = { location_scope?: string; remote_mode?: string; preferred_locations?: string[] };
type Account = { found: boolean; email: string; prefs?: Prefs; profile?: Profile; jobs?: Job[]; saved?: Job[]; applied?: Job[] };

export default function AccountPage() {
  const supabase = supabaseBrowser();
  const [step, setStep] = useState<"loading" | "email" | "authed">("loading");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [acct, setAcct] = useState<Account | null>(null);
  const [cities, setCities] = useState<string[]>([]);
  const [saved, setSaved] = useState(false);
  const [roles, setRoles] = useState<string[]>([]);
  const [skills, setSkills] = useState<string[]>([]);
  const [profSaved, setProfSaved] = useState(false);

  const loadAccount = useCallback(async () => {
    const res = await fetch("/api/account");
    if (res.status === 401) { setStep("email"); return; }
    const data: Account = await res.json();
    setAcct(data);
    setCities(data.prefs?.preferred_locations ?? []);
    setRoles(data.profile?.role_titles ?? []);
    setSkills(data.profile?.skills ?? []);
    setStep("authed");
  }, []);

  async function saveProfile() {
    setProfSaved(false);
    const res = await fetch("/api/account", {
      method: "PATCH", headers: { "content-type": "application/json" },
      body: JSON.stringify({ role_titles: roles, skills }),
    });
    if (res.ok) setProfSaved(true);
  }

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) loadAccount();
      else setStep("email");
    });
  }, [supabase, loadAccount]);

  async function savePrefs(patch: Prefs) {
    setSaved(false);
    const res = await fetch("/api/account", { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify(patch) });
    if (res.ok) { const d = await res.json(); setAcct((a) => a ? { ...a, prefs: d.prefs } : a); setSaved(true); }
  }

  async function google() {
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback?next=/account` },
    });
    if (error) setError("Couldn't start Google sign-in. Please try again.");
  }

  const [finding, setFinding] = useState(false);
  const [findMsg, setFindMsg] = useState<string | null>(null);

  async function findNow() {
    setFinding(true); setFindMsg(null);
    try {
      const res = await fetch("/api/account/run", { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (res.status === 429) { setFindMsg(data.error); setFinding(false); return; }
      if (!res.ok && res.status !== 202) { setFindMsg(data.error ?? "Couldn't start the search."); setFinding(false); return; }
      // The worker runs in the background; poll for results.
      setFindMsg("Searching across all sources… new jobs will appear here shortly.");
      setTimeout(loadAccount, 25000);
      setTimeout(async () => { await loadAccount(); setFinding(false); setFindMsg("Done. You can search again anytime."); }, 55000);
    } catch { setFindMsg("Network hiccup — please try again."); setFinding(false); }
  }

  async function logout() { await supabase.auth.signOut(); setAcct(null); setStep("email"); }

  async function deleteAccount() {
    if (!confirm("Permanently delete your account, profile, history, and resume file?")) return;
    await fetch("/api/account", { method: "DELETE" });
    await logout();
    setInfo("Your data has been deleted.");
  }

  if (step === "loading") return <main className="wrap"><p className="sub">Loading…</p></main>;

  if (step !== "authed") {
    return (
      <main className="wrap">
        <h1>Sign in</h1>
        <p className="sub">Sign in to manage your preferences and see your matched jobs.</p>
        <div className="card">
          <button type="button" onClick={google} style={{ marginTop: 0, background: "#fff", color: "#1f2937" }}>
            Continue with Google
          </button>
          <p className="hint" style={{ textAlign: "center", marginBottom: 0 }}>Email sign-in is coming soon.</p>
          {info && <div className="msg ok">{info}</div>}
          {error && <div className="msg err">{error}</div>}
        </div>
      </main>
    );
  }

  // Authenticated
  const p = acct?.prefs ?? {};
  return (
    <main className="wrap">
      <h1>Your account</h1>
      <p className="sub">{acct?.email} · <a onClick={logout} style={{ cursor: "pointer" }}>Sign out</a></p>

      {!acct?.found ? (
        <div className="card"><div className="msg warn">Let's finish setting up — <a href="/onboarding">upload your résumé</a> to get started.</div></div>
      ) : (
        <>
          <div className="card" style={{ marginBottom: 18 }}>
            <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>Your profile</h2>
            <p className="hint" style={{ marginTop: 0 }}>Fix anything we mis-read from your resume.</p>
            <label>Target roles</label>
            <TagInput value={roles} onChange={setRoles} placeholder="e.g. Full-Stack Developer" max={8} />
            <label style={{ marginTop: 16 }}>Skills</label>
            <TagInput value={skills} onChange={setSkills} placeholder="e.g. React, Node.js, Python" max={30} />
            <button onClick={saveProfile} style={{ width: "auto", padding: "8px 14px", marginTop: 16 }}>Save profile</button>
            {profSaved && <p className="hint" style={{ color: "var(--ok)" }}>Saved. Applies on your next search.</p>}
            {acct?.profile?.location && <p className="hint">Resume location: {acct.profile.location}</p>}
          </div>

          <div className="card" style={{ marginBottom: 18 }}>
            <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>Preferences</h2>
            <label htmlFor="scope">Job location</label>
            <select id="scope" value={p.location_scope ?? "mix"} onChange={(e) => savePrefs({ location_scope: e.target.value })}>
              <option value="mix">Both, balanced (50/50)</option>
              <option value="in_country">Within my country (incl. remote)</option>
              <option value="outside_only">Outside my country (international)</option>
            </select>

            <label htmlFor="remote">Remote work</label>
            <select id="remote" value={p.remote_mode ?? "include_remote"} onChange={(e) => savePrefs({ remote_mode: e.target.value })}>
              <option value="include_remote">Include remote and onsite</option>
              <option value="only_remote">Only remote</option>
              <option value="no_remote">No remote (onsite only)</option>
            </select>

            <label style={{ marginTop: 16 }}>Preferred cities (optional, overrides location)</label>
            <TagInput value={cities} onChange={(next) => { setCities(next); savePrefs({ preferred_locations: next }); }}
              placeholder="e.g. Ahmedabad, Pune" max={5} />
            {saved && <p className="hint" style={{ color: "var(--ok)" }}>Saved. Applies on the next daily run.</p>}
          </div>

          <div className="card" style={{ marginBottom: 18 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
              <h2 style={{ fontSize: "1.05rem", margin: 0 }}>Your jobs ({acct?.jobs?.length ?? 0})</h2>
              <button onClick={findNow} disabled={finding} style={{ width: "auto", margin: 0, padding: "8px 14px" }}>
                {finding ? "Searching…" : "Find new jobs now"}
              </button>
            </div>
            {findMsg && <div className="msg ok" style={{ marginTop: 12 }}>{findMsg}</div>}
            <div style={{ marginTop: 14 }} />
            {(acct?.jobs?.length ?? 0) === 0 ? (
              <p className="hint">No jobs yet. They arrive on the next daily run.</p>
            ) : (
              <ul className="jobs">
                {acct!.jobs!.map((j) => <JobCard key={j.canonical_key} job={j as Job} />)}
              </ul>
            )}
          </div>

          {(acct?.saved?.length ?? 0) > 0 && (
            <div className="card" style={{ marginBottom: 18 }}>
              <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>★ Saved ({acct!.saved!.length})</h2>
              <ul className="jobs">{acct!.saved!.map((j) => <JobCard key={"s" + j.canonical_key} job={j as Job} />)}</ul>
            </div>
          )}

          {(acct?.applied?.length ?? 0) > 0 && (
            <div className="card" style={{ marginBottom: 18 }}>
              <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>Applications ({acct!.applied!.length})</h2>
              <ul className="jobs">{acct!.applied!.map((j) => <JobCard key={"a" + j.canonical_key} job={j as Job} />)}</ul>
            </div>
          )}

          <div className="card">
            <button className="danger" onClick={deleteAccount}>Delete my account and data</button>
          </div>
        </>
      )}
    </main>
  );
}
