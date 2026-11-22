import { test as setup, expect } from "@playwright/test";
import { writeFileSync, mkdirSync } from "node:fs";
import { users } from "../lib/users";

// Logs each fixture user in through the UI, saves the session for UI checks
// and creates a personal access token for API checks.
mkdirSync(".auth", { recursive: true });

// A fresh mini image answers /ping while the worker still loads fixture
// vocabularies (several minutes), so wait until those the checks use exist.
setup("[site.ready] fixture vocabularies are loaded", async ({ request }) => {
  setup.setTimeout(30 * 60_000);
  // Reads hit the database, listings the search index; the deposit form needs both.
  const poll = (fn: () => Promise<unknown>) =>
    expect.poll(fn, { timeout: 30 * 60_000, intervals: [10_000] });
  for (const path of ["resourcetypes/dataset", "licenses/cc-by-4.0"]) {
    await poll(async () => (await request.get(`/api/vocabularies/${path}`)).status()).toBe(200);
  }
  await poll(async () => (await (await request.get("/api/vocabularies/resourcetypes")).json()).hits.total)
    .toBeGreaterThan(0);
});

for (const [role, user] of Object.entries(users)) {
  setup(`[accounts.login][accounts.tokens] log in and create a token as ${role}`, async ({ page }) => {
    await page.goto("/login/");
    await page.fill('input[name="email"]', user.email);
    await page.fill('input[name="password"]', user.password);
    await page.click('form[name="login_user_form"] button[type="submit"]');
    await expect(page).not.toHaveURL(/\/login/);

    await page.goto("/account/settings/applications/tokens/new/");
    await page.fill('input[name="name"]', `e2e-${Date.now()}`);
    for (const box of await page.locator('input[name="scopes"]').all()) await box.check();
    await page.click('form button[type="submit"].primary');
    const token = (await page.locator("code.word-break-all").innerText()).trim();
    expect(token).toMatch(/^\w{20,}$/);

    await page.context().storageState({ path: `.auth/${role}.json` });
    writeFileSync(`.auth/${role}.token`, token);
  });
}
