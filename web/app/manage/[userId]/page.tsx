"use client";

import { use, useEffect, useState } from "react";

export default function Manage({ params }: { params: Promise<{ userId: string }> }) {
  const { userId } = use(params);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [scope, setScope] = useState("mix");
  const [remote, setRemote] = useState("include_remote");
  const [cities, setCities] = useState("");
  const [savedPref, setSavedPref] = useState(false);

  useEffect(() => {
    fetch(`/api/prefs?userId=${userId}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.location_scope) setScope(d.location_scope);
        if (d.remote_mode) setRemote(d.remote_mode);
        if (Array.isArray(d.preferred_locations)) setCities(d.preferred_locations.join(", "));
      })
      .catch(() => {});
  }, [userId]);

  async function savePref(patch: { location_scope?: string; remote_mode?: string; preferred_locations?: string[] }) {
    if (patch.location_scope) setScope(patch.location_scope);
    if (patch.remote_mode) setRemote(patch.remote_mode);
    setSavedPref(false);
    try {
      const res = await fetch("/api/prefs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ userId, ...patch }),
      });
      if (res.ok) setSavedPref(true);
    } catch {}
  }

  async function onDelete() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/delete", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ userId }),
      });
      const data = await res.json();
      if (!res.ok) setError(data.error ?? "Delete failed");
      else setDone(true);
    } catch {
      setError("Network error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="wrap">
      <h1>Manage your data</h1>
      <p className="sub">Your rights under the India DPDP Act.</p>

      {!done && (
        <div className="card" style={{ marginBottom: 18 }}>
          <label htmlFor="scope">Job location preference</label>
          <select id="scope" value={scope} onChange={(e) => savePref({ location_scope: e.target.value })}>
            <option value="mix">Both, balanced (50/50)</option>
            <option value="in_country">Within my country (incl. remote)</option>
            <option value="outside_only">Outside my country (international)</option>
          </select>

          <label htmlFor="remote">Remote work</label>
          <select id="remote" value={remote} onChange={(e) => savePref({ remote_mode: e.target.value })}>
            <option value="include_remote">Include remote and onsite</option>
            <option value="only_remote">Only remote</option>
            <option value="no_remote">No remote (onsite only)</option>
          </select>

          <label htmlFor="cities">Preferred cities (optional)</label>
          <input id="cities" type="text" value={cities} placeholder="e.g. Ahmedabad, Pune"
                 onChange={(e) => setCities(e.target.value)}
                 onBlur={() => savePref({ preferred_locations: cities.split(",").map((s) => s.trim()).filter(Boolean) })} />
          <p className="hint">If set, overrides the location choice above. Comma-separated, up to 5.</p>
          {savedPref && <p className="hint" style={{ color: "var(--ok)" }}>Saved. Applies on the next daily run.</p>}
        </div>
      )}

      <div className="card">
        {done ? (
          <div className="msg ok">
            <strong>All your data has been deleted.</strong> Your profile, saved searches, sent
            history, and uploaded resume file are gone. Thanks for trying the service.
          </div>
        ) : (
          <>
            <p>
              Deleting removes your account, your parsed profile, your sent-job history, and the raw
              resume file from storage. This cannot be undone.
            </p>
            <label className="consent">
              <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} />
              <span>I understand this permanently deletes all my data.</span>
            </label>
            <button className="danger" disabled={!confirm || busy} onClick={onDelete}>
              {busy ? "Deleting..." : "Delete my data"}
            </button>
            {error && <div className="msg err">{error}</div>}
          </>
        )}
        <div className="links">
          <a href="/">Back to start</a>
        </div>
      </div>
    </main>
  );
}
