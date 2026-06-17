import { NextRequest, NextResponse } from "next/server";
import { supabaseAdmin } from "@/lib/supabaseAdmin";

export const runtime = "nodejs";

const SCOPES = ["mix", "in_country", "outside_only"];

export async function GET(req: NextRequest) {
  const userId = req.nextUrl.searchParams.get("userId");
  if (!userId) return NextResponse.json({ error: "Missing userId" }, { status: 400 });
  const { data } = await supabaseAdmin()
    .from("users")
    .select("channel_prefs")
    .eq("id", userId)
    .single();
  const scope = (data?.channel_prefs as { location_scope?: string })?.location_scope ?? "mix";
  return NextResponse.json({ location_scope: scope });
}

// Update a user's location preference (stored in users.channel_prefs).
// NOTE: unauthenticated for now; add identity checks before public launch.
export async function POST(req: NextRequest) {
  const { userId, location_scope } = await req.json().catch(() => ({}));
  if (!userId) return NextResponse.json({ error: "Missing userId" }, { status: 400 });
  if (!SCOPES.includes(location_scope)) {
    return NextResponse.json({ error: "Invalid location_scope" }, { status: 400 });
  }

  const supabase = supabaseAdmin();
  const { data: existing } = await supabase
    .from("users")
    .select("channel_prefs")
    .eq("id", userId)
    .single();
  if (!existing) return NextResponse.json({ error: "User not found" }, { status: 404 });

  const prefs = { ...(existing.channel_prefs ?? { telegram: true }), location_scope };
  const { error } = await supabase.from("users").update({ channel_prefs: prefs }).eq("id", userId);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json({ ok: true, location_scope });
}
