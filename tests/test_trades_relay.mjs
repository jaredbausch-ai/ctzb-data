// Tests for the ctzb-trades Worker (item 13a): the lead trader's real trades from Coinbase.
// Coinbase and KV are mocked; every request's JWT is verified against the test key.
// Run: node tests/test_trades_relay.mjs
import fs from "node:fs"; import os from "node:os"; import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "ctzbtrades-")), "w.mjs");
fs.writeFileSync(tmp, fs.readFileSync(path.join(ROOT, "cloudflare/ctzb-trades-worker.js"), "utf8") +
  "\nexport const _test = { tick, handle, makeJwt, signingKey };\n");
const { _test, default: worker } = await import(pathToFileURL(tmp));

const res = []; const check = (n, c, d = "") => { res.push(!!c); console.log(`  ${c ? "PASS" : "*** FAIL ***"}  ${n}${d ? "  -- " + d : ""}`); };
const kv = () => { const m = new Map(); let puts = 0; return { m, puts: () => puts,
  get: async (k, o) => { const v = m.get(k); return v === undefined ? null : (o && o.type === "json" ? JSON.parse(v) : v); },
  put: async (k, v) => { puts++; m.set(k, v); } }; };

// ---- a test key, in the form Coinbase hands out (SEC1 "EC PRIVATE KEY") ----
const { privateKey, publicKey } = crypto.generateKeyPairSync("ec", { namedCurve: "P-256" });
const SEC1 = privateKey.export({ type: "sec1", format: "pem" });
const KEYNAME = "organizations/test-org/apiKeys/test-key";

// ---- mock Coinbase ----
const P = {
  "ETP-20DEC30-CDE": { future_product_details: { contract_root_unit: "ETH", contract_size: "0.1", contract_expiry_type: "PERPETUAL" } },
  "BIP-20DEC30-CDE": { future_product_details: { contract_root_unit: "BTC", contract_size: "0.01", contract_expiry_type: "PERPETUAL" } },
  "SLP-20DEC30-CDE": { future_product_details: { contract_root_unit: "SOL", contract_size: "5", contract_expiry_type: "PERPETUAL" } },
};
const cb = { fills: [], positions: [], balance: 400000, margin: 150000, down: false, calls: [], jwtProblems: [], nonces: new Set() };
const amt = (v) => ({ value: String(v), currency: "USD" });
const b64d = (s) => Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64");
async function fx(url, init) {
  const u = new URL(url);
  cb.calls.push(u.pathname);
  const jwt = (init.headers.authorization || "").replace(/^Bearer /, "");
  const [h, c, s] = jwt.split(".");
  const head = JSON.parse(b64d(h)), claims = JSON.parse(b64d(c));
  const ok = crypto.verify("sha256", Buffer.from(`${h}.${c}`), { key: publicKey, dsaEncoding: "ieee-p1363" }, b64d(s));
  if (!ok) cb.jwtProblems.push("bad signature");
  if (head.alg !== "ES256" || head.kid !== KEYNAME || !head.nonce) cb.jwtProblems.push("bad header");
  if (cb.nonces.has(head.nonce)) cb.jwtProblems.push("nonce reused"); cb.nonces.add(head.nonce);
  if (claims.iss !== "cdp" || claims.sub !== KEYNAME || claims.exp - claims.nbf !== 120) cb.jwtProblems.push("bad claims");
  if (claims.uri !== `GET api.coinbase.com${u.pathname}`) cb.jwtProblems.push(`bad uri ${claims.uri}`);
  if (init.method !== "GET") cb.jwtProblems.push("non-GET request");
  if (cb.down) return new Response("oops", { status: 503 });
  const J = (o) => new Response(JSON.stringify(o), { status: 200 });
  if (u.pathname === "/api/v3/brokerage/orders/historical/fills") {
    const start = Date.parse(u.searchParams.get("start_sequence_timestamp"));
    if (u.searchParams.getAll("product_types").join() !== "FUTURE") cb.jwtProblems.push("fills not limited to futures");
    return J({ fills: cb.fills.filter((f) => Date.parse(f.trade_time) >= start), cursor: "" });
  }
  if (u.pathname === "/api/v3/brokerage/cfm/positions") return J({ positions: cb.positions });
  if (u.pathname === "/api/v3/brokerage/cfm/balance_summary") return J({ balance_summary: { total_usd_balance: amt(cb.balance), initial_margin: amt(cb.margin) } });
  if (u.pathname.startsWith("/api/v3/brokerage/products/")) return J(P[decodeURIComponent(u.pathname.split("/").pop())] || {});
  return new Response("nope", { status: 404 });
}
const pos = (pid, side, n, avg, cur) => ({ product_id: pid, side, number_of_contracts: String(n), avg_entry_price: String(avg), current_price: String(cur ?? avg) });
let seq = 0;
const fill = (order, pid, side, size, price, t, extra = {}) => ({ entry_id: `e${++seq}`, trade_id: `t${seq}`, order_id: order, product_id: pid,
  side, size: String(size), price: String(price), commission: "0", trade_time: t, sequence_timestamp: t, trade_type: "FILL", ...extra });

let clock = Date.parse("2026-11-11T12:00:00Z");
const now = () => clock;
const step = (min = 1) => { clock += min * 60000; return new Date(clock).toISOString(); };
const ENV = (k, mode) => ({ TRADES: k, COINBASE_KEY_NAME: KEYNAME, COINBASE_PRIVATE_KEY: SEC1, DRY_VIEW_PASSWORD: "pw-test", ...(mode ? { MODE: mode } : {}) });
const events = (k) => JSON.parse(k.m.get("events") || "[]");
const state = (k) => JSON.parse(k.m.get("state"));

// ---- 1. baseline ----
let k = kv();
cb.positions = [pos("BIP-20DEC30-CDE", "LONG", 10, 100000)];
let r = await _test.tick(ENV(k), fx, now);
check("first run takes a baseline and posts nothing", r.posted === 0 && !k.m.has("events") && state(k).baseline_at);
check("baseline records the already-open BTC position", state(k).positions["BIP-20DEC30-CDE"]?.qty === 10);
check("every request carried a valid ES256 JWT for its exact path", cb.jwtProblems.length === 0, cb.jwtProblems.join("; "));

// ---- 2. an order filled in three pieces = one open ----
let t = step();
cb.fills.push(fill("A", "ETP-20DEC30-CDE", "BUY", 600, 3100, t), fill("A", "ETP-20DEC30-CDE", "BUY", 600, 3102, t), fill("A", "ETP-20DEC30-CDE", "BUY", 600, 3104, t));
cb.positions = [pos("BIP-20DEC30-CDE", "LONG", 10, 100000), pos("ETP-20DEC30-CDE", "LONG", 1800, 3102)];
step(); r = await _test.tick(ENV(k), fx, now);
let ev = events(k);
check("three fills of one order become one trade", r.posted === 1 && ev.length === 1 && ev[0].action === "open" && ev[0].direction === "long" && ev[0].asset === "ETH");
check("price is the volume-weighted fill price", ev[0].price === 3102);
check("leverage = open notional / initial margin", ev[0].leverage === 3.8, `got ${ev[0].leverage}`);
check("size = margin share / account balance", ev[0].size_pct === 36.8, `got ${ev[0].size_pct}`);
check("made in dry-run mode", ev[0].mode === "dry" && ev[0].instrument === "perp");
const leak = JSON.stringify(ev);
check("no dollar amount, balance, contract count or notional anywhere in the record",
  !/1800|558360|400000|150000|contracts|notional|usd|commission|_realized|product/i.test(leak), leak);

// ---- 3. the same fills seen again (overlap window) ----
step(); r = await _test.tick(ENV(k), fx, now);
check("fills already seen are never posted twice", r.posted === 0 && events(k).length === 1);

// ---- 4. reduce half ----
t = step();
cb.fills.push(fill("B", "ETP-20DEC30-CDE", "SELL", 900, 3400, t, { commission: "10" }));
cb.positions = [pos("BIP-20DEC30-CDE", "LONG", 10, 100000), pos("ETP-20DEC30-CDE", "LONG", 900, 3102, 3400)];
cb.balance = 426810;
step(); r = await _test.tick(ENV(k), fx, now);
ev = events(k);
check("partial sale is a reduce of 50%", ev[0].action === "reduce" && ev[0].reduced_pct === 50, JSON.stringify(ev[0]));
check("reduce shows the move from average entry", ev[0].move_pct === 9.6, `got ${ev[0].move_pct}`);
check("reduce shows the result as % of the account, after fees", ev[0].account_pct === 6.7, `got ${ev[0].account_pct}`);
check("reduce carries the entry's leverage and size", ev[0].leverage === 3.8 && ev[0].size_pct === 36.8);

// ---- 5. sell through zero: close, then open short ----
t = step();
cb.fills.push(fill("C", "ETP-20DEC30-CDE", "SELL", 1500, 3500, t));
cb.positions = [pos("BIP-20DEC30-CDE", "LONG", 10, 100000), pos("ETP-20DEC30-CDE", "SHORT", 600, 3500)];
cb.balance = 462630;
step(); r = await _test.tick(ENV(k), fx, now);
ev = events(k);
check("flip posts a close and a new short", r.posted === 2 && ev[1].action === "close" && ev[1].direction === "long" && ev[0].action === "open" && ev[0].direction === "short");
check("close shows held time", ev[1].held_days === 0, `got ${ev[1].held_days}`);
check("close move is from the average entry", ev[1].move_pct === 12.8, `got ${ev[1].move_pct}`);

// ---- 6. other assets are ignored ----
t = step();
cb.fills.push(fill("D", "SLP-20DEC30-CDE", "BUY", 3, 150, t));
step(); r = await _test.tick(ENV(k), fx, now);
check("a non-BTC/ETH fill is ignored, not posted", r.posted === 0 && state(k).ignored_fills === 1);

// ---- 7. adjusted fill: not posted, flagged ----
t = step();
cb.fills.push(fill("E", "ETP-20DEC30-CDE", "BUY", 600, 3500, t, { trade_type: "REVERSAL" }));
step(); r = await _test.tick(ENV(k), fx, now);
check("an adjusted fill (reversal) is not posted", r.posted === 0);
check("and is logged for review", state(k).notes.some((n) => /adjusted fill/.test(n.text)));

// ---- 8. drift: Coinbase shows a different size with no fills -> reconcile after 15 min ----
cb.positions = [pos("BIP-20DEC30-CDE", "LONG", 10, 100000), pos("ETP-20DEC30-CDE", "SHORT", 500, 3500)];
step(16); r = await _test.tick(ENV(k), fx, now);
check("a mismatch is corrected from Coinbase and logged, nothing posted",
  r.posted === 0 && state(k).positions["ETP-20DEC30-CDE"].qty === -500 && state(k).notes.some((n) => /Reconciled ETP/.test(n.text)));

// ---- 9. closing the baseline position ----
t = step();
cb.fills.push(fill("F", "BIP-20DEC30-CDE", "SELL", 10, 105000, t));
cb.positions = [pos("ETP-20DEC30-CDE", "SHORT", 500, 3500)];
step(); r = await _test.tick(ENV(k), fx, now);
ev = events(k);
check("closing a position that predates the relay posts a close with its move", ev[0].action === "close" && ev[0].asset === "BTC" && ev[0].move_pct === 5);
check("and leaves leverage and size blank, since its entry was never measured", !("leverage" in ev[0]) && !("size_pct" in ev[0]));

// ---- 10. Coinbase down, then back ----
const before = events(k).length, cursorBefore = state(k).cursor_at;
cb.down = true; step(); r = await _test.tick(ENV(k), fx, now);
check("Coinbase down: failure counted, error recorded without secrets",
  state(k).consecutive_failures === 1 && /HTTP 503/.test(state(k).last_error) && !state(k).last_error.includes("PRIVATE"));
check("and the cursor does not move", state(k).cursor_at === cursorBefore);
cb.down = false; t = step();
cb.fills.push(fill("G", "ETP-20DEC30-CDE", "BUY", 500, 3300, t));
cb.positions = [];
step(); r = await _test.tick(ENV(k), fx, now);
check("next tick recovers and posts the missed trade once", state(k).consecutive_failures === 0 && events(k).length === before + 1 && events(k)[0].action === "close");

// ---- 11. idle ticks don't hammer KV ----
const putsBefore = k.puts();
for (let i = 0; i < 10; i++) { step(); await _test.tick(ENV(k), fx, now); }
check("10 quiet minutes cost at most one KV write", k.puts() - putsBefore <= 1, `${k.puts() - putsBefore} writes`);
check("every JWT in the whole run verified, nonces unique, GET only", cb.jwtProblems.length === 0, cb.jwtProblems.slice(0, 3).join("; "));

// ---- 12. HTTP: dry run is private ----
const req = (p, auth) => new Request("https://ctzb-trades.example.workers.dev" + p, auth ? { headers: { authorization: "Basic " + btoa("x:" + auth) } } : {});
let resp = await _test.handle(req("/trades.json"), ENV(k));
check("dry run: /trades.json is not public", resp.status === 404);
resp = await _test.handle(req("/dry"), ENV(k));
check("/dry without a password: refused", resp.status === 401);
resp = await _test.handle(req("/dry", "wrong"), ENV(k));
check("/dry with the wrong password: refused", resp.status === 401);
resp = await _test.handle(req("/dry", "pw"), { ...ENV(k), DRY_VIEW_PASSWORD: undefined });
check("/dry with no password configured: fails closed", resp.status === 503);
resp = await _test.handle(req("/dry", "pw-test"), ENV(k));
let body = await resp.json();
check("/dry with the password shows the would-be posts and review notes", resp.status === 200 && body.trades.length === events(k).length && body.review_notes.length > 0);
check("/dry shows no contract counts or balances either", !/contracts|balance"|qty|notional/i.test(JSON.stringify(body.open_positions)));
resp = await _test.handle(req("/health"), ENV(k));
body = await resp.json();
check("/health is public and carries no trade data", resp.status === 200 && body.mode === "dry" && !("trades" in body) && !("open_positions" in body));

// ---- 13. live mode publishes only live-made trades ----
t = step();
cb.fills.push(fill("H", "ETP-20DEC30-CDE", "BUY", 100, 3200, t));
cb.positions = [pos("ETP-20DEC30-CDE", "LONG", 100, 3200)];
step(); await _test.tick(ENV(k, "live"), fx, now);
resp = await _test.handle(req("/trades.json"), ENV(k, "live"));
body = await resp.json();
check("live: /trades.json serves only trades made in live mode, never dry-run history",
  resp.status === 200 && body.trades.length === 1 && body.trades[0].mode === "live");
check("live feed carries the label and the standing disclosure", /lead trader's real trades/.test(body.label) && /sometimes not at all/.test(body.disclosure));

// ---- 14. key handling ----
const pkcs8 = privateKey.export({ type: "pkcs8", format: "pem" });
let okPk = true; try { await _test.signingKey({ COINBASE_PRIVATE_KEY: pkcs8 }); } catch (_) { okPk = false; }
check("a PKCS#8 key also works", okPk);
let okEsc = true; try { await _test.signingKey({ COINBASE_PRIVATE_KEY: SEC1.replace(/\n/g, "\\n") }); } catch (_) { okEsc = false; }
check("a key pasted with literal \\n escapes works", okEsc);
const ed = crypto.generateKeyPairSync("ed25519").privateKey.export({ type: "pkcs8", format: "pem" });
let edMsg = ""; try { await _test.signingKey({ COINBASE_PRIVATE_KEY: ed }); } catch (e) { edMsg = e.message; }
check("an Ed25519 key is refused with a clear message", /ECDSA/.test(edMsg), edMsg);
const k2 = kv();
await _test.tick({ TRADES: k2, COINBASE_KEY_NAME: KEYNAME }, fx, now);
check("missing key: error recorded, nothing posted", /COINBASE_PRIVATE_KEY is not set/.test(state(k2).last_error) && !k2.m.has("events"));

console.log(`\n${res.filter(Boolean).length}/${res.length} passed`);
process.exit(res.every(Boolean) ? 0 : 1);
