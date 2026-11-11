// Tests for the ctzb-dashboard Worker's Telegram alerts (item 17f).
// Telegram, the mirror and KV are all mocked. Run: node tests/test_dashboard_alerts.mjs
import fs from "node:fs"; import os from "node:os"; import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
// The deployed file exports only `default`; append a test-only export to a temp copy.
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "ctzbdash-")), "w.mjs");
fs.writeFileSync(tmp, fs.readFileSync(path.join(ROOT, "cloudflare/ctzb-dashboard-worker.js"), "utf8") +
  "\nexport const _test = { notify, alertText, tick };\n");
const { _test, default: worker } = await import(pathToFileURL(tmp));
const TOKEN = "123456:SECRET-TOKEN-xyz";
const kv = () => { const m = new Map(); return { m,
  get: async (k, o) => { const v = m.get(k); return v === undefined ? null : (o && o.type === "json" ? JSON.parse(v) : v); },
  put: async (k, v) => { m.set(k, v); } }; };
const card = { signal_id: "ETH-2D-2026-11-12", chart: "ETH 2D", low_date: "2026-11-07", confirms_on: "2026-11-12",
  must_close_above: 2124.0, grade: "A+", confirmations: "GAP + HIGH + AGREE + BTC3", past_trades: 33,
  rose10_never_fell25_within60d_pct: 78, rose20_within60d_pct: 61, typical_deepest_dip_pct: -10.5 };
const feedWith = (alerts, extra = {}) => ({ alerts_withheld: false, cards: [card], prints: [], open_signals: [], alerts, ...extra });
const A = (event, sid = "ETH-2D-2026-11-12", chart = "ETH 2D") => ({ alert_id: `${sid}:${event}`, event, signal_id: sid, chart });
let feed; const mirror = { fetch: async () => new Response(JSON.stringify(feed)) };
let sends = [], tgStatus = 200;
const tg = async (url, init) => { sends.push({ url: String(url), body: JSON.parse(init.body) }); return new Response("{}", { status: tgStatus }); };
const env = (k) => ({ MIRROR: mirror, NOTIFY: k, TELEGRAM_BOT_TOKEN: TOKEN, TELEGRAM_CHAT_ID: "999" });
const res = []; const check = (n, c, d = "") => { res.push(!!c); console.log(`  ${c ? "PASS" : "*** FAIL ***"}  ${n}${d ? "  -- " + d : ""}`); };

let k = kv(); feed = feedWith([A("forming")]); sends = [];
let r = await _test.notify(env(k), tg);
check("new alert is sent once", r.sent === 1 && sends.length === 1);
check("sent to the configured chat only", sends[0].body.chat_id === "999");
const text = sends[0].body.text;
check("forming message carries the card's numbers", text.includes("FORMING  ETH 2D") && text.includes("78% of 33") && text.includes("must close above 2124.00") && text.includes("Grade A+"), JSON.stringify(text.split("\n")[0]));
check("message carries the computed-signal label", text.includes("Computed signal, not a trade"));
sends = []; for (let i = 0; i < 16; i++) await _test.notify(env(k), tg);
check("16 more ticks on the same feed (a 4h feed read every 15 min): no resend", sends.length === 0);

feed = feedWith([A("confirmed")], { cards: [], prints: [{ signal_id: "ETH-2D-2026-11-12", confirms_on: "2026-11-12", entry_close: 2131.5, tags: "A + filled diamond" }] });
sends = []; await _test.notify(env(k), tg);
check("confirmed is its own alert, sent once", sends.length === 1 && sends[0].body.text.includes("CONFIRMED  ETH 2D") && sends[0].body.text.includes("2131.50 on 2026-11-12"));
feed = feedWith([A("vanished", "BTC-1D-2026-11-13", "BTC 1D")]); sends = []; await _test.notify(env(k), tg);
check("vanished alert sent", sends.length === 1 && sends[0].body.text.startsWith("VANISHED  BTC 1D"));

k = kv(); feed = feedWith([A("forming")], { alerts_withheld: true }); sends = [];
r = await _test.notify(env(k), tg); check("withheld feed: nothing sent", sends.length === 0 && r.skipped === "withheld");

k = kv(); feed = feedWith([A("forming")]); tgStatus = 502; sends = [];
await _test.notify(env(k), tg); check("Telegram down: not marked sent", !k.m.has("sent:ETH-2D-2026-11-12:forming"));
tgStatus = 200; await _test.notify(env(k), tg);
check("next tick retries and succeeds, still only one delivery", sends.length === 2 && k.m.has("sent:ETH-2D-2026-11-12:forming"));
const st = JSON.parse(k.m.get("status"));
check("status records the recovery", st.consecutive_failures === 0 && st.total_sent === 1);

r = await _test.notify({ MIRROR: mirror, NOTIFY: kv() }, tg);
check("no bot configured: skips quietly, no throw", r.skipped === "not configured");

const h = await worker.fetch(new Request("https://x/health", { headers: { authorization: "Basic " + Buffer.from("j:pw").toString("base64") } }),
  { GATE_MODE: "password", DASHBOARD_PASSWORD: "pw", MIRROR: { fetch: async () => new Response("{}") }, NOTIFY: k, TELEGRAM_BOT_TOKEN: TOKEN, TELEGRAM_CHAT_ID: "999" });
const hb = await h.text();
check("/health shows alert status but never the token", JSON.parse(hb).alerts.configured === true && !hb.includes("SECRET-TOKEN"));
check("token appears only in the Telegram URL", sends.every(s => s.url.includes(TOKEN) && !JSON.stringify(s.body).includes(TOKEN)));

// ---- /alerts/test ----
const B = { authorization: "Basic " + Buffer.from("j:pw").toString("base64") };
const tenv = (k2) => ({ GATE_MODE: "password", DASHBOARD_PASSWORD: "pw", MIRROR: mirror, NOTIFY: k2, TELEGRAM_BOT_TOKEN: TOKEN, TELEGRAM_CHAT_ID: "999" });
globalThis.fetch = tg; sends = []; tgStatus = 200; const k3 = kv();
let t1 = await worker.fetch(new Request("https://x/alerts/test", { method: "POST", headers: B }), tenv(k3));
check("test send works when logged in", t1.status === 200 && sends.length === 1 && sends[0].body.text.startsWith("CTZB alerts are connected"));
let t2 = await worker.fetch(new Request("https://x/alerts/test", { method: "POST", headers: B }), tenv(k3));
check("second test within 10 min is refused", t2.status === 429 && sends.length === 1);
let t3 = await worker.fetch(new Request("https://x/alerts/test", { method: "POST" }), tenv(kv()));
check("test send without login is refused", t3.status === 401 && sends.length === 1);
let t4 = await worker.fetch(new Request("https://x/alerts/test", { headers: B }), tenv(kv()));
check("GET on the test path does nothing", t4.status === 405 && sends.length === 1);
// ---- heartbeat (11 Nov 2026): the health monitor watches it ----
{ const k4 = kv(); feed = feedWith([]); tgStatus = 200;
  await _test.tick(env(k4), tg); const hb = JSON.parse(k4.m.get("heartbeat"));
  check("each tick leaves a heartbeat", hb && Date.now() - hb.at < 5000 && hb.result.sent === 0, JSON.stringify(hb));
  const k5 = kv(); await _test.tick({ ...env(k5), MIRROR: { fetch: async () => { throw new Error("down"); } } }, tg);
  check("heartbeat even when the mirror is down, with the reason", JSON.parse(k5.m.get("heartbeat")).result.skipped === "feed unreadable");
  check("heartbeat never holds the bot token", !k5.m.get("heartbeat").includes(TOKEN)); }
console.log(`\n${res.filter(Boolean).length}/${res.length} passed`);
process.exit(res.every(Boolean) ? 0 : 1);
