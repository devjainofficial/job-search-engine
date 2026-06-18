import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

// Server auth client bound to the request cookies. Use in route handlers /
// server components to read the logged-in user (the verified session).
export async function supabaseServer() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (toSet) => {
          try {
            toSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
          } catch {
            // called from a Server Component; middleware refreshes the session.
          }
        },
      },
    },
  );
}

// The verified email of the current session, or null. Authorization key.
export async function sessionEmail(): Promise<string | null> {
  const supabase = await supabaseServer();
  const { data } = await supabase.auth.getUser();
  return data.user?.email ?? null;
}
