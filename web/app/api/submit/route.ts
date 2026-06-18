import { NextRequest, NextResponse } from "next/server";
import { telegramConnectUrl } from "@/lib/connectToken";
import { RESUME_BUCKET, supabaseAdmin } from "@/lib/supabaseAdmin";

export const runtime = "nodejs";

const ALLOWED = [".pdf", ".docx", ".doc", ".txt"];
const MAX_BYTES = 3 * 1024 * 1024; // 3 MB is plenty for a resume

function sanitize(name: string): string {
  return name.replace(/[^a-zA-Z0-9._-]/g, "_").slice(-100);
}

export async function POST(req: NextRequest) {
  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return NextResponse.json({ error: "Something went wrong submitting the form. Please try again." }, { status: 400 });
  }

  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const consent = form.get("consent");
  const file = form.get("resume");
  const SCOPES = ["mix", "in_country", "outside_only"];
  const rawScope = String(form.get("location_scope") ?? "mix");
  const locationScope = SCOPES.includes(rawScope) ? rawScope : "mix";
  const REMOTE_MODES = ["include_remote", "only_remote", "no_remote"];
  const rawRemote = String(form.get("remote_mode") ?? "include_remote");
  const remoteMode = REMOTE_MODES.includes(rawRemote) ? rawRemote : "include_remote";
  const preferredLocations = String(form.get("preferred_locations") ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 5); // cap to keep it sane

  // Validation (friendly, actionable messages)
  if (!email || !email.includes("@")) {
    return NextResponse.json({ error: "Please enter a valid email address." }, { status: 400 });
  }
  if (!consent) {
    return NextResponse.json({ error: "Please tick the consent box so we can process your resume." }, { status: 400 });
  }
  if (!(file instanceof File) || file.size === 0) {
    return NextResponse.json({ error: "Please attach your resume to continue." }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json({ error: "That file is over 3 MB. Please upload a smaller resume." }, { status: 400 });
  }
  const lower = file.name.toLowerCase();
  if (!ALLOWED.some((ext) => lower.endsWith(ext))) {
    return NextResponse.json({ error: "Please upload a PDF, DOCX, or TXT file." }, { status: 400 });
  }

  const supabase = supabaseAdmin();
  const prefs = {
    telegram: true,
    location_scope: locationScope,
    remote_mode: remoteMode,
    preferred_locations: preferredLocations,
  };

  // 1. One account per email: reuse an existing user (re-upload), else create.
  const { data: existing } = await supabase
    .from("users")
    .select("id")
    .ilike("email", email)
    .limit(1)
    .maybeSingle();

  let userId: string;
  let created = false;
  if (existing) {
    userId = existing.id as string;
    await supabase.from("users").update({ consent_at: new Date().toISOString(), channel_prefs: prefs }).eq("id", userId);
  } else {
    const { data: user, error: userErr } = await supabase
      .from("users")
      .insert({ email, consent_at: new Date().toISOString(), channel_prefs: prefs })
      .select("id")
      .single();
    if (userErr || !user) {
      return NextResponse.json({ error: "We couldn't create your account just now. Please try again in a moment." }, { status: 500 });
    }
    userId = user.id as string;
    created = true;
  }

  // 2. Upload the raw resume to Storage (deletable after parsing per retention policy).
  const path = `${userId}/${sanitize(file.name)}`;
  const bytes = Buffer.from(await file.arrayBuffer());
  const { error: upErr } = await supabase.storage
    .from(RESUME_BUCKET)
    .upload(path, bytes, { contentType: file.type || "application/octet-stream", upsert: true });
  if (upErr) {
    if (created) await supabase.from("users").delete().eq("id", userId); // roll back only a fresh account
    return NextResponse.json({ error: "We couldn't upload your resume. Please try again." }, { status: 500 });
  }

  // 3. Upsert the profile row pointing at the raw file (parsed_at set by the worker).
  await supabase.from("profiles").upsert({ user_id: userId, raw_resume_path: path }, { onConflict: "user_id" });

  // 4. Ask the worker to parse (parse-once lives in the Python service).
  try {
    const res = await fetch(`${process.env.WORKER_URL}/parse-resume`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
    const connectUrl = telegramConnectUrl(userId);
    if (!res.ok) {
      return NextResponse.json(
        { userId, connectUrl, parsed: false,
          warning: "You're signed up! We couldn't read your resume automatically this time — we'll retry it shortly, no action needed." },
        { status: 202 },
      );
    }
    const parsed = await res.json();
    return NextResponse.json({ userId, connectUrl, parsed: true, profile: parsed });
  } catch (e) {
    return NextResponse.json(
      { userId, connectUrl: telegramConnectUrl(userId), parsed: false,
        warning: "You're signed up! Our matching service is just waking up — your profile will be ready in a minute." },
      { status: 202 },
    );
  }
}
