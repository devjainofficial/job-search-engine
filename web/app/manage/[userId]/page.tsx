"use client";

import { use, useState } from "react";

export default function Manage({ params }: { params: Promise<{ userId: string }> }) {
  const { userId } = use(params);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);

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
