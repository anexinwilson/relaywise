import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Route protection.
 *
 * The list is public, not protected. Naming the protected routes instead means
 * a page added later is reachable signed out until someone remembers to list
 * it, which is how `/integrations` was left open while `/dashboard`,
 * `/settings` and `/onboarding` were covered.
 *
 * Next 16 renamed `middleware.ts` to `proxy.ts`. The two cannot coexist: Next
 * refuses to serve any route at all when both are present.
 */
const isPublicRoute = createRouteMatcher(["/", "/auth/sign-in(.*)", "/auth/sign-up(.*)"]);

/**
 * API routes authenticate themselves and must not be redirected.
 *
 * `auth.protect()` answers a signed-out request with a 307 to the sign-in
 * page. That is right for a page and wrong for `fetch`, which follows the
 * redirect, receives HTML and fails on `JSON.parse`. Each route under /api
 * calls `auth()` and returns a 401, which a JSON caller can handle.
 */
const isApiRoute = createRouteMatcher(["/api(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isApiRoute(req)) return;
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  // Skip Next internals and static files. Kept simple on purpose: Turbopack
  // handled complex matcher patterns differently from webpack before 16.3.0,
  // which produced a routing manifest Vercel served as a sitewide 404.
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
