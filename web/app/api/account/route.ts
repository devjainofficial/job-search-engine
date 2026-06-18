import { NextRequest, NextResponse } from "next/server";
import { RESUME_BUCKET, supabaseAdmin } from "@/lib/supabaseAdmin";
import { sessionEmail } from "@/lib/supabaseServer";

export const runtime = "nodejs";

const SCOPES = ["mix", "in_country", "outside_only"];
const REMOTE_MODES = ["include_remote", "only_remote", "no_remote"];

// Find the app user row for the logged-in email (case-insensitive).
async function currentUser() {
  const email = await sessionEmail();
  if (!email) return { email: null, user: null };
  const { data } = await supabaseAdmin()
    .from("users")
    .select("id, email, channel_prefs")
    .ilike("email", email)
    .limit(1)
    .maybeSingle();
  return { email, user: data };
}

export async function GET() {
  const { email, user } = await currentUser();
  if (!email) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  if (!user) return NextResponse.json({ found: false, email });

  const supabase = supabaseAdmin();
  const { data: profile } = await supabase
    .from("profiles")
    .select("role_titles, skills, location, remote_pref, years_experience, parsed_at")
    .eq("user_id", user.id)
    .maybeSingle();

  const { data: sent } = await supabase
    .from("sent_jobs")
    .select("canonical_key, sent_at")
    .eq("user_id", user.id)
    .order("sent_at", { ascending: false })
    .limit(50);

  let jobs: unknown[] = [];
  const keys = (sent ?? []).map((r) => r.canonical_key);
  if (keys.length) {
    const { data: cache } = await supabase
      .from("job_cache")
      .select("canonical_key, title, company, location, apply_url, apply_url_type, source")
      .in("canonical_key", keys);
    const byKey = new Map((cache ?? []).map((c) => [c.canonical_key, c]));
    jobs = (sent ?? [])
      .map((r) => {
        const j = byKey.get(r.canonical_key);
        return j ? { ...j, sent_at: r.sent_at } : null;
      })
      .filter(Boolean);
  }

  return NextResponse.json({ found: true, email, prefs: user.channel_prefs ?? {}, profile, jobs });
}

export async function PATCH(req: NextRequest) {
  const { email, user } = await currentUser();
  if (!email) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  if (!user) return NextResponse.json({ error: "No profile for this account" }, { status: 404 });

  const body = await req.json().catch(() => ({}));
  const update: Record<string, unknown> = {};
  if (body.location_scope !== undefined) {
    if (!SCOPES.includes(body.location_scope)) return NextResponse.json({ error: "Invalid location_scope" }, { status: 400 });
    update.location_scope = body.location_scope;
  }
  if (body.remote_mode !== undefined) {
    if (!REMOTE_MODES.includes(body.remote_mode)) return NextResponse.json({ error: "Invalid remote_mode" }, { status: 400 });
    update.remote_mode = body.remote_mode;
  }
  if (body.preferred_locations !== undefined) {
    if (!Array.isArray(body.preferred_locations)) return NextResponse.json({ error: "preferred_locations must be an array" }, { status: 400 });
    update.preferred_locations = body.preferred_locations.map((s: unknown) => String(s).trim()).filter(Boolean).slice(0, 5);
  }
  if (Object.keys(update).length === 0) return NextResponse.json({ error: "Nothing to update" }, { status: 400 });

  const prefs = { ...(user.channel_prefs ?? { telegram: true }), ...update };
  const { error } = await supabaseAdmin().from("users").update({ channel_prefs: prefs }).eq("id", user.id);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true, prefs });
}

export async function DELETE() {
  const { email, user } = await currentUser();
  if (!email) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  if (!user) return NextResponse.json({ ok: true }); // nothing to delete

  const supabase = supabaseAdmin();
  const { data: profile } = await supabase
    .from("profiles")
    .select("raw_resume_path")
    .eq("user_id", user.id)
    .maybeSingle();
  if (profile?.raw_resume_path) {
    try { await supabase.storage.from(RESUME_BUCKET).remove([profile.raw_resume_path]); } catch {}
  }
  await supabase.from("users").delete().eq("id", user.id); // cascades profile/searches/sent_jobs
  return NextResponse.json({ ok: true, deleted: true });
}
