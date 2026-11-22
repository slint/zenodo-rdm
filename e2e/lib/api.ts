import { readFileSync } from "node:fs";
import { request, expect, type APIRequestContext } from "@playwright/test";
import type { Role } from "./users";

const baseURL = process.env.ZENODO_URL ?? "https://127.0.0.1:5000";

// Prefer RDM JSON: plain application/json on /api/records is Zenodo's legacy
// format, which the RDM endpoints can't take back (a PUT with it answers 500).
// File endpoints only serve application/json.
export const RDM_JSON = "application/vnd.inveniordm.v1+json, application/json;q=0.9";

// An API client authenticated with the token auth.setup.ts created for role,
// or anonymous without a role.
export async function api(role?: Role, accept = RDM_JSON): Promise<APIRequestContext> {
  const headers: Record<string, string> = { Accept: accept };
  if (role) headers.Authorization = `Bearer ${readFileSync(`.auth/${role}.token`, "utf8")}`;
  return request.newContext({ baseURL, ignoreHTTPSErrors: true, extraHTTPHeaders: headers });
}

export function draftPayload(title: string) {
  return {
    access: { record: "public", files: "public" },
    files: { enabled: true },
    metadata: {
      title,
      // Publishing with a Zenodo DOI fails with 400 without a publisher.
      publisher: "Zenodo",
      resource_type: { id: "dataset" },
      publication_date: new Date().toISOString().slice(0, 10),
      creators: [
        { person_or_org: { type: "personal", given_name: "Ada", family_name: "Lovelace" } },
      ],
      description: "Created by the e2e checks.",
    },
  };
}

// Creates a draft with one text file and publishes it; returns the record.
export async function publishRecord(client: APIRequestContext, title: string) {
  const draft = await json(client.post("/api/records", { data: draftPayload(title) }), 201);
  const id = draft.id;
  await json(client.post(`/api/records/${id}/draft/files`, { data: [{ key: "hello.txt" }] }), 201);
  const content = await client.put(`/api/records/${id}/draft/files/hello.txt/content`, {
    headers: { "Content-Type": "application/octet-stream" },
    data: Buffer.from("hello from e2e\n"),
  });
  expect(content.status()).toBe(200);
  await json(client.post(`/api/records/${id}/draft/files/hello.txt/commit`), 200);
  return json(client.post(`/api/records/${id}/draft/actions/publish`), 202);
}

// Awaits a response, checks its status and returns its JSON body.
export async function json(res: ReturnType<APIRequestContext["get"]>, status = 200) {
  const r = await res;
  const body = await r.text();
  expect(r.status(), body.slice(0, 500)).toBe(status);
  return JSON.parse(body);
}
