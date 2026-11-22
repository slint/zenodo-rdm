// Builds the feature catalog site (site/dist/index.html) from the catalog
// Markdown, the latest Playwright results and the docs map:
//
//   node site/build.mjs   # from e2e/, after `npx playwright test`
//
// Inputs: catalog/catalog.md (export of the catalog document),
// results/results.json, docs/map.json and docs/pages.json (docs/crawl.py).
import { readFileSync, writeFileSync, mkdirSync, copyFileSync, existsSync, rmSync } from "node:fs";

const HELP = "https://help.zenodo.org";
const DEV = "https://developers.zenodo.org/";
const out = "site/dist";
rmSync(out, { recursive: true, force: true });
mkdirSync(`${out}/shots`, { recursive: true });

// Catalog: one section per area, one table row per feature. Tables differ per
// section, so cells are read by header name.
function parseCatalog(md) {
  const features = [];
  let area = null, header = null;
  for (const line of md.split("\n")) {
    if (line.startsWith("## ")) { area = line.slice(3).trim(); header = null; continue; }
    if (!line.startsWith("|")) { header = null; continue; }
    const cells = line.slice(1, -1).split(/(?<!\\)\|/).map((c) => c.trim());
    if (!header) { header = cells.map((c) => c.toLowerCase()); continue; }
    if (/^-+$/.test(cells[0])) continue;
    const ids = [...cells[0].matchAll(/`([\w.-]+)`/g)].map((m) => m[1]);
    if (!ids.length || !/[a-z]\.[a-z]/.test(ids[0])) continue;
    const col = (re) => cells[header.findIndex((h) => re.test(h))] ?? "";
    features.push({
      id: ids[0], aliases: ids.slice(1), area,
      what: col(/feature|task|commands|rule/), entry: col(/entry|source/) || (/task/.test(header[1]) ? cells[1] : ""),
      who: col(/^who/), check: col(/how to check/), catalogStatus: col(/status/), doesWhat: col(/what it does/),
    });
  }
  return features;
}

// Playwright JSON: tests per catalog ID (from the [id] tags in titles), their
// final result and screenshot attachments in order.
function parseResults(path) {
  const byId = new Map();
  if (!existsSync(path)) return { byId, run: null };
  const results = JSON.parse(readFileSync(path, "utf8"));
  let n = 0;
  const walk = (suite, trail) => {
    for (const spec of suite.specs ?? []) {
      const last = spec.tests[0]?.results.at(-1);
      const shots = (last?.attachments ?? [])
        .filter((a) => a.contentType === "image/png" && (a.body || (a.path && existsSync(a.path))))
        .map((a) => {
          // attach({ body }) lands inline as base64; failure screenshots as files.
          const file = `shots/${++n}.png`;
          if (a.body) writeFileSync(`${out}/${file}`, Buffer.from(a.body, "base64"));
          else copyFileSync(a.path, `${out}/${file}`);
          return { label: a.name === "screenshot" ? "Final state" : a.name, file };
        });
      const test = {
        title: spec.title.replace(/\[[\w.-]+\]\s*/g, ""), file: spec.file, line: spec.line,
        suite: trail.filter(Boolean).join(" › "), status: last?.status ?? "not run",
        error: last?.error?.message?.replace(/\u001b\[\d+m/g, "").split("\n")[0] ?? null, shots,
      };
      for (const [, id] of spec.title.matchAll(/\[([\w.-]+)\]/g)) (byId.get(id) ?? byId.set(id, []).get(id)).push(test);
    }
    for (const s of suite.suites ?? []) walk(s, [...trail, s.title.endsWith(".ts") ? "" : s.title]);
  };
  results.suites.forEach((s) => walk(s, []));
  return { byId, run: results.stats?.startTime ?? null };
}

const catalog = parseCatalog(readFileSync("catalog/catalog.md", "utf8"));
const { byId, run } = parseResults("results/results.json");
const map = JSON.parse(readFileSync("docs/map.json", "utf8"));
const pages = JSON.parse(readFileSync("docs/pages.json", "utf8"));
const titleOf = new Map(pages.map((p) => [p.url, p.title]));
const helpUrl = (p) => HELP + p;
const devUrl = (a) => DEV + a;

const features = catalog.map((f) => {
  const tests = [f.id, ...f.aliases].flatMap((id) => byId.get(id) ?? []);
  let status;
  if (tests.length) status = tests.every((t) => t.status === "passed") ? "passing" : "failing";
  else if (/^can't run/i.test(f.catalogStatus)) status = "cant-run";
  else if (/^passing/i.test(f.catalogStatus)) status = "passing";
  else if (/^failing/i.test(f.catalogStatus)) status = "failing";
  else status = "untested";
  const d = map.features[f.id] ?? map.features[f.aliases[0]] ?? {};
  const help = (d.help ?? []).map((p) => ({ url: helpUrl(p), title: (titleOf.get(helpUrl(p)) ?? p).replace(/ - Zenodo.*$/, "") }));
  const dev = (d.dev ?? []).map((a) => ({ url: devUrl(a), title: titleOf.get(devUrl(a)) ?? a }));
  const docs = help.length && dev.length ? "both" : help.length ? "help" : dev.length ? "developers" : d.audience ? "internal" : "none";
  return { ...f, tests, status, docs, audience: d.audience ?? "public", help, dev, docsNote: d.note ?? "", mapped: f.id in map.features };
});

// Crawled help pages no feature or docs_only entry points at: candidates for
// new catalog rows. Index pages that only list their children are skipped.
const referenced = new Set([
  ...Object.values(map.features).flatMap((d) => (d.help ?? []).map(helpUrl)),
  ...map.docs_only.map((d) => (d.url.startsWith("/") ? helpUrl(d.url) : d.url)),
]);
const unmapped = pages
  .filter((p) => p.site === "help" && !p.broken && !referenced.has(p.url))
  .filter((p) => p.url !== `${HELP}/` && !/\/docs\/[a-z-]+\/$/.test(p.url))  // site and section indexes
  .filter((p) => !(p.headings.length <= 1 && /^(Overview|Docs|Guides)?$/.test(p.headings[0] ?? "")))
  .filter((p) => !referenced.has(p.url.replace(/[^/]+\/$/, "")) || p.headings.length > 2)
  .map((p) => ({ url: p.url, title: p.title.replace(/ - Zenodo.*$/, ""), headings: p.headings.slice(0, 6) }));

const pub = features.filter((f) => f.audience === "public");
const count = (arr, k, v) => arr.filter((f) => f[k] === v).length;
const summary = {
  features: features.length, public: pub.length,
  passing: count(features, "status", "passing"), failing: count(features, "status", "failing"),
  untested: count(features, "status", "untested"), cantRun: count(features, "status", "cant-run"),
  docsBoth: count(pub, "docs", "both"), docsHelp: count(pub, "docs", "help"), docsDev: count(pub, "docs", "developers"),
  docsNone: count(pub, "docs", "none"), internal: features.length - pub.length,
  helpPages: pages.filter((p) => p.site === "help" && !p.broken).length,
  devSections: pages.filter((p) => p.site === "developers").length,
  docsOnly: map.docs_only.length, issues: map.issues.length, unmapped: unmapped.length,
  unknownIds: features.filter((f) => !f.mapped).map((f) => f.id), run,
};

const data = { summary, features, docsOnly: map.docs_only, issues: map.issues, unmapped, HELP, DEV };
const html = readFileSync("site/template.html", "utf8").replace(
  "/*DATA*/",
  `const DATA = ${JSON.stringify(data).replace(/</g, "\\u003c")};`,
);
writeFileSync(`${out}/index.html`, html);
console.log(JSON.stringify({ ...summary, unknownIds: summary.unknownIds.length }));
if (summary.unknownIds.length) console.log("Not in docs/map.json:", summary.unknownIds.join(", "));
