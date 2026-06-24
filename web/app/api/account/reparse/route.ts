import { NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabaseAdmin";
import { sessionEmail } from "@/lib/supabaseServer";

export const runtime = "nodejs";
export const maxDuration = 60;

// Re-run résumé parsing for the signed-in user (fixes a failed/incomplete parse).
export async function POST() {
  const email = await sessionEmail();
  if (!email) return NextResponse.json({ error: "Not signed in" }, { status: 401 });

  const supabase = supabaseAdmin();
  const { data: user } = await supabase.from("users").select("id").ilike("email", email).limit(1).maybeSingle();
  if (!user) return NextResponse.json({ error: "No profile" }, { status: 404 });

  try {
    const res = await fetch(`${process.env.WORKER_URL}/parse-resume`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_id: user.id }),
    });
    if (res.status === 404) return NextResponse.json({ error: "No résumé on file. Please re-upload via onboarding." }, { status: 404 });
    if (!res.ok) return NextResponse.json({ error: "Couldn't read your résumé this time. Please try again." }, { status: 502 });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ error: "Parser is waking up — try again in a moment." }, { status: 502 });
  }
}
