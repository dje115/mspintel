import { test, expect, type Route } from "@playwright/test";
import fs from "fs";
import path from "path";

import { installReviewAiMocks } from "./helpers/reviewAiRouteMock";

type Meta = { tenantId: string; customerId: string | null };

function loadMeta(): Meta {
  const p = path.join(process.cwd(), "e2e", ".cache", "meta.json");
  const raw = fs.readFileSync(p, "utf-8");
  return JSON.parse(raw) as Meta;
}

const useMock = process.env.E2E_MOCK_AI !== "0";

test.describe("MSPIntel demo journey — Review/QBR smoke", () => {
  test("dashboard loads with tenant session", async ({ page }) => {
    await page.goto("/app");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  });

  test("tenant login via browser reaches dashboard", async ({ browser, baseURL }) => {
    const origin = baseURL ?? "http://127.0.0.1:5173";
    const ctx = await browser.newContext({ baseURL: origin });
    const page = await ctx.newPage();
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /Sign in to your MSP/ })).toBeVisible();
    await page.getByLabel("Work email").fill(process.env.E2E_TENANT_EMAIL || "tenant-admin@demo-msp.example.com");
    await page.getByLabel("Password").fill(process.env.E2E_TENANT_PASSWORD || "ChangeMe123!");
    await page.getByRole("button", { name: "Continue to workspace" }).click();
    await expect(page).toHaveURL(/\/app(\/|$)/);
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible({ timeout: 45_000 });
    await ctx.close();
  });

  test("integrations mappings and customers list", async ({ page }) => {
    await page.goto("/app/integrations/mappings");
    await expect(page.getByRole("heading", { name: "Integration mappings review" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Needs review" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Needs attention" }).first()).toBeVisible();

    await page.goto("/app/customers");
    await expect(page.getByRole("heading", { name: /Accounts & customers/ })).toBeVisible();

    const meta = loadMeta();
    if (!meta.customerId) {
      await expect(page.getByText(/No synced customer data yet/)).toBeVisible();
      return;
    }
    const rowLink = page.locator("table.tenant-table tbody a").first();
    await expect(rowLink).toBeVisible();
    await rowLink.click();
    await expect(page).toHaveURL(/\/app\/customers\/[0-9a-f-]{8,}/i);
  });

  test("Review workspace tabs render for selected customer", async ({ page }) => {
    const meta = loadMeta();
    test.skip(!meta.customerId, "No customer rows — run demo seed / M365 import (docs/DEMO_SEED_DATA.md).");

    await page.goto(`/app/reviews?customer_id=${encodeURIComponent(meta.customerId!)}&tab=overview`);
    await expect(page.getByRole("heading", { name: /Review & QBR workspace/ })).toBeVisible();

    for (const label of [
      "Prep overview",
      "AI agenda",
      "Account manager",
      "Customer email",
      "Customer report",
      "AI history",
      "Data confidence"
    ]) {
      await expect(page.getByRole("button", { name: label })).toBeVisible();
    }
  });

  test("mocked AI: agenda, email, report; copy controls; persistence; history", async ({ page }) => {
    test.skip(!useMock, "Skipped when E2E_MOCK_AI=0 (live provider path).");
    const meta = loadMeta();
    test.skip(!meta.customerId, "No customer rows — run demo seed / M365 import (docs/DEMO_SEED_DATA.md).");

    const unmock = installReviewAiMocks(page, { tenantId: meta.tenantId, customerId: meta.customerId! });
    try {
      await page.goto(`/app/reviews?customer_id=${encodeURIComponent(meta.customerId!)}&tab=agenda`);
      await page.getByRole("button", { name: "Generate / refresh agenda" }).click();
      await expect(page.getByRole("heading", { name: "E2E agenda" })).toBeVisible();

      await page.getByRole("button", { name: "Customer email" }).click();
      await page.getByRole("button", { name: "Generate / refresh" }).click();
      const subject = page.getByRole("textbox", { name: "Email subject" });
      await expect(subject).toHaveValue(/Quarterly review/);
      const body = page.getByRole("textbox", { name: "Email body" });
      await expect(body).toContainText("schedule");
      await expect(page.getByRole("button", { name: "Copy subject" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Copy body" })).toBeVisible();
      await expect(page.getByRole("button", { name: "Copy full" })).toBeVisible();
      await expect(body).not.toContainText("[Customer Name]");
      await expect(body).not.toContainText("{{");
      await expect(body).not.toContainText("```");
      await expect(body).not.toContainText("this is a json");

      await page.getByRole("button", { name: "Customer report" }).click();
      await page.getByRole("button", { name: "Generate / refresh report" }).click();
      await expect(page.locator("#review-customer-report-root h1")).toContainText("Acme");
      await expect(page.getByRole("button", { name: "Print customer report" })).toBeVisible();

      await page.reload();
      await page.goto(`/app/reviews?customer_id=${encodeURIComponent(meta.customerId!)}&tab=email`);
      await expect(subject).toHaveValue(/Quarterly review/);

      await page.getByRole("button", { name: "AI history" }).click();
      await expect(page.locator(".tenant-review-history-item").first()).toBeVisible();
      await expect(page.locator(".tenant-review-history-list")).toContainText("customer_email_draft");
      await expect(page.locator(".tenant-review-history-list")).toContainText("review_agenda");
      await expect(page.locator(".tenant-review-history-list")).toContainText("customer_report");
    } finally {
      unmock();
    }
  });

  test("agenda POST failure shows outcome banner (no UI crash)", async ({ page }) => {
    const meta = loadMeta();
    test.skip(!meta.customerId, "No customer rows — run demo seed / M365 import (docs/DEMO_SEED_DATA.md).");

    const failHandler = async (route: Route) => {
      const req = route.request();
      const url = req.url();
      if (req.method() === "POST" && url.includes("/ai/agenda")) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({
            detail:
              "AI provider unreachable — open AI engines (AI settings) and confirm a default provider and reachable model."
          })
        });
        return;
      }
      await route.continue();
    };
    await page.route("**/api/v1/reviews/**", failHandler);
    try {
      await page.goto(`/app/reviews?customer_id=${encodeURIComponent(meta.customerId!)}&tab=agenda`);
      await page.getByRole("button", { name: "Generate / refresh agenda" }).click();
      const banner = page.locator(".tenant-review-ai-outcome");
      await expect(banner).toBeVisible();
      await expect(banner).toContainText(/AI run did not complete successfully/i);
      await expect(banner).toContainText(/AI settings|AI engines|provider/i);
      await expect(page.getByRole("heading", { name: /Review & QBR workspace/ })).toBeVisible();
    } finally {
      await page.unroute("**/api/v1/reviews/**", failHandler);
    }
  });
});
