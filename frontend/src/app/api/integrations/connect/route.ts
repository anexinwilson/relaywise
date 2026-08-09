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

    const controlEndpoint = process.env.COMPOSIO_CONTROL_URL;
    if (!controlEndpoint) throw new Error("COMPOSIO_CONTROL_URL is not configured");

    const res = await fetch(`${controlEndpoint}/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "get_auth_url",
        userId,
        appSlug: slug,
      }),
    });

    if (!res.ok) {
      throw new Error(`Connection service error: ${res.statusText}`);
    }

    const data = await res.json();
    if (data.success && data.url) {
      return NextResponse.json({ url: data.url });
    }

    return NextResponse.json(
      { error: data.error || "Failed to generate auth URL" },
      { status: 500 }
    );
  } catch (error) {
    console.error("[CONNECT_APP]", error);
    return new NextResponse("Internal Error", { status: 500 });
  }
}
