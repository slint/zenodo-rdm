// Prints one status per catalog ID from results/results.json: a feature
// passes when every test tagged with its ID passed.
import { readFileSync } from "node:fs";

const results = JSON.parse(readFileSync("results/results.json", "utf8"));
const status = new Map();
const failures = [];

function walk(suite) {
  for (const spec of suite.specs ?? []) {
    const ok = spec.tests.every((t) => t.results.at(-1)?.status === "passed");
    for (const [, id] of spec.title.matchAll(/\[([\w.-]+)\]/g)) {
      status.set(id, (status.get(id) ?? true) && ok);
    }
    if (!ok) failures.push(spec.title);
  }
  for (const child of suite.suites ?? []) walk(child);
}
results.suites.forEach(walk);

for (const [id, ok] of [...status].sort()) console.log(`${id}\t${ok ? "passing" : "failing"}`);
if (failures.length) console.log(`\nFailed:\n${failures.map((f) => `- ${f}`).join("\n")}`);
