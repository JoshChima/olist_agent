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
}

for (const path of PAGES) {
  for (const scheme of ["light", "dark"] as const) {
    test(`${path} at ${CLOCK} in ${scheme} mode matches its baseline`, async ({ page }) => {
      test.skip(process.platform !== "linux", "baselines are recorded on linux, CI's platform (docs/agents/web-tests.md)");
      await page.emulateMedia({ colorScheme: scheme });
      await open(page, path);
      await expect(page).toHaveScreenshot(`${path.slice(1)}-${scheme}.png`, { fullPage: true });
    });
  }
}

test("a forward step shows the delta event from the fixture", async ({ page }) => {
  await open(page, "/orders");
  await page.getByRole("button", { name: "+1D" }).click();
  const { counts } = JSON.parse(fixture("delta"));
  await expect(page.getByRole("status")).toHaveText(
    new RegExp(`^${CLOCK} → 2018-02-18: ${counts.new_orders} new orders, ${counts.approved} approved, `),
  );
});
