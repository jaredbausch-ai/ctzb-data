// Tests for the ctzb-site Worker (item 18): the member site served from Cloudflare.
// The mirror and the trades relay are mocked Service Bindings. Run: node tests/test_site_worker.mjs
import fs from "node:fs"; import os from "node:os"; import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "ctzbsite-")), "w.mjs");
fs.writeFileSync(tmp, fs.readFileSync(path.join(ROOT, "cloudflare/ctzb-site-worker.js"), "utf8") + "\nexport const _test = { handle, csvToBars };\n");
const { _test, default: worker } = await import(pathToFileURL(tmp));
const res = []; const check = (n, c, d = "") => { res.push(!!c); console.log(`  ${c ? "PASS" : "*** FAIL ***"}  ${n}${d ? "  -- " + d : ""}`); };

const FEED = JSON.stringify({ schema_version: 6, cards: [] });
const LEDGER = "asset,chart,grade\nETH,ETH 2D,A+\n";
const CANDLES = "time,open,high,low,close\n1788393600,77307.36,82283,76929.29,81263.99\n1788480000,81263.99,81438.01,78626,79675.12\n";
const seen = [];
const mirror = { fetch: async (req) => { const p = new URL(req.url).pathname; seen.push(p);
  if (p === "/feed/ctzb_feed.json") return new Response(FEED);
  if (p === "/datasets/ledger.csv") return new Response(LEDGER);
  if (p === "/datasets/candles_btc_1d.csv") return new Response(CANDLES);
  if (p === "/datasets/candles_btc_2d.csv") return new Response(CANDLES + "1788566400,79675.12,nan,78000,79000\n");
  if (p === "/datasets/candles_btc_3d.csv") return new Response(CANDLES.slice(0, -2));   // cut short: 79675.12 reads 79675.1
  return new Response("nope", { status: 404 }); } };
let tradesStatus = 404;
const trades = { fetch: async () => tradesStatus === 200 ? new Response(JSON.stringify({ trades: [] })) : new Response("{}", { status: tradesStatus }) };
const PW = { GATE_MODE: "password", SITE_PASSWORD: "pw-test", MIRROR: mirror, TRADES: trades };
const req = (p, auth, method = "GET") => new Request("https://ctzb-site.example.workers.dev" + p, { method, headers: auth ? { authorization: "Basic " + btoa("x:" + auth) } : {} });

let r = await _test.handle(req("/"), { MIRROR: mirror, TRADES: trades });
check("no GATE_MODE: everything refused", r.status === 503);
r = await _test.handle(req("/"), { ...PW, GATE_MODE: "open" });
check("unknown GATE_MODE: refused", r.status === 503);
r = await _test.handle(req("/"), PW);
check("password mode, no password: refused", r.status === 401 && r.headers.get("www-authenticate"));
r = await _test.handle(req("/data/ctzb_feed.json", "wrong"), PW);
check("wrong password: data refused too", r.status === 401);
r = await _test.handle(req("/"), { ...PW, SITE_PASSWORD: undefined });
check("password mode with no password set: refused", r.status === 401);
r = await _test.handle(req("/", "x"), { GATE_MODE: "access", ACCESS_TEAM_DOMAIN: "t.cloudflareaccess.com", ACCESS_AUD: "aud", MIRROR: mirror, TRADES: trades }, async () => new Response("{}", { status: 500 }));
check("access mode without an Access token: refused", r.status === 403);

r = await _test.handle(req("/", "pw-test"), PW);
const html = await r.text();
check("page served to a logged-in viewer", r.status === 200 && html.startsWith("<!doctype html>") && html.includes("ETHKROS"));
check("page carries a CSP and no-store", /default-src 'none'/.test(r.headers.get("content-security-policy")) && r.headers.get("cache-control") === "no-store");
r = await _test.handle(req("/data/ctzb_feed.json", "pw-test"), PW);
check("feed comes from the mirror, unchanged", r.status === 200 && (await r.text()) === FEED && seen.includes("/feed/ctzb_feed.json"));
r = await _test.handle(req("/data/ledger.csv", "pw-test"), PW);
check("ledger comes from the mirror's datasets", r.status === 200 && (await r.text()) === LEDGER);
r = await _test.handle(req("/data/candles/BTC_1D.json", "pw-test"), PW);
const c = await r.json();
check("candles: mirror CSV becomes the page's JSON", r.status === 200 && c.chart === "BTC 1D" && c.bars.length === 2 && c.bars[0].h === 82283);
r = await _test.handle(req("/data/candles/BTC_2D.json", "pw-test"), PW);
check("candles with a row that is not numbers: the whole file refused (502), no row dropped silently", r.status === 502);
r = await _test.handle(req("/data/candles/BTC_3D.json", "pw-test"), PW);
check("candles cut short (last line has no line end): refused (502), never a shorter last close (audit #29)", r.status === 502);
r = await _test.handle(req("/data/candles/ETH_3D.json", "pw-test"), PW);
check("candles missing upstream: 404, not an error page", r.status === 404);
for (const p of ["/data/candles/../ledger.json", "/data/candles/SOL_1D.json", "/data/candles/BTC_4H.json", "/data/datasets/status.csv", "/feed/ctzb_feed.json", "/data/candles/btc_1d.json"]) {
  r = await _test.handle(req(p, "pw-test"), PW);
  check(`path outside the fixed table refused: ${p}`, r.status === 404);
}
check("no caller-supplied path ever reached the mirror", seen.every((p) => ["/feed/ctzb_feed.json", "/datasets/ledger.csv", "/datasets/candles_btc_1d.csv", "/datasets/candles_btc_2d.csv", "/datasets/candles_btc_3d.csv", "/datasets/candles_eth_3d.csv"].includes(p)), seen.join(" "));
r = await _test.handle(req("/data/trades.json", "pw-test"), PW);
check("trades relay in dry run (404): page gets 404 and shows its empty state", r.status === 404);
tradesStatus = 200; r = await _test.handle(req("/data/trades.json", "pw-test"), PW);
check("trades relay live: passed through", r.status === 200);
r = await _test.handle(req("/data/ctzb_feed.json", "pw-test"), { ...PW, MIRROR: { fetch: async () => { throw new Error("down"); } } });
check("mirror down: 502 with a fixed message, no upstream detail", r.status === 502 && (await r.text()) === "Data source unavailable");
r = await _test.handle(req("/data/example_ETH-2D-2024-09-22.json", "pw-test"), PW);
check("built-in chart example served", r.status === 200 && (await r.json()).signal_id === "ETH-2D-2024-09-22");
r = await _test.handle(req("/", "pw-test", "POST"), PW);
check("POST refused", r.status === 405);

console.log(`\n${res.filter(Boolean).length}/${res.length} passed`);
process.exit(res.every(Boolean) ? 0 : 1);
