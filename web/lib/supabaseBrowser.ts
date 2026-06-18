import { createBrowserClient } from "@supabase/ssr";

// Browser auth client (anon key). Used by the /account page for email-OTP login.
export function supabaseBrowser() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
