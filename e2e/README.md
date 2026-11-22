# Feature catalog checks

Browser and API checks for the features in the
[Zenodo feature catalog](https://ampcode.com/artifacts/zenodo-feature-catalog-862fb917-5f26-4c27-bfca-08d7d157ffca).
Each test title starts with the catalog IDs it covers, such as `[records.export]`.

They run against a live instance, by default the all-in-one image:

```sh
docker build -f docker/mini/Dockerfile -t zenodo-mini-all .   # after building the app image
docker run -p 5000:5000 -v zenodo-mini:/var/lib/postgresql zenodo-mini-all

cd e2e
npm ci && npx playwright install chromium
npx playwright test          # ZENODO_URL=https://... to target another instance
npm run report               # catalog ID -> passing/failing
```

`tests/auth.setup.ts` logs in the fixture users from `app_data/users.yaml`
and creates an API token for each; the other tests use those sessions and tokens.
Tests create their own records, so they run on a fresh or reused instance.
Search on the mini image runs on ParadeDB, so assert membership, not ranking order.
