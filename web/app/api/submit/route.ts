import { NextRequest, NextResponse } from "next/server";
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
    return NextResponse.json({ error: "Invalid form submission" }, { status: 400 });
  }

  const email = String(form.get("email") ?? "").trim();
  const chatId = String(form.get("telegram_chat_id") ?? "").trim();
  const consent = form.get("consent");
  const file = form.get("resume");

  // Validation
  if (!email || !email.includes("@")) {
    return NextResponse.json({ error: "A valid email is required" }, { status: 400 });
  }
  if (!consent) {
    return NextResponse.json({ error: "Consent is required to process your resume" }, { status: 400 });
  }
  if (!(file instanceof File) || file.size === 0) {
    return NextResponse.json({ error: "Please attach your resume" }, { status: 400 });
  }
  if (file.size > MAX_BYTES) {
    return NextResponse.json({ error: "Resume must be under 3 MB" }, { status: 400 });
  }
  const lower = file.name.toLowerCase();
  if (!ALLOWED.some((ext) => lower.endsWith(ext))) {
    return NextResponse.json({ error: "Use a PDF, DOCX, or TXT file" }, { status: 400 });
  }

  const supabase = supabaseAdmin();

  // 1. Create the user with explicit consent (DPDP).
  const { data: user, error: userErr } = await supabase
    .from("users")
    .insert({
      email,
      telegram_chat_id: chatId || null,
      consent_at: new Date().toISOString(),
    })
    .select("id")
    .single();
  if (userErr || !user) {
    return NextResponse.json({ error: "Could not create account: " + (userErr?.message ?? "") }, { status: 500 });
  }
  const userId = user.id as string;

  // 2. Upload the raw resume to Storage (deletable after parsing per retention policy).
  const path = `${userId}/${sanitize(file.name)}`;
  const bytes = Buffer.from(await file.arrayBuffer());
  const { error: upErr } = await supabase.storage
    .from(RESUME_BUCKET)
    .upload(path, bytes, { contentType: file.type || "application/octet-stream", upsert: true });
  if (upErr) {
    await supabase.from("users").delete().eq("id", userId); // roll back
    return NextResponse.json({ error: "Upload failed: " + upErr.message }, { status: 500 });
  }

  // 3. Create the profile row pointing at the raw file (parsed_at set by the worker).
  await supabase.from("profiles").insert({ user_id: userId, raw_resume_path: path });

  // 4. Ask the worker to parse (parse-once lives in the Python service).
  try {
    const res = await fetch(`${process.env.WORKER_URL}/parse-resume`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
    if (!res.ok) {
      const detail = await res.text();
      return NextResponse.json(
        { userId, parsed: false, warning: "Saved, but parsing failed: " + detail },
        { status: 202 },
      );
    }
    const parsed = await res.json();
    return NextResponse.json({ userId, parsed: true, profile: parsed });
  } catch (e) {
    return NextResponse.json(
      { userId, parsed: false, warning: "Saved, but the parser is unreachable. It will be retried." },
      { status: 202 },
    );
  }
}
