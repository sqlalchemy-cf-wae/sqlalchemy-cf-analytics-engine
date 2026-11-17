# Cloudflare test setup

A small Worker that writes fake app events to the `cfwae_demo` Analytics
Engine dataset, plus scripts to query the SQL API and save its replies as test
fixtures. None of this is part of the published package.

## One-time setup (each teammate)

1. **Cloudflare account.** Sign up at <https://dash.cloudflare.com/sign-up>
   if you don't have one. The free Workers plan should be enough.
2. **Log in Wrangler** (opens a browser):
   ```bash
   cd dev/cloudflare && npx wrangler@4 login
   ```
3. **API token for queries.** In the dashboard: My Profile → API Tokens →
   Create Token → Custom token → permission
   *Account / Account Analytics / Read*. Then:
   ```bash
   cp .env.example .env   # and paste in your account ID and token
   ```
   `.env` is gitignored. Never commit it.

## Deploy the Worker

```bash
cd dev/cloudflare && npx wrangler@4 deploy
```

This creates the `cfwae_demo` dataset on the first write. A cron trigger then
writes 20–60 events every 15 minutes, so hourly and daily charts fill in over
time. To write a batch straight away, open
`https://cfwae-demo.<your-subdomain>.workers.dev/seed?n=100`.

New data can take a minute or two to become queryable.

## Query the SQL API

```bash
./query.sh "SELECT blob1, SUM(_sample_interval) AS n FROM cfwae_demo GROUP BY blob1 FORMAT JSON"
```

## Record fixtures

```bash
./probe.sh
```

Runs every query the driver, dialect and engine spec rely on (time grains,
date literals, LIMIT/OFFSET, subqueries, joins, quoting, errors) and saves each
raw reply to `tests/fixtures/responses/`. Check the files for anything account
specific before committing them.

## Clean up

The cron trigger keeps writing until the Worker is removed:

```bash
npx wrangler@4 delete
```
