import { defineConfig } from "@playwright/test";

const LOCAL_MAX_DIFF_PIXEL_RATIO = 0.01; // placeholder until measured (AIE-58)

// The built app in a real browser (AIE-47 Testing Decisions, seam 1): `pnpm build` first, this
// serves dist/. Every /api/* call is answered from e2e/fixtures, so no API, database or network
// is needed. Screenshot baselines live in e2e/baselines and are recorded on CI's platform; the
// shipped typeface makes every platform draw the same glyphs, so they compare everywhere
// (docs/agents/web-tests.md).
export default defineConfig({
  testDir: "e2e",
  snapshotPathTemplate: "{testDir}/baselines/{arg}{ext}",
  expect: {
    toHaveScreenshot: {
      // CI is the platform the baselines come from, so it compares pixel-exact. Elsewhere only
      // antialiasing and hinting differ: the measured Windows-vs-CI diff is in web-tests.md, and
      // this ratio sits just above it, far below what a moved panel or a changed colour produces.
      maxDiffPixelRatio: process.env.CI ? 0 : LOCAL_MAX_DIFF_PIXEL_RATIO,
    },
  },
  forbidOnly: !!process.env.CI,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    viewport: { width: 1280, height: 1000 },
    locale: "en-US", // number formatting in the screenshots
    timezoneId: "UTC",
  },
  webServer: {
    command: "vite preview --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
  },
});
