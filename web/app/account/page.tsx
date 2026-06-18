"use client";

import { useCallback, useEffect, useState } from "react";
import { supabaseBrowser } from "@/lib/supabaseBrowser";

type Job = { title: string; company: string; location: string | null; apply_url: string; apply_url_type: string; source: string; sent_at: string };
type Profile = { role_titles: string[]; skills: string[]; location: string | null; years_experience: number | null } | null;
type Prefs = { location_scope?: string; remote_mode?: string; preferred_locations?: string[] };
type Account = { found: boolean; email: string; prefs?: Prefs; profile?: Profile; jobs?: Job[] };

const APPLY_LABEL: Record<string, string> = { direct_apply: "Apply", job_detail: "View posting", company_careers: "Careers", source_search: "Search" };

export default function AccountPage() {
  const supabase = supabaseBrowser();
  const [step, setStep] = useState<"loading" | "email" | "otp" | "authed">("loading");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [acct, setAcct] = useState<Account | null>(null);
  const [cities, setCities] = useState("");
  const [saved, setSaved] = useState(false);

  const loadAccount = useCallback(async () => {
    const res = await fetch("/api/account");
    if (res.status === 401) { setStep("email"); return; }
    const data: Account = await res.json();
    setAcct(data);
    setCities((data.prefs?.preferred_locations ?? []).join(", "));
    setStep("authed");
  }, []);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) loadAccount();
      else setStep("email");
    });
  }, [supabase, loadAccount]);

  async function sendOtp(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null); setInfo(null);
    const { error } = await supabase.auth.signInWithOtp({ email: email.trim(), options: { shouldCreateUser: true } });
    setBusy(false);
    if (error) setError(error.message);
    else { setStep("otp"); setInfo("We emailed you a 6-digit code. Enter it below."); }
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null);
    const { error } = await supabase.auth.verifyOtp({ email: email.trim(), token: code.trim(), type: "email" });
    setBusy(false);
    if (error) setError(error.message);
    else loadAccount();
  }

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
    if (error) setError(error.message);
  }

  async function logout() { await supabase.auth.signOut(); setAcct(null); setStep("email"); setEmail(""); setCode(""); }

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
        <p className="sub">Use the email you signed up with to manage preferences and see your jobs.</p>
        <div className="card">
          <button type="button" onClick={google} style={{ marginTop: 0, background: "#fff", color: "#1f2937" }}>
            Continue with Google
          </button>
          <p className="hint" style={{ textAlign: "center" }}>or use email</p>
          {step === "email" ? (
            <form onSubmit={sendOtp}>
              <label htmlFor="email">Email</label>
              <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
              <button type="submit" disabled={busy}>{busy ? "Sending…" : "Email me a code"}</button>
            </form>
          ) : (
            <form onSubmit={verify}>
              <label htmlFor="code">6-digit code</label>
              <input id="code" type="text" inputMode="numeric" required value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" />
              <button type="submit" disabled={busy}>{busy ? "Verifying…" : "Sign in"}</button>
            </form>
          )}
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
        <div className="card"><div className="msg warn">No profile found for this email. Upload your resume on the <a href="/">home page</a> first.</div></div>
      ) : (
        <>
          {acct?.profile && (
            <div className="card" style={{ marginBottom: 18 }}>
              <div className="profile-h">Detected roles</div>
              <div className="tags">{acct.profile.role_titles.map((r) => <span className="tag" key={r}>{r}</span>)}</div>
              <div className="profile-h">Skills</div>
              <div className="tags">{acct.profile.skills.slice(0, 14).map((s) => <span className="tag" key={s}>{s}</span>)}</div>
              {acct.profile.location && <p className="hint">Resume location: {acct.profile.location}</p>}
            </div>
          )}

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

            <label htmlFor="cities">Preferred cities (optional, overrides location)</label>
            <input id="cities" type="text" value={cities} placeholder="e.g. Ahmedabad, Pune"
              onChange={(e) => setCities(e.target.value)}
              onBlur={() => savePrefs({ preferred_locations: cities.split(",").map((s) => s.trim()).filter(Boolean) })} />
            {saved && <p className="hint" style={{ color: "var(--ok)" }}>Saved. Applies on the next daily run.</p>}
          </div>

          <div className="card" style={{ marginBottom: 18 }}>
            <h2 style={{ fontSize: "1.05rem", marginTop: 0 }}>Your jobs ({acct?.jobs?.length ?? 0})</h2>
            {(acct?.jobs?.length ?? 0) === 0 ? (
              <p className="hint">No jobs yet. They arrive on the next daily run.</p>
            ) : (
              <ul className="jobs">
                {acct!.jobs!.map((j, i) => (
                  <li key={i} className="job">
                    <div className="job-main">
                      <div className="job-title">{j.title}</div>
                      <div className="job-meta">{j.company}{j.location ? ` · ${j.location}` : ""} · <span className="src">{j.source}</span></div>
                    </div>
                    <a className="apply" href={j.apply_url} target="_blank" rel="noreferrer">{APPLY_LABEL[j.apply_url_type] ?? "Open"}</a>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="card">
            <button className="danger" onClick={deleteAccount}>Delete my account and data</button>
          </div>
        </>
      )}
    </main>
  );
}
