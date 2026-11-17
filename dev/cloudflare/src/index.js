// Simulated traffic for "Northwind Shop", a small e-commerce company.
//
// The column layouts below are what a real app would write: the order of
// blobs and doubles is whatever the app developer picked, labels are raw
// values (no precomputed groupings), unused fields are left out, and text
// comes from real-looking sources (URLs, user agents, error messages, search
// queries). Nothing here is shaped to make querying from Superset easier.
//
// ---------------------------------------------------------------------------
// Dataset `api_requests` (binding API_REQUESTS): one row per public API call
//   index1   customer account ID         sampling key, per tenant
//   blob1    HTTP method
//   blob2    request path with IDs and query string
//   blob3    request.cf.country
//   blob4    request.cf.colo (Cloudflare data center)
//   blob5    User-Agent header
//   blob6    API version header
//   blob7    error code, "" on success
//   blob8    error message, "" on success
//   double1  HTTP status code
//   double2  latency in ms
//   double3  response size in bytes
//   double4  request body size in bytes
//   double5  cache hit (1) or miss (0)
//
// Dataset `product_events` (binding PRODUCT_EVENTS): storefront analytics
//   index1   user ID ("anon_..." when signed out)
//   blob1    event name
//   blob2    session ID
//   blob3    page URL
//   blob4    referrer URL, "" for direct traffic
//   blob5    device type
//   blob6    subscription plan
//   blob7    product SKU, "" when not about a product
//   blob8    search query, "" unless event is "search"
//   blob9    currency, "" unless money is involved
//   double1  order or cart value in `blob9` currency
//   double2  item quantity
//   double3  time on page in ms (page_view only)
// ---------------------------------------------------------------------------

// Writes per invocation are limited; stay well under the cap.
const MAX_WRITES = 200;

// ---------- helpers ----------

const rand = Math.random;

function pick(list) {
  return list[Math.floor(rand() * list.length)];
}

// Pick from [[value, weight], ...].
function weighted(pairs) {
  let total = 0;
  for (const [, w] of pairs) total += w;
  let r = rand() * total;
  for (const [v, w] of pairs) {
    if ((r -= w) < 0) return v;
  }
  return pairs[pairs.length - 1][0];
}

// Skewed pick: early items are much more likely (a few big customers, many
// small ones), like real tenant traffic.
function zipf(list) {
  return list[Math.floor(list.length * Math.pow(rand(), 2.5))];
}

function int(min, max) {
  return min + Math.floor(rand() * (max - min + 1));
}

// Long-tailed latency: most requests are fast, a few are very slow.
function latency(medianMs) {
  const normal = Math.sqrt(-2 * Math.log(1 - rand())) * Math.cos(2 * Math.PI * rand());
  return Math.max(1, Math.round(medianMs * Math.exp(0.6 * normal)));
}

function hex(len) {
  let s = "";
  for (let i = 0; i < len; i++) s += Math.floor(rand() * 16).toString(16);
  return s;
}

// ---------- shared reference data ----------

const ACCOUNTS = Array.from({ length: 40 }, (_, i) => `acct_${(0x1a2b3c + i * 7919).toString(16)}`);
const USERS = Array.from({ length: 600 }, (_, i) => `usr_${(0x5000 + i * 104729).toString(36)}`);

// [country, colo] pairs, weighted by traffic share.
const LOCATIONS = [
  [["US", "IAD"], 18], [["US", "SJC"], 14], [["US", "ORD"], 9], [["CA", "YYZ"], 12],
  [["CA", "YVR"], 4], [["GB", "LHR"], 10], [["DE", "FRA"], 8], [["FR", "CDG"], 5],
  [["IN", "BOM"], 6], [["JP", "NRT"], 5], [["BR", "GRU"], 4], [["AU", "SYD"], 3],
  [["NL", "AMS"], 2],
];

const SKUS = [
  "NW-TRAIL-RUNNER-2", "NW-ROAD-RACER", "NW-HIKER-MID-GTX", "NW-KIDS-SPLASH",
  "NW-WOOL-SOCK-3PK", "NW-RAIN-SHELL", "NW-DOWN-VEST", "NW-CAP-LOGO",
];
const PRICES = {
  "NW-TRAIL-RUNNER-2": 149.0, "NW-ROAD-RACER": 179.99, "NW-HIKER-MID-GTX": 229.5,
  "NW-KIDS-SPLASH": 54.99, "NW-WOOL-SOCK-3PK": 24.0, "NW-RAIN-SHELL": 189.0,
  "NW-DOWN-VEST": 139.99, "NW-CAP-LOGO": 29.0,
};

// ---------- api_requests ----------

const USER_AGENTS = [
  ["northwind-node/4.2.1 (+https://github.com/northwind/node-sdk) node/20.11.1", 30],
  ["northwind-python/2.8.0 python-requests/2.31.0 CPython/3.11.7", 25],
  ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", 15],
  ["Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1", 8],
  ["curl/8.4.0", 7],
  ["Go-http-client/2.0", 6],
  ["Zapier", 5],
  ["PostmanRuntime/7.37.3", 4],
];

// [method, path builder, typical latency ms, request bytes], weighted.
const ENDPOINTS = [
  [["GET", () => `/v1/products?category=${pick(["shoes", "apparel", "accessories"])}&page=${int(1, 6)}&limit=24`, 45, 0], 22],
  [["GET", () => `/v1/products/${pick(SKUS)}`, 25, 0], 18],
  [["GET", () => `/v1/orders/ord_${hex(10)}`, 60, 0], 12],
  [["GET", () => `/v1/orders?status=${pick(["open", "shipped", "refunded"])}&created_after=2026-${String(int(1, 11)).padStart(2, "0")}-01`, 140, 0], 8],
  [["POST", () => "/v1/orders", 220, 1400], 7],
  [["POST", () => "/v1/carts", 80, 600], 6],
  [["PATCH", () => `/v1/carts/cart_${hex(8)}/items`, 70, 350], 6],
  [["POST", () => "/v1/payments/intents", 380, 900], 4],
  [["GET", () => "/v1/customers/me", 30, 0], 9],
  [["PUT", () => `/v1/customers/cus_${hex(8)}/addresses/default`, 90, 500], 2],
  [["DELETE", () => `/v1/carts/cart_${hex(8)}`, 40, 0], 2],
  [["POST", () => "/v1/webhooks/stripe", 120, 3200], 3],
  [["GET", () => "/healthz", 3, 0], 4],
];

// [status, error code, message builder], used when a request fails.
const FAILURES = [
  [400, "validation_error", () => `Field 'quantity' must be a positive integer, got ${pick(["-1", "0", "\"two\""])}`],
  [400, "validation_error", () => "Body is not valid JSON: Unexpected token } in JSON at position 87"],
  [401, "unauthorized", () => "Missing or invalid API key"],
  [403, "forbidden", () => `Customer "O'Brien & Sons Ltd" has no active subscription`],
  [404, "not_found", () => `No such order: 'ord_${hex(10)}'`],
  [409, "conflict", () => "Order is already in state \"shipped\" and can't be cancelled"],
  [422, "card_declined", () => "Your card was declined. Reason: insufficient_funds"],
  [429, "rate_limited", () => "Rate limit of 100 req/10s exceeded; retry after 3s"],
  [500, "internal_error", () => "Unexpected error. Request ID req_" + hex(16)],
  [502, "upstream_error", () => "Payment provider timed out after 10000ms"],
  [503, "unavailable", () => "Inventory service unavailable (circuit open)"],
];

function apiRequest(incident) {
  const [method, path, median, reqBytes] = weighted(ENDPOINTS);
  const [country, colo] = weighted(LOCATIONS);
  const p = path();

  let status = method === "POST" && p !== "/v1/webhooks/stripe" ? 201 : 200;
  if (method === "DELETE") status = 204;
  let code = "";
  let message = "";

  // ~6% of requests fail normally; during an incident 5xx errors spike.
  const failRate = incident ? 0.3 : 0.06;
  if (p !== "/healthz" && rand() < failRate) {
    const pool = incident ? FAILURES.filter(([s]) => s >= 500) : FAILURES;
    const [s, c, m] = pick(pool);
    status = s;
    code = c;
    message = m();
  } else if (method === "GET" && rand() < 0.05) {
    status = 304;
  }

  const slow = incident || status >= 500 ? 4 : 1;
  const cacheHit = method === "GET" && status === 200 && rand() < 0.35 ? 1 : 0;
  const ms = cacheHit ? int(1, 8) : latency(median * slow);
  const resBytes = status === 204 || status === 304 ? 0 : status >= 400 ? int(90, 400) : int(300, 48000);

  return {
    indexes: [zipf(ACCOUNTS)],
    blobs: [method, p, country, colo, weighted(USER_AGENTS), pick(["2025-01-15", "2025-01-15", "2025-09-30", "2024-06-01"]), code, message],
    doubles: [status, ms, resBytes, reqBytes ? int(reqBytes / 2, reqBytes * 2) : 0, cacheHit],
  };
}

// ---------- product_events ----------

const REFERRERS = [
  ["", 40],
  ["https://www.google.com/", 30],
  ["https://www.instagram.com/", 8],
  ["https://news.ycombinator.com/", 2],
  ["https://mail.northwindshop.com/newsletter/2026-11", 6],
  ["https://www.bing.com/search?q=trail+running+shoes", 4],
  ["https://www.reddit.com/r/trailrunning/comments/1abc2d/", 4],
  ["https://duckduckgo.com/", 3],
];

const SEARCHES = [
  "trail running shoes", "waterproof hiking boots", "kids' rain boots", "wool socks",
  "gore-tex", "size 11 wide", "vest", "Running Shoes", "  running shoes ", "chaussures de randonnée",
  "regenjacke damen", "gift card", "return policy", "black friday", "跑鞋",
];

// [event name, weight]: a realistic funnel, most traffic never buys.
const EVENTS = [
  ["page_view", 55], ["search", 12], ["product_view", 15], ["add_to_cart", 7],
  ["remove_from_cart", 2], ["checkout_started", 3], ["purchase", 1.5],
  ["signup", 1], ["login", 2.5], ["newsletter_subscribe", 1],
];

const PAGES = ["/", "/collections/shoes", "/collections/sale", "/cart", "/account", "/help/returns", "/blog/how-to-choose-trail-shoes"];

function productEvent() {
  const name = weighted(EVENTS);
  const signedIn = rand() < 0.45 || ["purchase", "login", "checkout_started"].includes(name);
  const user = signedIn ? zipf(USERS) : `anon_${hex(12)}`;
  const sku = ["product_view", "add_to_cart", "remove_from_cart"].includes(name) ? pick(SKUS) : "";
  const currency = ["add_to_cart", "remove_from_cart", "checkout_started", "purchase"].includes(name)
    ? weighted([["USD", 60], ["CAD", 25], ["EUR", 10], ["GBP", 5]])
    : "";

  let page = "https://www.northwindshop.com" + pick(PAGES);
  if (sku) page = `https://www.northwindshop.com/products/${sku.toLowerCase()}?variant=${int(40000000, 49999999)}`;
  if (name === "search") page = "https://www.northwindshop.com/search";
  if (name === "purchase") page = `https://www.northwindshop.com/checkout/thank-you?order=ord_${hex(10)}`;
  if (rand() < 0.15) page += (page.includes("?") ? "&" : "?") + "utm_source=newsletter&utm_medium=email&utm_campaign=bf2026";

  let qty = 0;
  let value = 0;
  if (sku) {
    qty = name === "product_view" ? 0 : int(1, 3);
    value = qty * PRICES[sku];
  } else if (name === "checkout_started" || name === "purchase") {
    qty = int(1, 5);
    value = Math.round(qty * (30 + rand() * 170) * 100) / 100;
  }

  return {
    indexes: [user],
    blobs: [
      name,
      `sess_${hex(16)}`,
      page,
      rand() < 0.7 ? weighted(REFERRERS) : "",
      weighted([["desktop", 52], ["mobile", 42], ["tablet", 6]]),
      signedIn ? weighted([["free", 70], ["plus", 25], ["business", 5]]) : "",
      sku,
      name === "search" ? pick(SEARCHES) : "",
      currency,
    ],
    doubles: [value, qty, name === "page_view" ? latency(18000) : 0],
  };
}

// ---------- traffic simulation ----------

// Daily cycle: busiest around 18:00 UTC (afternoon in North America),
// quietest around 06:00 UTC.
function trafficMultiplier(date) {
  const hour = date.getUTCHours() + date.getUTCMinutes() / 60;
  const daily = 0.55 + 0.45 * Math.cos(((hour - 18) / 24) * 2 * Math.PI);
  const weekend = [0, 6].includes(date.getUTCDay()) ? 0.7 : 1;
  return daily * weekend;
}

function simulate(env, total, incident = false) {
  const n = Math.min(total, MAX_WRITES);
  const api = Math.round(n * 0.6);
  for (let i = 0; i < api; i++) env.API_REQUESTS.writeDataPoint(apiRequest(incident));
  for (let i = api; i < n; i++) env.PRODUCT_EVENTS.writeDataPoint(productEvent());
  return { api_requests: api, product_events: n - api };
}

export default {
  // GET /seed?n=100 simulates a burst of traffic now.
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/seed") return new Response("Not found\n", { status: 404 });
    const n = Number(url.searchParams.get("n") || 100);
    return Response.json({ wrote: simulate(env, n) });
  },

  // Every 5 minutes: volume follows the daily cycle, and about 1 run in 50
  // is a short incident with a burst of 5xx errors and slow responses.
  async scheduled(controller, env) {
    const now = new Date(controller.scheduledTime);
    const base = 40 + Math.floor(rand() * 30);
    simulate(env, Math.round(base * trafficMultiplier(now)), rand() < 0.02);
  },
};
