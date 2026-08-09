import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const { userId } = await auth();
    if (!userId) {
      return new NextResponse("Unauthorized", { status: 401 });
    }

    const { slug } = await req.json();
    if (!slug) {
      return new NextResponse("Missing app slug", { status: 400 });
    }

    const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
    const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;
    const redisKey = `connected_apps:${userId}`;

    // 1. Get the connectedAccountId from Redis (needed for Composio revocation)
    const getRes = await fetch(`${redisUrl}/hget/${redisKey}/${slug}`, {
      headers: { Authorization: `Bearer ${redisToken}` },
    });
    const accountData = await getRes.json();
    const connectedAccountId = accountData.result;

    // 2. Delete from Redis immediately — so refresh won't re-show the app
    await fetch(`${redisUrl}/hdel/${redisKey}/${slug}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${redisToken}` },
    });

    // 3. Also clean up the reverse index
    if (connectedAccountId) {
      fetch(`${redisUrl}/del/account_owner:${connectedAccountId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${redisToken}` },
      }).catch(() => {});
    }

    const controlEndpoint = process.env.COMPOSIO_CONTROL_URL;
    if (!controlEndpoint) throw new Error("COMPOSIO_CONTROL_URL is not configured");
    // Revoke the connection through the Composio control plane.
    fetch(`${controlEndpoint}/disconnect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "disconnect_app",
        userId,
        appSlug: slug,
        connectedAccountId,
      }),
    }).catch((err) => console.error("Connection revoke failed:", err));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("[DISCONNECT_APP]", error);
    return new NextResponse("Internal Error", { status: 500 });
  }
}
