import { NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabaseAdmin";
import { sessionEmail } from "@/lib/supabaseServer";

export const runtime = "nodejs";
export const maxDuration = 60; // the worker fetch can take a while (cold start)

const COOLDOWN_MS = 60_000;

// On-demand "find new jobs now" for the signed-in user. Rate-limited; the worker
// dedups against history so no old jobs reappear.
export async function POST() {
  const email = await sessionEmail();
  if (!email) return NextResponse.json({ error: "Not signed in" }, { status: 401 });

  const supabase = supabaseAdmin();
  const { data: user } = await supabase
    .from("users")
    .select("id, channel_prefs")
    .ilike("email", email)
    .limit(1)
    .maybeSingle();
  if (!user) return NextResponse.json({ error: "No profile for this account" }, { status: 404 });

  const prefs = (user.channel_prefs as Record<string, unknown>) ?? {};
  const last = typeof prefs.last_manual_run === "string" ? Date.parse(prefs.last_manual_run) : 0;
  const elapsed = Date.now() - last;
  if (elapsed < COOLDOWN_MS) {
    return NextResponse.json(
      { error: `Please wait ${Math.ceil((COOLDOWN_MS - elapsed) / 1000)}s before searching again.` },
      { status: 429 },
    );
  }
  await supabase
    .from("users")
    .update({ channel_prefs: { ...prefs, last_manual_run: new Date().toISOString() } })
    .eq("id", user.id);

  try {
    const res = await fetch(`${process.env.WORKER_URL}/run-user`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_id: user.id, limit: 20 }),
    });
    if (!res.ok) return NextResponse.json({ error: "We couldn't complete the search just now. Please try again shortly." }, { status: 502 });
    return NextResponse.json(await res.json());
  } catch {
    // Worker still completes server-side even if our wait timed out.
    return NextResponse.json({ pending: true, message: "Search started — refresh in a moment." }, { status: 202 });
  }
}
