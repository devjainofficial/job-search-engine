import { createHmac } from "crypto";

// Twin of worker/app/connect_token.py. Same secret (Supabase service-role key)
// and construction so the worker can verify a token this app generates.
// token = uuid-hex(32) + hmac_sha256(secret, uuid-hex)[:16]

const SIG_LEN = 16;

function secret(): string {
  const s = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!s) throw new Error("Missing SUPABASE_SERVICE_ROLE_KEY");
  return s;
}

export function makeConnectToken(userId: string): string {
  const uuidHex = userId.replace(/-/g, "");
  const sig = createHmac("sha256", secret()).update(uuidHex).digest("hex").slice(0, SIG_LEN);
  return uuidHex + sig;
}

export function telegramConnectUrl(userId: string): string {
  const bot = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "";
  return `https://t.me/${bot}?start=${makeConnectToken(userId)}`;
}
