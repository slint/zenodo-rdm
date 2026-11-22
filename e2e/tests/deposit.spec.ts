import { test, expect } from "@playwright/test";
import { api, json, draftPayload, publishRecord } from "../lib/api";

// Deposit area: creating, editing, versioning and publishing records, through
// the UI deposit form, the RDM REST API and the legacy Zenodo deposit API.

test.describe("UI", () => {
  test("[deposit.ui.login-required] anonymous users are sent to log in", async ({ page }) => {
    await page.goto("/uploads/new");
    await expect(page).toHaveURL(/\/login\/\?next=/);
  });

  test.describe("as user", () => {
    test.use({ storageState: ".auth/user.json" });

    test("[deposit.ui.publish] fill the form, upload a file and publish", async ({ page }) => {
      const title = `E2E UI upload ${Date.now()}`;
      await page.goto("/uploads/new");
      await page.locator('input[type="file"]').first().setInputFiles({
        name: "ui.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("uploaded from the form\n"),
      });
      await expect(page.getByText("ui.txt").first()).toBeVisible();

      await page.getByRole("combobox", { name: "Resource type" }).click();
      await page.getByRole("option").getByText("Dataset", { exact: true }).click();
      await page.locator("#metadata\\.title").fill(title);
      // Empty by default, and publishing fails without it.
      await page.locator('input[name="metadata.publisher"]').fill("Zenodo");
      // Leaving the DOI question unanswered fails with "Missing DOI for required field."
      await page.getByText("No, I need one").first().click();

      await page.getByRole("button", { name: "Add author", exact: true }).click();
      const modal = page.locator(".ui.modal.visible");
      await modal.locator('input[name="person_or_org.family_name"]').fill("Hopper");
      await modal.locator('input[name="person_or_org.given_name"]').fill("Grace");
      await modal.getByRole("button", { name: /^Save$/ }).click();
      await expect(page.getByText("Hopper, Grace")).toBeVisible();

      await page.getByRole("button", { name: "Publish", exact: true }).first().click();
      await page.locator(".ui.modal.visible").getByRole("button", { name: "Publish" }).click();
      await expect(page).toHaveURL(/\/records\/\d+/, { timeout: 30_000 });
      await expect(page.locator("h1#record-title")).toHaveText(title);
    });

    test("[deposit.ui.dashboard] my uploads lists the user's records", async ({ page }) => {
      const title = `E2E dashboard ${Date.now()}`;
      await json((await api("user")).post("/api/records", { data: draftPayload(title) }), 201);
      await page.goto("/me/uploads");
      await expect(page.getByText(title).first()).toBeVisible({ timeout: 30_000 });
    });
  });
});

test.describe("REST API", () => {
  test("[deposit.api.publish] create, upload, publish", async () => {
    const record = await publishRecord(await api("user"), `E2E API ${Date.now()}`);
    expect(record.status).toBe("published");
    const files = await json((await api()).get(`/api/records/${record.id}/files`));
    expect(files.entries.map((f: any) => [f.key, f.size])).toEqual([["hello.txt", 15]]);
  });

  test("[deposit.api.validation] publishing without required fields fails", async () => {
    const client = await api("user");
    const draft = await json(client.post("/api/records", { data: { metadata: {}, files: { enabled: false } } }), 201);
    const res = await client.post(`/api/records/${draft.id}/draft/actions/publish`);
    expect(res.status()).toBe(400);
    const fields = (await res.json()).errors.map((e: any) => e.field);
    expect(fields).toEqual(expect.arrayContaining(["metadata.title", "metadata.creators"]));
  });

  test("[deposit.api.edit] edit a published record", async () => {
    const client = await api("user");
    const record = await publishRecord(client, `E2E edit ${Date.now()}`);
    const draft = await json(client.post(`/api/records/${record.id}/draft`), 201);
    draft.metadata.title = `${draft.metadata.title} (edited)`;
    await json(client.put(`/api/records/${record.id}/draft`, { data: draft }));
    const published = await json(client.post(`/api/records/${record.id}/draft/actions/publish`), 202);
    expect(published.metadata.title).toMatch(/\(edited\)$/);
    expect(published.revision_id).toBeGreaterThan(record.revision_id);
  });

  test("[deposit.api.new-version] publish a new version", async () => {
    const client = await api("user");
    const v1 = await publishRecord(client, `E2E versions ${Date.now()}`);
    const v2 = await json(client.post(`/api/records/${v1.id}/versions`), 201);
    await json(client.post(`/api/records/${v2.id}/draft/actions/files-import`), 201);
    v2.metadata.publication_date = v1.metadata.publication_date;
    await json(client.put(`/api/records/${v2.id}/draft`, { data: v2 }));
    const published = await json(client.post(`/api/records/${v2.id}/draft/actions/publish`), 202);
    expect(published.versions.index).toBe(2);
    expect(published.parent.id).toBe(v1.parent.id);
  });

  test("[deposit.api.delete-draft] discard a draft", async () => {
    const client = await api("user");
    const draft = await json(client.post("/api/records", { data: draftPayload("E2E discard") }), 201);
    expect((await client.delete(`/api/records/${draft.id}/draft`)).status()).toBe(204);
    expect((await client.get(`/api/records/${draft.id}/draft`)).status()).toBe(404);
  });

  test("[deposit.permissions] drafts are private to their owner", async () => {
    const draft = await json((await api("user")).post("/api/records", { data: draftPayload("E2E private") }), 201);
    // Invenio hides drafts from anonymous users as not found.
    expect((await (await api()).get(`/api/records/${draft.id}/draft`)).status()).toBe(404);
    expect((await (await api("user")).get(`/api/records/${draft.id}/draft`)).status()).toBe(200);
    expect((await (await api("admin")).get(`/api/records/${draft.id}/draft`)).status()).toBe(200);
  });

  test("[deposit.restricted-files] restricted files stay hidden from anonymous users", async () => {
    const client = await api("user");
    const payload = draftPayload(`E2E restricted ${Date.now()}`);
    payload.access.files = "restricted";
    const draft = await json(client.post("/api/records", { data: payload }), 201);
    await json(client.post(`/api/records/${draft.id}/draft/files`, { data: [{ key: "secret.txt" }] }), 201);
    await client.put(`/api/records/${draft.id}/draft/files/secret.txt/content`, {
      headers: { "Content-Type": "application/octet-stream" },
      data: Buffer.from("secret"),
    });
    await json(client.post(`/api/records/${draft.id}/draft/files/secret.txt/commit`));
    await json(client.post(`/api/records/${draft.id}/draft/actions/publish`), 202);
    const anon = await api();
    expect((await anon.get(`/api/records/${draft.id}`)).status()).toBe(200);
    expect((await anon.get(`/api/records/${draft.id}/files/secret.txt/content`)).status()).toBe(403);
    expect((await client.get(`/api/records/${draft.id}/files/secret.txt/content`)).status()).toBe(200);
  });
});

test.describe("legacy deposit API", () => {
  test("[deposit.legacy] create, upload and publish through /api/deposit/depositions", async () => {
    const client = await api("user", "application/json");
    const dep = await json(client.post("/api/deposit/depositions", { data: {} }), 201);
    const bucket = dep.links.bucket as string;
    const put = await client.put(`${bucket}/legacy.txt`, {
      headers: { "Content-Type": "application/octet-stream" },
      data: Buffer.from("legacy upload\n"),
    });
    expect([200, 201]).toContain(put.status());
    await json(
      client.put(`/api/deposit/depositions/${dep.id}`, {
        data: {
          metadata: {
            title: `E2E legacy ${Date.now()}`,
            upload_type: "dataset",
            description: "Legacy API upload",
            creators: [{ name: "Turing, Alan" }],
          },
        },
      }),
    );
    const published = await json(client.post(`/api/deposit/depositions/${dep.id}/actions/publish`), 202);
    expect(published.submitted).toBe(true);
    expect(published.state).toBe("done");
  });
});
