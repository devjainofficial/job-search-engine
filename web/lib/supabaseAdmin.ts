import { createClient } from "@supabase/supabase-js";

// Service-role client. SERVER ONLY: never import this into a client component.
// There are no RLS policies yet, so this key must stay on the server.
export function supabaseAdmin() {
  const url = process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  }
  return createClient(url, key, { auth: { persistSession: false } });
}

export const RESUME_BUCKET = "resumes";
