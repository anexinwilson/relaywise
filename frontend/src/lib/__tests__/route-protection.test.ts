import { createRouteMatcher } from "@clerk/nextjs/server";
import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

/**
 * The route lists from proxy.ts.
 *
 * Duplicated rather than imported because importing the proxy pulls in Clerk's
 * runtime, which expects request context this test does not have. The matcher
 * itself is the real thing, so what is under test is the pattern list, which
 * is where the bug was: `/integrations` was reachable signed out because
 * nothing listed it as protected.
 */
const PUBLIC_ROUTES = ["/", "/auth/sign-in(.*)", "/auth/sign-up(.*)"];
const API_ROUTES = ["/api(.*)"];

const isPublicRoute = createRouteMatcher(PUBLIC_ROUTES);
const isApiRoute = createRouteMatcher(API_ROUTES);

const request = (path: string) =>
  new NextRequest(new URL(path, "https://relaywise.test"));

describe("public routes", () => {
  it.each(["/", "/auth/sign-in", "/auth/sign-up"])(
    "%s is reachable signed out",
    (path) => {
      expect(isPublicRoute(request(path))).toBe(true);
    },
  );

  it("allows clerk's catch-all sign-in segments", () => {
    expect(isPublicRoute(request("/auth/sign-in/factor-one"))).toBe(true);
    expect(isPublicRoute(request("/auth/sign-up/verify-email-address"))).toBe(true);
  });
});

describe("protected routes", () => {
  it.each(["/dashboard", "/integrations", "/onboarding", "/settings"])(
    "%s requires a session",
    (path) => {
      expect(isPublicRoute(request(path))).toBe(false);
    },
  );

  it("protects a route nobody has written yet", () => {
    // The point of an allowlist: a new route is protected by default rather
    // than exposed until someone remembers to add it.
    expect(isPublicRoute(request("/dashboard/billing"))).toBe(false);
    expect(isPublicRoute(request("/admin"))).toBe(false);
  });
});

describe("api routes", () => {
  it.each(["/api/credits/balance", "/api/integrations/connected"])(
    "%s is recognised as an api route",
    (path) => {
      expect(isApiRoute(request(path))).toBe(true);
    },
  );

  // API routes are skipped by the proxy so they can answer 401 with JSON.
  // Redirecting them to a sign-in page makes `fetch` fail on JSON.parse.
  it("does not treat a page as an api route", () => {
    expect(isApiRoute(request("/dashboard"))).toBe(false);
    expect(isApiRoute(request("/"))).toBe(false);
  });
});
