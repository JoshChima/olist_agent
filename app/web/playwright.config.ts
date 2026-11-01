import { defineConfig } from "@playwright/test";

// Off CI, the share of a page's pixels that may differ from its baseline. Measured on Windows 11
// against CI's baselines (docs/agents/web-tests.md): the dashboards differ by at most 0.16%, all of
// it text antialiasing, so 0.5% passes them with margin and still fails a missing tile or a moved
// panel. The Explorer, a page of 13px identifiers, differs by 4% and sets its own ratio in the spec.
const LOCAL_MAX_DIFF_PIXEL_RATIO = 0.005;

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
      // CI is the platform the baselines come from, so it compares pixel-exact.
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
    // Grayscale antialiasing and whole-pixel glyph placement on every platform. With LCD text on,
    // Windows and Linux draw different colour fringes around the same glyph, and the pixel diff
    // reaches a tenth of a text-dense page; without it only rasteriser rounding is left.
    launchOptions: { args: ["--disable-lcd-text", "--disable-font-subpixel-positioning", "--font-render-hinting=none"] },
  },
  webServer: {
    command: "vite preview --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
  },
});
