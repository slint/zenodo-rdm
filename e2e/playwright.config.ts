import { defineConfig } from "@playwright/test";

// Checks run against a running instance, by default the all-in-one image
// (docker/mini/Dockerfile) on https://127.0.0.1:5000 with its fixture users.
export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  // One app process serves the mini image; parallel workers only add noise.
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "results/results.json" }]],
  use: {
    baseURL: process.env.ZENODO_URL ?? "https://127.0.0.1:5000",
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    { name: "checks", dependencies: ["setup"] },
  ],
});
