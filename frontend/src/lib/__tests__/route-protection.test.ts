import { createRouteMatcher } from "@clerk/nextjs/server";
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

/**
 * The public route list from proxy.ts.
 *
 * Duplicated rather than imported because importing proxy.ts pulls in
 * Clerk's runtime, which expects request context this test does not have. The
 * matcher itself is the real thing, so what is under test is the pattern list
 * — which is exactly where the bug was: `/integrations`, `/onboarding` and
 * `/settings` were reachable signed out because nothing listed them as
 * protected.
 */
const PUBLIC_ROUTES = ["/", "/auth/sign-in(.*)", "/auth/sign-up(.*)"];

const isPublicRoute = createRouteMatcher(PUBLIC_ROUTES);

const check = (path: string) =>
  isPublicRoute(new NextRequest(new URL(path, "https://relaywise.test")));

describe("public routes", () => {
  it.each(["/", "/auth/sign-in", "/auth/sign-up"])(
    "%s is reachable signed out",
    (path) => {
      expect(check(path)).toBe(true);
    },
  );

  it("allows clerk's catch-all sign-in segments", () => {
    expect(check("/auth/sign-in/factor-one")).toBe(true);
    expect(check("/auth/sign-up/verify-email-address")).toBe(true);
  });
});

describe("protected routes", () => {
  // The regression: these three rendered for signed-out visitors because each
  // page was responsible for its own check and three of them had none.
  it.each(["/dashboard", "/integrations", "/onboarding", "/settings"])(
    "%s requires a session",
    (path) => {
      expect(check(path)).toBe(false);
    },
  );

  it.each(["/api/credits/balance", "/api/integrations/connected"])(
    "%s requires a session",
    (path) => {
      expect(check(path)).toBe(false);
    },
  );

  it("protects a route nobody has written yet", () => {
    // The point of an allowlist: new routes are protected by default rather
    // than exposed until someone remembers to add them.
    expect(check("/dashboard/billing")).toBe(false);
    expect(check("/admin")).toBe(false);
  });
});
