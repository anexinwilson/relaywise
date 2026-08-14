import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import catalog from "@/apps_catalog.json";

// Build a slug → { name, logo } lookup map at module level (free, runs once)
const catalogMap = Object.fromEntries(
  (catalog as { slug: string; name: string; logo: string }[]).map((app) => [
    app.slug,
    { name: app.name, logo: app.logo },
  ]),
);

export async function GET() {
  try {
    const { userId } = await auth();

    if (!userId) {
      return new NextResponse("Unauthorized", { status: 401 });
    }

    // No sync here: the integrations page calls the syncConnections mutation,
    // which reconciles Redis with Composio. This route is the cheap read used
    // by the dashboard, so it must not depend on a control-plane round trip.

    const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
    const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;

    if (!redisUrl || !redisToken) {
      console.error("Redis credentials missing");
      return NextResponse.json({ apps: [], slugs: [] });
    }

    // Fetch slugs (hash keys) from Redis
    const redisKey = `connected_apps:${userId}`;
    const fetchUrl = `${redisUrl}/hkeys/${redisKey}`;
    console.log("[CONNECTED_APPS] userId:", userId);
    console.log("[CONNECTED_APPS] fetching:", fetchUrl);

    const response = await fetch(fetchUrl, {
      headers: { Authorization: `Bearer ${redisToken}` },
    });

    if (!response.ok) {
      const text = await response.text();
      console.error("[CONNECTED_APPS] Redis error:", response.status, text);
      throw new Error(`Redis error: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("[CONNECTED_APPS] raw Redis response:", JSON.stringify(data));
    const slugs: string[] = data.result || [];

    // Enrich with name + logo from local catalog
    const apps = slugs.map((slug) => ({
      slug,
      name: catalogMap[slug]?.name ?? slug,
      logo: catalogMap[slug]?.logo ?? `https://logos.composio.dev/api/${slug}`,
    }));

    console.log("[CONNECTED_APPS] returning:", slugs.length, "apps");
    return NextResponse.json({ apps, slugs });
  } catch (error) {
    console.error("[CONNECTED_APPS_GET]", error);
    return NextResponse.json({ apps: [], slugs: [] });
  }
}
