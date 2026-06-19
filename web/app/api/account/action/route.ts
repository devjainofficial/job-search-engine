import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabaseAdmin";
import { sessionEmail } from "@/lib/supabaseServer";

export const runtime = "nodejs";

const FEEDBACK = ["up", "down", null];
const STATUS = ["applied", "interviewing", "rejected", "offer", null];

// Save / thumbs feedback / application status for one job (session-authorized).
// A display snapshot is stored so saved/applied jobs render after cache prune.
export async function POST(req: NextRequest) {
  const email = await sessionEmail();
  if (!email) return NextResponse.json({ error: "Not signed in" }, { status: 401 });

  const b = await req.json().catch(() => ({}));
  if (!b.canonical_key) return NextResponse.json({ error: "Missing job" }, { status: 400 });
  if (b.feedback !== undefined && !FEEDBACK.includes(b.feedback))
    return NextResponse.json({ error: "Invalid feedback" }, { status: 400 });
  if (b.status !== undefined && !STATUS.includes(b.status))
    return NextResponse.json({ error: "Invalid status" }, { status: 400 });

  const supabase = supabaseAdmin();
  const { data: user } = await supabase.from("users").select("id").ilike("email", email).limit(1).maybeSingle();
  if (!user) return NextResponse.json({ error: "No profile" }, { status: 404 });

  const row: Record<string, unknown> = {
    user_id: user.id,
    canonical_key: b.canonical_key,
    updated_at: new Date().toISOString(),
  };
  if (b.saved !== undefined) row.saved = !!b.saved;
  if (b.feedback !== undefined) row.feedback = b.feedback;
  if (b.status !== undefined) row.status = b.status;
  // Snapshot for display (only overwrites if provided).
  for (const f of ["title", "company", "location", "apply_url", "apply_url_type", "source"]) {
    if (b.job?.[f] !== undefined) row[f] = b.job[f];
  }

  const { error } = await supabase.from("job_actions").upsert(row, { onConflict: "user_id,canonical_key" });
  if (error) return NextResponse.json({ error: "Couldn't save. Please try again." }, { status: 500 });
  return NextResponse.json({ ok: true });
}
