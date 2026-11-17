#!/usr/bin/env bash
# Send one SQL query to the Workers Analytics Engine SQL API and print the
# raw reply. Reads CFWAE_ACCOUNT_ID and CFWAE_API_TOKEN from dev/cloudflare/.env.
#
#   ./query.sh "SELECT count() FROM api_requests FORMAT JSON"
set -euo pipefail

cd "$(dirname "$0")"
if [[ ! -f .env ]]; then
  echo "Missing dev/cloudflare/.env - copy .env.example and fill it in." >&2
  exit 1
fi
set -a; source .env; set +a

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 \"<SQL>\"" >&2
  exit 1
fi

curl -sS -w '\nHTTP %{http_code}\n' \
  -X POST "https://api.cloudflare.com/client/v4/accounts/${CFWAE_ACCOUNT_ID}/analytics_engine/sql" \
  -H "Authorization: Bearer ${CFWAE_API_TOKEN}" \
  --data-binary "$1"
