import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const { userId } = await auth();

    if (!userId) {
      return new NextResponse("Unauthorized", { status: 401 });
    }

    const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
    const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;

    if (!redisUrl || !redisToken) {
      console.error("[CREDITS_BALANCE] Redis credentials missing");
      return NextResponse.json({
        remaining_credits: 100.0,
        total_credits: 100.0,
        used_credits: 0.0,
        error: "Redis not configured"
      });
    }

    // Fetch credits directly from Redis
    const key = `user_credits:${userId}`;
    const fetchUrl = `${redisUrl}/get/${key}`;
    
    const response = await fetch(fetchUrl, {
      headers: { Authorization: `Bearer ${redisToken}` },
    });

    if (!response.ok) {
      const text = await response.text();
      console.error("[CREDITS_BALANCE] Redis error:", response.status, text);
      return NextResponse.json({
        remaining_credits: 100.0,
        total_credits: 100.0,
        used_credits: 0.0,
        error: "Failed to fetch from Redis"
      });
    }

    const data = await response.json();
    const remaining = data.result;

    if (remaining === null) {
      // Key doesn't exist - credits not initialized or expired
      console.warn(`[CREDITS_BALANCE] No credit key found for user ${userId}`);
      return NextResponse.json({
        remaining_credits: 0.0,
        total_credits: 100.0,
        used_credits: 100.0,
      });
    }

    const remainingFloat = parseFloat(remaining);
    const used = Math.max(0.0, 100.0 - remainingFloat);

    return NextResponse.json({
      remaining_credits: remainingFloat,
      total_credits: 100.0,
      used_credits: used,
    });
  } catch (error) {
    console.error("[CREDITS_BALANCE_GET]", error);
    
    // Return default credits on error (fail-open)
    return NextResponse.json({
      remaining_credits: 100.0,
      total_credits: 100.0,
      used_credits: 0.0,
      error: "Failed to fetch credits"
    });
  }
}
