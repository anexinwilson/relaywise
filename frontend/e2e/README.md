# End-to-end tests

Covers what a type check and unit tests structurally cannot: whether a page
actually renders in a browser.

The suite exists because of a specific bug. A blank `src=""` reached
`next/image`, which rejects it at render time. TypeScript was happy, ESLint was
happy, unit tests were happy, and the page was broken.

```bash
npm run e2e                 # starts its own dev server on :3100
npm run e2e:ui              # watch mode

E2E_BASE_URL=http://localhost:3001 npx playwright test   # against a server you already have running
```

Runs on Chromium and a mobile viewport. In CI it runs after lint/types/unit,
since there is no point booting a browser for code that does not compile.

## What is asserted

| Test                                       | Guards against                                        |
| ------------------------------------------ | ----------------------------------------------------- |
| Public pages render without console errors | Hydration mismatches, bad props, failed fetches       |
| Every image has a real `src`               | The regression above                                  |
| Images are served locally                  | A remote logo URL creeping back into the catalog      |
| Pricing is gone                            | A stale link claiming a paid plan that does not exist |
| Signed-out users leave `/dashboard`        | Auth gating quietly breaking                          |

The console assertion is the valuable one. Most front-end regressions announce
themselves in the console long before anyone notices them by eye.

## Signed-in flows

Not covered yet. Clerk needs a testing token rather than a scripted login —
`@clerk/testing` provides `setupClerkTestingToken()` for exactly this. Worth
adding once the signed-in surface stops changing; scripting a real sign-in
against a live Clerk instance is fragile and rate-limited.

The natural first cases are the regressions fixed during the migration:

- history renders each message once, not duplicated per conversation
- deleting a conversation removes it
- the sidebar title does not change on the second message
- credits start at 0.00/100
