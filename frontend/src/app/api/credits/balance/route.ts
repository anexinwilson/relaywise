import { auth } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

/**
 * Credit balance for the signed-in user.
 *
 * Credits exist as a spend guardrail on the LLM budget, not as billing. The
 * balance lives in Redis under `user_credits:{userId}` and is seeded on first
 * read — a missing key means "new user", not "exhausted". Reading it as
 * exhausted showed every new account a full red bar before they had sent a
 * single message.
 *
 * Deduction is not yet wired: the worker computes token usage but nothing
 * writes it back yet, so this currently only ever reports the starting balance.
 */

const STARTING_CREDITS = 100;
const KEY_TTL_SECONDS = 45 * 24 * 60 * 60;

/**
 * Month-scoped key, matching `backend/src/credits/period.py` and
 * `api/app/services/credits.py`. The allowance resets because the key changes
 * at the month boundary, not because anything is scheduled to run.
 */
function balanceKey(userId: string): string {
  const now = new Date();
  const period = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`;
  return `user_credits:${userId}:${period}`;
}

type Balance = {
  remaining_credits: number;
  total_credits: number;
  used_credits: number;
  error?: string;
};

function balance(remaining: number, error?: string): Balance {
  const clamped = Math.max(0, Math.min(remaining, STARTING_CREDITS));
  return {
    remaining_credits: clamped,
    total_credits: STARTING_CREDITS,
    used_credits: Math.max(0, STARTING_CREDITS - clamped),
    ...(error ? { error } : {}),
  };
}

async function redisCommand(base: string, token: string, path: string): Promise<unknown> {
  const response = await fetch(`${base}/${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Redis responded ${response.status}`);
  }
  const body = await response.json();
  return body.result;
}

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
  const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;

  if (!redisUrl || !redisToken) {
    console.error("[CREDITS] Redis is not configured");
    return NextResponse.json(balance(STARTING_CREDITS, "Redis not configured"));
  }

  const key = balanceKey(userId);

  try {
    const stored = await redisCommand(redisUrl, redisToken, `get/${key}`);

    if (stored === null || stored === undefined) {
      // First request of a new month. SETNX so two concurrent requests cannot
      // both seed, which would otherwise reset a balance mid-flight.
      await redisCommand(redisUrl, redisToken, `setnx/${key}/${STARTING_CREDITS}`);
      await redisCommand(redisUrl, redisToken, `expire/${key}/${KEY_TTL_SECONDS}`);
      return NextResponse.json(balance(STARTING_CREDITS));
    }

    const remaining = Number.parseFloat(String(stored));
    if (Number.isNaN(remaining)) {
      console.error("[CREDITS] Non-numeric balance stored for user");
      return NextResponse.json(balance(STARTING_CREDITS, "Invalid stored balance"));
    }

    return NextResponse.json(balance(remaining));
  } catch (error) {
    // Display-only surface: a Redis outage should not block the UI. The
    // enforcing check lives server-side in the worker and fails closed there.
    console.error("[CREDITS]", error);
    return NextResponse.json(balance(STARTING_CREDITS, "Failed to fetch credits"));
  }
}
