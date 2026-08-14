import { test, expect, type ConsoleMessage, type Page } from "@playwright/test";

/**
 * Every public page must render cleanly in a real browser.
 *
 * The console assertion is the point of this file. A blank `src` on an image,
 * a hydration mismatch, a failed fetch — none of these fail a type check or a
 * unit test, and all of them are visible here.
 */

/** Noise from the dev environment, not defects in our code. */
const IGNORED = [
  /Download the React DevTools/i,
  /\[Fast Refresh\]/i,
  /webpack-hmr|turbopack/i,
  // Expected whenever Clerk runs on test keys, which is every local run.
  /Clerk has been loaded with development keys/i,
];

function collectProblems(page: Page): string[] {
  const problems: string[] = [];

  page.on("console", (message: ConsoleMessage) => {
    if (message.type() !== "error" && message.type() !== "warning") return;
    const text = message.text();
    if (IGNORED.some((pattern) => pattern.test(text))) return;
    problems.push(`${message.type()}: ${text}`);
  });

  page.on("pageerror", (error) => problems.push(`pageerror: ${error.message}`));

  return problems;
}

const PUBLIC_PAGES = [
  { path: "/", heading: /Chat With Your Apps/i },
  { path: "/auth/sign-in", heading: /Relaywise/i },
  { path: "/auth/sign-up", heading: /Relaywise/i },
];

for (const { path, heading } of PUBLIC_PAGES) {
  test(`${path} renders without console errors`, async ({ page }) => {
    const problems = collectProblems(page);

    const response = await page.goto(path, { waitUntil: "networkidle" });

    expect(response?.status(), `${path} should return 2xx`).toBeLessThan(400);
    await expect(page.locator("body")).toContainText(heading);
    expect(problems, `console output on ${path}`).toEqual([]);
  });
}

test("every image has a real src", async ({ page }) => {
  // Regression: blank logos were emitted as src="", which next/image rejects
  // at render time. Type-checked fine, unit-tested fine, broke the page.
  await page.goto("/", { waitUntil: "networkidle" });

  const sources = await page
    .locator("img")
    .evaluateAll((images) =>
      images.map((image) => (image as HTMLImageElement).getAttribute("src")),
    );

  expect(sources.length).toBeGreaterThan(0);
  for (const src of sources) {
    expect(src, "img src must not be empty or missing").toBeTruthy();
  }
});

test("app logos are served locally, not from a third party", async ({ page }) => {
  // Logos are committed under /public/logos precisely so a CDN outage cannot
  // blank the page. This stops a remote URL creeping back into the catalog.
  const external: string[] = [];

  page.on("request", (request) => {
    if (request.resourceType() !== "image") return;
    const url = new URL(request.url());
    if (url.hostname !== "localhost" && url.hostname !== "127.0.0.1") {
      external.push(request.url());
    }
  });

  await page.goto("/", { waitUntil: "networkidle" });

  expect(external, "images should be served from the app itself").toEqual([]);
});

test("pricing is gone", async ({ page }) => {
  // The product has no paid plan; a stale link would be a false claim.
  await page.goto("/", { waitUntil: "networkidle" });

  await expect(page.locator('a[href="/pricing"]')).toHaveCount(0);
  expect(await page.goto("/pricing").then((r) => r?.status())).toBe(404);
});

test("signed-out visitors are redirected away from the dashboard", async ({ page }) => {
  await page.goto("/dashboard");

  await expect(page).toHaveURL(/sign-in|auth/, { timeout: 15_000 });
});
