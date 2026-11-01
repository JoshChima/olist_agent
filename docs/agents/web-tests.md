# Web tests

`scripts/check.sh web` runs, after the build, the two seams AIE-47's Testing Decisions name. Both need no API, database, Docker or network.

- **Vitest** (`pnpm test`, `app/web/src/app.test.tsx`): exactly three behaviours, with fetch stubbed. Counts format with locale separators and currency with two decimals; the step buttons are disabled at the dataset's first and last day; the delta strip says "rewound" after a backward clock change. Don't add per-component suites; a new behaviour worth pinning gets its own line in the spec first.
- **Playwright** (`pnpm e2e`, `app/web/e2e/pages.spec.ts`): serves `dist/` with `vite preview` and answers every `/api/*` request from `app/web/e2e/fixtures/<path>.json` (the deployed API's answer at clock 2018-02-17; `/api/explore/orders` is `explore-orders.json`). For Orders, Funnel and Explorer in light and dark it compares a full-page screenshot to `app/web/e2e/baselines/<page>-<mode>.png`; one interaction, a forward day step, asserts the delta strip's text from `delta.json`.

## Screenshot baselines are recorded on CI's platform

Concord's fonts are system stacks, so the same page renders differently on Windows, macOS and Ubuntu. The six baselines are what Chromium draws on CI's `ubuntu-24.04` runner, compared pixel-exact. A local run on any other platform **skips the six comparisons** and still runs Vitest and the interaction test, so a local pass and a CI pass mean the same thing everywhere except for looks, which only CI judges. The alternative, a tolerance wide enough to absorb cross-platform text rendering, would also absorb the restyle regressions the baselines exist to catch.

**Updating baselines** (every restyle ticket does this deliberately):

1. Delete the baselines the ticket changes from `app/web/e2e/baselines/` (or all six) and push. CI's web job fails on the missing ones and writes what it saw.
2. Download the job's `web-screenshots` artifact (`gh run download <run-id> -n web-screenshots -D <dir>`). Its `e2e/baselines/` holds the new baselines; `test-results/` holds the actual and diff images of any comparison that failed against a kept baseline.
3. Look at them. Commit the new baselines in their own commit, named for the ticket; CI is green on the next push.

A screenshot that changes without the ticket intending it is a regression: fix the page, not the baseline.
