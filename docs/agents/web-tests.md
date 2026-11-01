# Web tests

`scripts/check.sh web` runs, after the build, the two seams AIE-47's Testing Decisions name. Both need no API, database, Docker or network.

- **Vitest** (`pnpm test`, `app/web/src/app.test.tsx`): exactly three behaviours, with fetch stubbed. Counts format with locale separators and currency with two decimals; the step buttons are disabled at the dataset's first and last day; the delta strip says "rewound" after a rewind. Don't add per-component suites; a new behaviour worth pinning gets its own line in the spec first.
- **Playwright** (`pnpm e2e`, `app/web/e2e/pages.spec.ts`): serves `dist/` with `vite preview` and answers every `/api/*` request from `app/web/e2e/fixtures/<path>.json` (the deployed API's answer at clock 2018-02-17; `/api/explore/orders` is `explore-orders.json`). For Orders, Funnel and Explorer in light and dark it compares a full-page screenshot to `app/web/e2e/baselines/<page>-<mode>.png`; one interaction, a forward day step, asserts the delta strip's text from `delta.json`.

## Screenshot baselines are recorded on CI and compared everywhere

The app ships one typeface, Inter and JetBrains Mono from their Fontsource packages (ADR-0011 as amended), so Chromium lays out the same glyphs on Windows, macOS and Ubuntu. The six baselines are what CI's `ubuntu-24.04` runner draws; the spec waits for `document.fonts.ready` before each shot so the shipped face is on screen, not its fallback. CI compares pixel-exact (`maxDiffPixelRatio: 0`). A local run on any platform compares against the same files with a small tolerance, because the two rasterisers (DirectWrite on Windows, FreeType on Linux) still shade the edges of the same glyph differently.

**What the test browser does about it.** `playwright.config.ts` launches Chromium with `--disable-lcd-text`, `--disable-font-subpixel-positioning` and `--font-render-hinting=none` on every platform: grayscale antialiasing and whole-pixel glyph placement. With LCD text on, the colour fringes differed on every glyph and the Windows-vs-CI diff was 10% of the Explorer's pixels; with it off, only the stem darkness of small text differs. These flags affect the test browser only, never a visitor.

**The local tolerance, and how it was measured** (AIE-58, 2026-11-01, Windows 11 against CI run 41345301232's baselines, Playwright's default colour threshold of 0.2):

| page | light | dark | local tolerance |
|---|---|---|---|
| Orders | 3,483 px (0.16%) | 1,031 px (0.05%) | 0.5% (`LOCAL_MAX_DIFF_PIXEL_RATIO` in the config) |
| Funnel | 1,783 px (0.14%) | 520 px (0.04%) | 0.5% |
| Explorer | 82,891 px (3.87%) | 86,310 px (4.03%) | 5% (`EXPLORER_LOCAL_MAX_DIFF_PIXEL_RATIO` in the spec) |

The Explorer is a page of 13px identifiers, so the small-text shading difference covers 4% of it; one ratio can't both pass the Explorer and still catch a missing tile on the Funnel, so the Explorer carries its own. Raising the colour threshold or the ssim comparator did not close that gap. What the tolerances catch, measured the same day: swapping Concord's system stack back in for headings alone fails all four dashboard shots (9,907 to 20,726 pixels each, past 0.5%), and the AIE-49 check that puts the dark shot where the light baseline belongs fails by 1,960,062 pixels. What they miss: that same heading fallback passes the two Explorer shots locally, because one heading is under 5% of that page; so on the Explorer a change confined to a few cells or the heading is CI's to catch. CI is pixel-exact, so nothing passes into main unseen; the local run is the fast check, CI the truth. If local comparisons start failing by small margins after a Chromium or OS update, re-measure this table the same way (`CI=1 pnpm e2e` on the platform prints each page's diff) rather than widening a number. Before AIE-58 the comparisons skipped off Linux entirely, because Concord's system font stacks drew different letterforms per platform.

**Updating baselines** (every restyle ticket does this deliberately):

1. Delete the baselines the ticket changes from `app/web/e2e/baselines/` (or all six) and push. CI's web job fails on the missing ones and writes what it saw.
2. Download the job's `web-screenshots` artifact (`gh run download <run-id> -n web-screenshots -D <dir>`). Its `e2e/baselines/` holds the new baselines; `test-results/` holds the actual and diff images of any comparison that failed against a kept baseline.
3. Look at them. Commit the new baselines in their own commit, named for the ticket; CI is green on the next push.

A screenshot that changes without the ticket intending it is a regression: fix the page, not the baseline. `pnpm e2e --update-snapshots` locally is a preview of what changed, never the committed truth: baselines come from CI.
