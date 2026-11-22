import { test, type Page } from "@playwright/test";

// Attaches a labelled screenshot to the running test; the feature page
// generator (site/build.mjs) shows them in order as the feature's playbook.
export async function shot(page: Page, label: string) {
  await test.info().attach(label, { body: await page.screenshot(), contentType: "image/png" });
}
