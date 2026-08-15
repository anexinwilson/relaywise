import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

/**
 * Route protection.
 *
 * The list below is public, not protected. Naming the protected routes instead
 * means a page added later is reachable signed out until someone remembers to
 * list it, which is how `/integrations` ended up unprotected while
 * `/dashboard`, `/settings` and `/onboarding` were covered.
 *
 * In Next.js 16 this file is `proxy.ts`. The old `middleware.ts` name still
 * loads but the two cannot coexist: Next refuses to serve any route at all,
 * returning 404 for every request including the landing page.
 */
const isPublicRoute = createRouteMatcher(["/", "/auth/sign-in(.*)", "/auth/sign-up(.*)"]);

/**
 * API routes authenticate themselves and must not be redirected.
 *
 * `auth.protect()` answers a signed-out request with a 307 to the sign-in
 * page. That is right for a page and wrong for `fetch`, which follows the
 * redirect, receives HTML and fails on `JSON.parse` with "Unexpected token
 * '<'". Each route under /api already calls `auth()` and returns a 401, which
 * is what a caller expecting JSON can actually handle.
 */
const isApiRoute = createRouteMatcher(["/api(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isApiRoute(req)) return;
  if (!isPublicRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Everything except Next internals and static files.
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
