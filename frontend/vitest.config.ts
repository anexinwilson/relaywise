import { defineConfig } from "vitest/config";

/**
 * Unit tests only.
 *
 * Vitest's default glob picks up every `*.spec.ts`, which swept in the
 * Playwright suite under `e2e/` and failed with "test() was not expected to be
 * called here" — two runners fighting over the same files. The two suites are
 * separate on purpose: `npm test` is fast and needs no browser, `npm run e2e`
 * boots one.
 */
export default defineConfig({
  test: {
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules", ".next", "e2e"],
  },
});
