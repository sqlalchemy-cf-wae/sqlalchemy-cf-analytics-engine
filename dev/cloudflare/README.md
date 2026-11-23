# Cloudflare test setup

Use this guide to query live Workers Analytics Engine datasets, generate sample
data, or record SQL API responses for the test suite. The Python tests use
recorded responses and run without a Cloudflare account. For local development,
see [Contributing](../../CONTRIBUTING.md).

From the root of your clone, open a terminal and change directories. Run the
remaining commands from this directory.

```bash
cd dev/cloudflare
```

## Configure access to the SQL API

1. Sign in to the [Cloudflare dashboard](https://dash.cloudflare.com/) and
   select the account that owns the datasets. For a new account, open
   **Storage & databases → Analytics Engine** and select **Enable**.
2. Under **My Profile → API Tokens**, create a custom token. Select the
   **Account Analytics** permission with **Read** access for the account.
   Copy the token when Cloudflare displays it.
3. Create a local configuration file from the example.

   ```bash
   cp .env.example .env
   ```

   In the dashboard, press **⌘K** (macOS) or **Ctrl+K** (Windows or Linux)
   to open **Search**. Type **Copy account ID** and select the result.
   You can also copy the ID under **Workers & Pages → Account Details**.

   In `.env`, set `CFWAE_ACCOUNT_ID` to the copied ID and `CFWAE_API_TOKEN`
   to the token you created. Git ignores `.env`.

## Query an existing dataset

List the datasets available to your account. The script reads `.env` and
prints the response body followed by the HTTP status.

```bash
./query.sh "SHOW TABLES FORMAT JSON"
```

If the list includes `api_requests`, run the following query to count requests
by HTTP method, weighted by the sampling interval. If you need sample data,
deploy the Worker using the steps below.

```bash
./query.sh "SELECT blob1, SUM(_sample_interval) AS n FROM api_requests GROUP BY blob1 FORMAT JSON"
```

## Deploy the sample Worker

Use this step when you need to populate your own account. The Worker simulates
traffic for an online store and writes to two datasets every five minutes.

| Dataset | One row represents | Example fields |
| --- | --- | --- |
| `api_requests` | An API request | Account ID, HTTP method, path, status, latency |
| `product_events` | A storefront event | User ID, event name, page URL, SKU, quantity |

See the [Worker source](src/index.js) for the full column mapping and the
[Wrangler configuration](wrangler.jsonc) for the dataset bindings and schedule.

Wrangler is Cloudflare’s command-line tool for deploying Workers. With Node.js
and npm installed, run the login command in your terminal. Wrangler opens a
browser. Approve the authorization request, then return to the terminal.

```bash
npx wrangler@4 login
```

Deploy the Worker using the account you configured for the SQL API.

```bash
npx wrangler@4 deploy
```

On your first deployment, Wrangler may prompt you to choose a `workers.dev`
subdomain. To generate data immediately, open the Worker URL printed by Wrangler
in your browser and append `/seed?n=200` to the URL.

Analytics Engine creates each dataset on its first write. Allow a minute or two
for new data to become queryable, then run the queries above. Cloudflare assigns
timestamps at write time, so hourly and daily charts accumulate data as the
Worker runs.

## Record test fixtures

With `api_requests` populated, run the probe script to refresh the recorded
responses used in offline tests.

```bash
./probe.sh
```

The script overwrites the corresponding files in
[tests/fixtures/responses](../../tests/fixtures/responses) with the response
body and HTTP status for each query. Some queries intentionally exercise API
errors. Review the diff for unexpected responses and account-specific values
before committing.

## Remove the sample Worker

When you finish collecting data, run the following command to remove the
Worker and stop scheduled writes.

```bash
npx wrangler@4 delete
```
