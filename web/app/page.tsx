"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabaseBrowser } from "@/lib/supabaseBrowser";

export default function Home() {
  const supabase = supabaseBrowser();
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) router.replace("/onboarding"); // routes onward to /account if already set up
      else setChecking(false);
    });
  }, [supabase, router]);

  async function google() {
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback?next=/onboarding` },
    });
    if (error) setError("Couldn't start Google sign-in. Please try again.");
  }

  if (checking) return <main className="hero"><p className="sub">Loading…</p></main>;

  return (
    <main className="hero">
      <h1>Your next job, delivered daily</h1>
      <p className="sub">
        Sign in, upload your résumé once, and we'll match jobs across many sources every day —
        with direct apply links, straight to your Telegram. Free.
      </p>
      <button className="g-btn" onClick={google}>Continue with Google</button>
      {error && <div className="msg err" style={{ maxWidth: 380 }}>{error}</div>}
      <p className="hint" style={{ marginTop: 22 }}>We use your email only to sign you in. Email sign-in coming soon.</p>
    </main>
  );
}
