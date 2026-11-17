# Cloudflare test setup

A Worker that simulates traffic for "Northwind Shop", a made-up e-commerce
company, and writes it to Analytics Engine the way a production app would,
plus scripts to query the SQL API and save its replies as test fixtures.
None of this is part of the published package.

The data is deliberately not shaped for Superset: columns are in the order an
app developer would pick, values are raw (full URLs, user agents, error
messages), and traffic follows a daily cycle with occasional incidents.

| Dataset | One row per | Columns |
|---|---|---|
| `api_requests` | public API call | `index1` account ID; `blob1` method, `blob2` path with IDs and query string, `blob3` country, `blob4` colo, `blob5` user agent, `blob6` API version, `blob7` error code, `blob8` error message; `double1` status, `double2` latency ms, `double3` response bytes, `double4` request bytes, `double5` cache hit |
| `product_events` | storefront analytics event | `index1` user ID; `blob1` event name, `blob2` session ID, `blob3` page URL, `blob4` referrer, `blob5` device, `blob6` plan, `blob7` SKU, `blob8` search query, `blob9` currency; `double1` value, `double2` quantity, `double3` time on page ms |

The full layout is documented at the top of `src/index.js`.

## One-time setup (each teammate)

About 10–15 minutes. Everything here works on the free plan.

1. **Cloudflare account.** Sign up at <https://dash.cloudflare.com/sign-up>
   if you don't have one.
2. **Enable Analytics Engine.** It's off by default. In the dashboard go to
   Storage & databases → Analytics Engine and click **Enable**. Without this,
   deploying fails with "You need to enable Analytics Engine" and queries
   return `403 Authorization error`.
3. **Log in Wrangler** (opens a browser). Logging in to the dashboard is not
   enough; Wrangler needs its own login:
   ```bash
   cd dev/cloudflare && npx wrangler@4 login
   ```
4. **API token for queries.** In the dashboard: My Profile → API Tokens →
   Create Token → Start from scratch → Start with an Account policy →
   Analytics & Logs → tick *Account Analytics, Read* → Continue to summary →
   Create Token. Copy it straight away; it's only shown once.
5. **`.env` file.**
   ```bash
   cp .env.example .env
   ```
   Fill in `CFWAE_ACCOUNT_ID` (the 32-character ID in your dashboard URL)
   and `CFWAE_API_TOKEN`. `.env` is gitignored. Never commit it. The names
   deliberately don't start with `CF_`/`CLOUDFLARE_`, because Wrangler would
   pick those up and try to deploy with the read-only token.

## Deploy the Worker

```bash
cd dev/cloudflare && npx wrangler@4 deploy
```

On a brand-new account, Wrangler first asks you to choose a `workers.dev`
subdomain; the Worker's URL ends up as `cfwae-demo.<subdomain>.workers.dev`.

Both datasets are created on the first write. A cron trigger then simulates
traffic every 5 minutes (busier around 18:00 UTC, quieter on weekends, with an
occasional burst of 5xx errors), so hourly and daily charts fill in over time.
Timestamps are set by Cloudflare and can't be backdated. To write a burst
straight away, open `https://cfwae-demo.<your-subdomain>.workers.dev/seed?n=200`.

New data can take a minute or two to become queryable.

## Query the SQL API

```bash
./query.sh "SELECT blob1, SUM(_sample_interval) AS n FROM api_requests GROUP BY blob1 FORMAT JSON"
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
