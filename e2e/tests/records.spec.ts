import { test, expect, type APIRequestContext } from "@playwright/test";
import { api, json, publishRecord } from "../lib/api";

// Records area: what anyone can do with a published record, plus search and
// OAI-PMH over it. One record is published by a regular user first.
const title = `E2E record ${Date.now()}`;
let record: any;
let anon: APIRequestContext;

test.beforeAll(async () => {
  record = await publishRecord(await api("user"), title);
  anon = await api();
});

test("[records.landing] landing page shows metadata, files and exports", async ({ page }) => {
  await page.goto(`/records/${record.id}`);
  await expect(page.locator("h1#record-title")).toHaveText(title);
  await expect(page.getByText("Lovelace, Ada").first()).toBeVisible();
  await expect(page.locator("#files-list-accordion-trigger, .files").first()).toBeVisible();
  await expect(page.getByText("hello.txt").first()).toBeVisible();
});

test("[records.files.download] anyone downloads a public file", async () => {
  const res = await anon.get(`/records/${record.id}/files/hello.txt?download=1`);
  expect(res.status()).toBe(200);
  expect(await res.text()).toBe("hello from e2e\n");
  const apiRes = await anon.get(`/api/records/${record.id}/files/hello.txt/content`);
  expect(await apiRes.text()).toBe("hello from e2e\n");
});

test("[records.api.legacy-json] plain JSON is the legacy Zenodo format", async () => {
  const legacy = await (await api(undefined, "application/json")).get(`/api/records/${record.id}`);
  const body = await legacy.json();
  expect(body.doi).toBe(record.pids.doi.identifier);
  expect(body.metadata.title).toBe(title);
});

test("[records.api.read] REST API returns the record and its versions", async () => {
  const r = await json(anon.get(`/api/records/${record.id}`));
  expect(r.metadata.title).toBe(title);
  expect(r.status).toBe("published");
  const versions = await json(anon.get(`/api/records/${record.id}/versions`));
  expect(versions.hits.total).toBe(1);
});

// Formats in APP_RDM_RECORD_EXPORTERS (invenio_app_rdm config plus invenio.cfg).
const exportFormats: [string, RegExp][] = [
  ["json", /"title"/],
  ["json-ld", /schema\.org/],
  ["csl", /"title"/],
  ["datacite-json", /"titles"/],
  ["datacite-xml", /<resource/],
  ["dublincore", /<oai_dc:dc|<dc:title/],
  ["marcxml", /<record/],
  ["bibtex", /@\w+\{/],
  ["dcat-ap", /dcat/],
  ["codemeta", /codemeta/],
  ["cff", /cff-version/],
  ["geojson", /\{/],
  ["datapackage", /"resources"/],
];
for (const [fmt, pattern] of exportFormats) {
  test(`[records.export] export as ${fmt}`, async () => {
    const res = await anon.get(`/records/${record.id}/export/${fmt}`);
    expect(res.status()).toBe(200);
    expect(await res.text()).toMatch(pattern);
  });
}

test("[records.citation] citation styles render through the API", async () => {
  const res = await anon.get(`/api/records/${record.id}?style=apa`, {
    headers: { Accept: "text/x-bibliography" },
  });
  expect(res.status()).toBe(200);
  expect(await res.text()).toContain("Lovelace, A.");
});

test("[search.api] the new record is searchable", async () => {
  await expect
    .poll(async () => (await json(anon.get(`/api/records?q="${title}"`))).hits.total, {
      timeout: 30_000,
    })
    .toBe(1);
  const res = await json(anon.get(`/api/records?q="${title}"`));
  expect(res.hits.hits[0].id).toBe(record.id);
  expect(res.aggregations).toHaveProperty("resource_type");
});

test("[search.ui] search page lists the record", async ({ page }) => {
  await page.goto(`/search?q="${encodeURIComponent(title)}"`);
  await expect(page.getByRole("link", { name: title })).toBeVisible();
});

test("[search.sort-filter] search API sorts and filters", async () => {
  const newest = await json(anon.get("/api/records?sort=newest&size=5"));
  expect(newest.hits.hits.length).toBeGreaterThan(0);
  const datasets = await json(anon.get("/api/records?resource_type=dataset&size=25"));
  for (const hit of datasets.hits.hits) expect(hit.metadata.resource_type.id).toMatch(/^dataset/);
});

test("[oai.identify] OAI-PMH Identify and ListMetadataFormats", async () => {
  const identify = await anon.get("/oai2d?verb=Identify");
  expect(identify.status()).toBe(200);
  expect(await identify.text()).toContain("<Identify>");
  const formats = await (await anon.get("/oai2d?verb=ListMetadataFormats")).text();
  for (const prefix of ["oai_dc", "datacite", "oai_datacite"]) expect(formats).toContain(prefix);
});

test("[oai.getrecord] OAI-PMH serves the new record", async () => {
  const id = record.pids.oai.identifier;
  expect(id).toBe(`oai:zenodo.org:${record.id}`);
  await expect
    .poll(async () => (await anon.get(`/oai2d?verb=GetRecord&metadataPrefix=oai_dc&identifier=${id}`)).text(), {
      timeout: 30_000,
    })
    .toContain(title);
});
