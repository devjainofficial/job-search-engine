import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabaseAdmin";

export const runtime = "nodejs";

const SCOPES = ["mix", "in_country", "outside_only"];
const REMOTE_MODES = ["include_remote", "only_remote", "no_remote"];

export async function GET(req: NextRequest) {
  const userId = req.nextUrl.searchParams.get("userId");
  if (!userId) return NextResponse.json({ error: "Missing userId" }, { status: 400 });
  const { data } = await supabaseAdmin()
    .from("users")
    .select("channel_prefs")
    .eq("id", userId)
    .single();
  const prefs = (data?.channel_prefs as { location_scope?: string; remote_mode?: string }) ?? {};
  return NextResponse.json({
    location_scope: prefs.location_scope ?? "mix",
    remote_mode: prefs.remote_mode ?? "include_remote",
  });
}

// Update a user's location preference (stored in users.channel_prefs).
// NOTE: unauthenticated for now; add identity checks before public launch.
export async function POST(req: NextRequest) {
  const { userId, location_scope, remote_mode } = await req.json().catch(() => ({}));
  if (!userId) return NextResponse.json({ error: "Missing userId" }, { status: 400 });

  const update: Record<string, string> = {};
  if (location_scope !== undefined) {
    if (!SCOPES.includes(location_scope)) {
      return NextResponse.json({ error: "Invalid location_scope" }, { status: 400 });
    }
    update.location_scope = location_scope;
  }
  if (remote_mode !== undefined) {
    if (!REMOTE_MODES.includes(remote_mode)) {
      return NextResponse.json({ error: "Invalid remote_mode" }, { status: 400 });
    }
    update.remote_mode = remote_mode;
  }
  if (Object.keys(update).length === 0) {
    return NextResponse.json({ error: "Nothing to update" }, { status: 400 });
  }

  const supabase = supabaseAdmin();
  const { data: existing } = await supabase
    .from("users")
    .select("channel_prefs")
    .eq("id", userId)
    .single();
  if (!existing) return NextResponse.json({ error: "User not found" }, { status: 404 });

  const prefs = { ...(existing.channel_prefs ?? { telegram: true }), ...update };
  const { error } = await supabase.from("users").update({ channel_prefs: prefs }).eq("id", userId);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true, ...update });
}
