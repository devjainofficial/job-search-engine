import { NextRequest, NextResponse } from "next/server";
import { telegramConnectUrl } from "@/lib/connectToken";
import { RESUME_BUCKET, supabaseAdmin } from "@/lib/supabaseAdmin";
import { sessionEmail } from "@/lib/supabaseServer";

export const runtime = "nodejs";
export const maxDuration = 60;

const ALLOWED = [".pdf", ".docx", ".doc", ".txt"];
const MAX_BYTES = 3 * 1024 * 1024;
const sanitize = (n: string) => n.replace(/[^a-zA-Z0-9._-]/g, "_").slice(-100);

// Authenticated résumé upload + parse (onboarding). The user is already signed in
// (Google), so we key off the session email — no email field, no anonymous uploads.
export async function POST(req: NextRequest) {
  const email = await sessionEmail();
  if (!email) return NextResponse.json({ error: "Please sign in first." }, { status: 401 });

  let form: FormData;
  try { form = await req.formData(); }
  catch { return NextResponse.json({ error: "Something went wrong. Please try again." }, { status: 400 }); }

  const consent = form.get("consent");
  const file = form.get("resume");
  if (!consent) return NextResponse.json({ error: "Please accept the consent to continue." }, { status: 400 });
  if (!(file instanceof File) || file.size === 0) return NextResponse.json({ error: "Please attach your résumé." }, { status: 400 });
  if (file.size > MAX_BYTES) return NextResponse.json({ error: "That file is over 3 MB. Please upload a smaller résumé." }, { status: 400 });
  if (!ALLOWED.some((ext) => file.name.toLowerCase().endsWith(ext)))
    return NextResponse.json({ error: "Please upload a PDF, DOCX, or TXT file." }, { status: 400 });

  const supabase = supabaseAdmin();

  // Ensure one app user per email (the Google login may be brand new).
  const { data: existing } = await supabase.from("users").select("id, channel_prefs").ilike("email", email.toLowerCase()).limit(1).maybeSingle();
  let userId: string;
  let created = false;
  if (existing) {
    userId = existing.id as string;
    await supabase.from("users").update({ consent_at: new Date().toISOString() }).eq("id", userId);
  } else {
    const { data: u, error } = await supabase
      .from("users")
      .insert({ email: email.toLowerCase(), consent_at: new Date().toISOString(),
        channel_prefs: { telegram: true, location_scope: "mix", remote_mode: "include_remote", preferred_locations: [] } })
      .select("id").single();
    if (error || !u) return NextResponse.json({ error: "We couldn't set up your account. Please try again." }, { status: 500 });
    userId = u.id as string; created = true;
  }

  const path = `${userId}/${sanitize(file.name)}`;
  const bytes = Buffer.from(await file.arrayBuffer());
  const { error: upErr } = await supabase.storage.from(RESUME_BUCKET)
    .upload(path, bytes, { contentType: file.type || "application/octet-stream", upsert: true });
  if (upErr) {
    if (created) await supabase.from("users").delete().eq("id", userId);
    return NextResponse.json({ error: "We couldn't upload your résumé. Please try again." }, { status: 500 });
  }
  await supabase.from("profiles").upsert({ user_id: userId, raw_resume_path: path }, { onConflict: "user_id" });

  const connectUrl = telegramConnectUrl(userId);
  try {
    const res = await fetch(`${process.env.WORKER_URL}/parse-resume`, {
      method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ user_id: userId }),
    });
    if (!res.ok) return NextResponse.json({ userId, connectUrl, parsed: false, profile: null }, { status: 202 });
    const profile = await res.json();
    return NextResponse.json({ userId, connectUrl, parsed: true, profile });
  } catch {
    return NextResponse.json({ userId, connectUrl, parsed: false, profile: null }, { status: 202 });
  }
}
