import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const CLOCK = "2018-02-17";
const PAGES = ["/orders", "/funnel", "/explore"];

// e2e/fixtures/<name>.json is the deployed API's answer at CLOCK, with /api/ dropped and / as -.
const fixture = (name: string) => readFileSync(`${import.meta.dirname}/fixtures/${name}.json`, "utf8");

test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", (route) => {
    const name = new URL(route.request().url()).pathname.slice("/api/".length).replaceAll("/", "-");
    try {
      return route.fulfill({ contentType: "application/json", body: fixture(name) });
    } catch {
      return route.fulfill({ status: 404, body: `no fixture e2e/fixtures/${name}.json` });
    }
  });
});

async function open(page: Page, path: string) {
  await page.clock.install(); // fake timers, so the Recharts entry animation is run to its end below
  await page.goto(`${path}?clock=${CLOCK}`);
  await expect(page.getByText("Loading…")).toHaveCount(0);
  await page.clock.runFor(2000);
  await page.evaluate(() => document.fonts.ready); // the self-hosted typeface is drawn, not its fallback
  // The content column scrolls inside the shell (AIE-51), so a full-page shot is only the viewport.
  // Grow the viewport to the column's full height first, so the whole page is in the baseline.
  const height = await page.evaluate(() => {
    const column = document.querySelector("main")!.parentElement!;
    return Math.ceil(column.getBoundingClientRect().top + column.scrollHeight);
  });
  await page.setViewportSize({ width: 1280, height: Math.max(1000, height) });
}

// The Explorer is a table of 13px identifiers, and the two rasterisers shade small text differently:
// measured at 4% of its pixels on Windows against CI's baseline (docs/agents/web-tests.md). A restyle
// of the table moves every row and goes far past this; a one-cell change is for CI, which compares
// pixel-exact, to catch.
const EXPLORER_LOCAL_MAX_DIFF_PIXEL_RATIO = 0.05;

for (const path of PAGES) {
  for (const scheme of ["light", "dark"] as const) {
    test(`${path} at ${CLOCK} in ${scheme} mode matches its baseline`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: scheme });
      await open(page, path);
      const tolerance = path === "/explore" && !process.env.CI ? { maxDiffPixelRatio: EXPLORER_LOCAL_MAX_DIFF_PIXEL_RATIO } : {};
      await expect(page).toHaveScreenshot(`${path.slice(1)}-${scheme}.png`, { fullPage: true, ...tolerance });
    });
  }
}

// The delta strip's wording for each count the API returns, in display order (GLOSSARY.md "Delta event").
const DELTA_LABELS: Record<string, string> = {
  new_orders: "new orders",
  approved: "approved",
  shipped: "shipped",
  delivered: "delivered",
  canceled_or_unavailable: "canceled or unavailable",
  new_reviews: "new reviews",
  new_mqls: "new MQLs",
  deals_closed: "deals closed",
  new_active_sellers: "new active sellers",
};

test("a forward step shows the delta event from the fixture", async ({ page }) => {
  await open(page, "/orders");
  await page.getByRole("button", { name: "+1D" }).click();
  const delta = JSON.parse(fixture("delta"));
  const summary = Object.entries(DELTA_LABELS)
    .map(([key, label]) => `${delta.counts[key].toLocaleString("en-US")} ${label}`)
    .join(", ");
  await expect(page.getByRole("status")).toHaveText(`${delta.from} → ${delta.to}: ${summary}`);
});
