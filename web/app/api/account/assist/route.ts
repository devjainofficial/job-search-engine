import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabaseAdmin";
import { sessionEmail } from "@/lib/supabaseServer";

export const runtime = "nodejs";
export const maxDuration = 60;

// Proxy to the worker's AI apply-assist for one job (session-authorized).
export async function POST(req: NextRequest) {
  const email = await sessionEmail();
  if (!email) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  const { canonical_key } = await req.json().catch(() => ({}));
  if (!canonical_key) return NextResponse.json({ error: "Missing job" }, { status: 400 });

  const supabase = supabaseAdmin();
  const { data: user } = await supabase.from("users").select("id").ilike("email", email).limit(1).maybeSingle();
  if (!user) return NextResponse.json({ error: "No profile" }, { status: 404 });

  try {
    const res = await fetch(`${process.env.WORKER_URL}/apply-assist`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_id: user.id, canonical_key }),
    });
    if (!res.ok) return NextResponse.json({ error: "Couldn't draft this one. Please try again." }, { status: 502 });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ error: "Drafting service is waking up — try again in a moment." }, { status: 502 });
  }
}
