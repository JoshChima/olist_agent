import { defineConfig } from "@playwright/test";

// The built app in a real browser (AIE-47 Testing Decisions, seam 1): `pnpm build` first, this
// serves dist/. Every /api/* call is answered from e2e/fixtures, so no API, database or network
// is needed. Screenshot baselines live in e2e/baselines and are recorded on CI's platform
// (docs/agents/web-tests.md).
export default defineConfig({
  testDir: "e2e",
  snapshotPathTemplate: "{testDir}/baselines/{arg}{ext}",
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
