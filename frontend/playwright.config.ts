import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests for the public surface.
 *
 * These cover what unit tests structurally cannot: whether a page actually
 * renders in a browser without errors. The bug that prompted this suite — an
 * empty `src` passed to next/image — type-checked, linted, and unit-tested
 * clean, and only failed once a browser tried to render it.
 *
 * Signed-in flows are not covered yet; they need Clerk testing tokens
 * (@clerk/testing). See e2e/README.md.
 */

// Same port as `npm run dev` on purpose. Two Next servers cannot run from one
// checkout — they share `.next`, and Turbopack holds a lock on it — so a
// second server on another port fails to start whenever you already have the
// app running. Matching the port lets `reuseExistingServer` attach to it
// instead, while CI (where nothing is running) still gets a fresh one.
const PORT = Number(process.env.E2E_PORT ?? 3001);
const baseURL = process.env.E2E_BASE_URL ?? `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  // Fail the build if someone commits a focused test.
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],

  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    // Catches layout breakage the desktop viewport hides.
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],

  // Reuse a running dev server locally; start a fresh one in CI.
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: `npx next dev -p ${PORT}`,
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
        stdout: "ignore",
      },
});
