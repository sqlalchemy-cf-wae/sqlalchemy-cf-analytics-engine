// Writes fake API request events to the `cfwae_demo` dataset.
//
// Column layout of each data point:
//   index1   path              (sampling key)
//   blob1    path              e.g. "/checkout"
//   blob2    method            e.g. "GET"
//   blob3    country           e.g. "CA"
//   blob4    status class      e.g. "2xx"
//   blob5    a name with a quote, to test escaping: "O'Malley"
//   double1  latency in ms
//   double2  HTTP status code
//   double3  response size in bytes

const PATHS = ["/", "/checkout", "/cart", "/login", "/api/items", "/api/search"];
const METHODS = ["GET", "GET", "GET", "POST"];
const COUNTRIES = ["CA", "US", "GB", "DE", "IN", "JP"];
const STATUSES = [200, 200, 200, 200, 201, 304, 400, 404, 500];
const NAMES = ["Alice", "Bob", "O'Malley", "Zoë"];

// Analytics Engine accepts a limited number of data points per invocation.
const MAX_BATCH = 100;

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function writeEvents(env, count) {
  const n = Math.min(count, MAX_BATCH);
  for (let i = 0; i < n; i++) {
    const path = pick(PATHS);
    const status = pick(STATUSES);
    env.EVENTS.writeDataPoint({
      indexes: [path],
      blobs: [path, pick(METHODS), pick(COUNTRIES), `${Math.floor(status / 100)}xx`, pick(NAMES)],
      doubles: [Math.round(20 + Math.random() * 480), status, Math.round(Math.random() * 50000)],
    });
  }
  return n;
}

export default {
  // GET /seed?n=50 writes a batch now; anything else writes one event.
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/seed") {
      const n = writeEvents(env, Number(url.searchParams.get("n") || 50));
      return new Response(`Wrote ${n} data points\n`);
    }
    writeEvents(env, 1);
    return new Response("Wrote 1 data point\n");
  },

  // Runs on the cron schedule in wrangler.jsonc.
  async scheduled(controller, env) {
    writeEvents(env, 20 + Math.floor(Math.random() * 40));
  },
};
