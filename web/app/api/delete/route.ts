import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

// Proxy to the worker's DPDP delete so erasure logic (rows + storage file) lives
// in one place. NOTE: unauthenticated for now; add identity verification (e.g. a
// confirmation emailed link) before public launch.
export async function POST(req: NextRequest) {
  const { userId } = await req.json().catch(() => ({ userId: "" }));
  if (!userId) return NextResponse.json({ error: "Missing userId" }, { status: 400 });

  try {
    const res = await fetch(`${process.env.WORKER_URL}/users/${userId}`, { method: "DELETE" });
    if (!res.ok) {
      return NextResponse.json({ error: "Delete failed: " + (await res.text()) }, { status: 502 });
    }
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ error: "Worker unreachable" }, { status: 502 });
  }
}
