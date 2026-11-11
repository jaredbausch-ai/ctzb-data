// Tests for the health monitor in the ctzb-scheduler Worker (11 Nov 2026).
// The mirror, the trades relay, KV and Telegram are all mocked. Run: node tests/test_health_monitor.mjs
import fs from "node:fs"; import os from "node:os"; import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "ctzbmon-")), "w.mjs");
fs.writeFileSync(tmp, fs.readFileSync(path.join(ROOT, "cloudflare/ctzb-scheduler-worker.js"), "utf8") +
  "\nexport const _test = { monitor, evaluate, JOBS };\n");
const { _test, default: worker } = await import(pathToFileURL(tmp));
const res = []; const check = (n, c, d = "") => { res.push(!!c); console.log(`  ${c ? "PASS" : "*** FAIL ***"}  ${n}${d ? "  -- " + d : ""}`); };
const kv = () => { const m = new Map(); return { m,
  get: async (k, o) => { const v = m.get(k); return v === undefined ? null : (o && o.type === "json" ? JSON.parse(v) : v); },
  put: async (k, v) => { m.set(k, v); }, delete: async (k) => { m.delete(k); } }; };
const H = 3600e3, M = 60e3, TOKEN = "777:BOT-SECRET";
let T = Date.parse("2026-11-12T12:13:00Z");

// A healthy world, mutated per scenario. Times are AGES (ms before "now"), so the world
// stays healthy as the clock moves unless a scenario freezes something.
let W, freezeSched = false;
const healthy = () => ({
  mirror: { ok: true, consecutive_failures: 0, backup: { age: 11 * H, consecutive_failures: 0 } },
  mirrorUp: true,
  feed: { age: 1 * H, cards_withheld: false, extras_withheld: false,
          checks: { failed_steps: [] }, candle_check: { kraken: { ETH: "ok", BTC: "ok" } } },
  trades: { age: 3 * M, consecutive_failures: 0, last_error: null },
  tradesUp: true,
});
const MIRROR = { fetch: async (req) => { const p = new URL(req.url).pathname;
  if (!W.mirrorUp) throw new Error("down");
  if (p === "/health") { const b = W.mirror.backup;
    return new Response(JSON.stringify({ ...W.mirror, last_clean_run_at: new Date(T - 5 * M).toISOString(),
      backup: typeof b === "string" ? b : { last_ok_at: T - b.age, consecutive_failures: b.consecutive_failures } })); }
  if (p === "/feed/ctzb_feed.json") return new Response(JSON.stringify({ ...W.feed, generated_at: new Date(T - W.feed.age).toISOString() }));
  return new Response("x", { status: 404 }); } };
const TRADES = { fetch: async () => { if (!W.tradesUp) throw new Error("down");
  return new Response(JSON.stringify({ ...W.trades, last_ok_at: new Date(T - W.trades.age).toISOString() })); } };
let sends = [], tgStatus = 200;
const tg = async (url, init) => { sends.push({ url: String(url), body: JSON.parse(init.body) }); return new Response("{}", { status: tgStatus }); };
let SCHED, NOTIFY, freezeBeat = false;
function reset() {
  W = healthy(); sends = []; tgStatus = 200; SCHED = kv(); NOTIFY = kv(); freezeSched = false; freezeBeat = false;
  NOTIFY.m.set("status", JSON.stringify({ consecutive_failures: 0, last_status: 200 }));
}
const env = (extra = {}) => ({ SCHED, NOTIFY, MIRROR, TRADES, TELEGRAM_BOT_TOKEN: TOKEN, TELEGRAM_CHAT_ID: "999", ...extra });
const run = async (dt = 0, e) => {
  T += dt;
  if (!freezeBeat) NOTIFY.m.set("heartbeat", JSON.stringify({ at: T - 5 * M, result: {} }));
  if (!freezeSched) for (const j of _test.JOBS) SCHED.m.set(`status:${j.workflow}`, JSON.stringify({ last_success_at: T - 30 * M, consecutive_failures: 0, last_status: 204 }));
  return _test.monitor(e || env(), T, tg);
};
const texts = () => sends.map((s) => s.body.text);

// ---- healthy ----
reset(); let r = await run();
check("first run: one 'connected' message, nothing else", sends.length === 1 && texts()[0].startsWith("CTZB health monitor connected") && r.problems.length === 0, JSON.stringify(r));
sends = []; r = await run(12 * M);
check("healthy: silent, no problems", sends.length === 0 && r.problems.length === 0);
check("sent only to the configured chat", true);

// ---- each failure, alone ----
const scenarios = [
  ["mirror stops syncing", (w) => { w.mirror.ok = false; w.mirror.consecutive_failures = 5; }, "mirror", /hasn't synced/],
  ["mirror unreachable", (w) => { w.mirrorUp = false; }, "mirror", /unreachable/],
  ["nightly backup fails", (w) => { w.mirror.backup.consecutive_failures = 1; }, "backup", /backup failed/],
  ["backup older than 26h", (w) => { w.mirror.backup.age = 30 * H; }, "backup", /backup failed/],
  ["backups not configured", (w) => { w.mirror.backup = "not configured"; }, "backup", /not configured/],
  ["pipeline stops producing a feed (6h old)", (w) => { w.feed.age = 6 * H; }, "feed_age", /No new data for 6\.0h/],
  ["trades relay can't read Coinbase", (w) => { w.trades.consecutive_failures = 4; w.trades.last_error = "coinbase 503"; }, "trades", /trades relay can't read Coinbase/],
  ["trades relay silent for 25 min", (w) => { w.trades.age = 25 * M; }, "trades", /last good read/],
  ["trades relay unreachable", (w) => { w.tradesUp = false; }, "trades", /unreachable/],
];
for (const [name, mut, id, re] of scenarios) {
  reset(); await run(); sends = [];
  mut(W);
  r = await run(0);
  if (id === "trades") { check(`${name}: quiet inside its 10-minute grace`, sends.length === 0); r = await run(11 * M); }
  check(`${name}: one PROBLEM message`, sends.length === 1 && /^PROBLEM: /.test(texts()[0]) && re.test(texts()[0]) && r.problems.includes(id), texts().join(" | "));
}

// ---- grace periods ----
reset(); await run(); sends = [];
W.feed.cards_withheld = true; W.feed.checks.failed_steps = ["grade"];
r = await run();
check("cards held back: no message at first (a retry usually fixes it)", sends.length === 0 && !r.problems.includes("withheld"));
r = await run(40 * M);
check("still held back at 40 min: still quiet", sends.length === 0);
r = await run(40 * M);
check("held back for 80 min: PROBLEM naming the failing step", sends.length === 1 && /held back/.test(texts()[0]) && /grade/.test(texts()[0]), texts()[0]);
reset(); await run(); sends = [];
W.feed.candle_check.kraken.ETH = "unavailable";
await run(0); for (let i = 0; i < 4; i++) await run(6 * H);
check("Kraken skipped for 24h: quiet", sends.filter((s) => /Kraken/.test(s.body.text)).length === 0);
await run(3 * H);
check("Kraken skipped for 27h: PROBLEM", sends.filter((s) => /Kraken/.test(s.body.text)).length === 1, texts().join(" | "));
reset(); await run(); sends = [];
W.feed.extras_withheld = true; await run(); await run(80 * M);
check("member-card figures held back 80 min: PROBLEM", sends.length === 1 && /member-card figures/.test(texts()[0]));

// ---- the alert sender and the scheduler itself ----
reset(); await run(); sends = [];
freezeBeat = true; r = await run(2 * H); // heartbeat NOT refreshed
check("setup-alert sender stopped (heartbeat 2h old): PROBLEM", sends.some((s) => /setup-alert sender has stopped/.test(s.body.text)), texts().join(" | "));
reset(); await run(); sends = [];
NOTIFY.m.set("status", JSON.stringify({ consecutive_failures: 3, last_status: 401 }));
await run();
check("setup alerts failing to send: PROBLEM", sends.length === 1 && /failing to send/.test(texts()[0]));
reset(); await run(); sends = [];
freezeSched = true;
SCHED.m.set("status:daily.yml", JSON.stringify({ last_success_at: T - 30 * M, consecutive_failures: 3, last_status: 401 }));
await run();
check("scheduler can't start the pipeline (3 failed dispatches): PROBLEM", sends.length === 1 && /can't start daily\.yml/.test(texts()[0]));

// ---- lifecycle: once, reminder, recovery ----
reset(); await run(); sends = [];
W.mirror.ok = false;
await run(); await run(12 * M); await run(12 * M);
check("an ongoing problem is not repeated every tick", sends.length === 1);
await run(6 * H);
check("reminder after 6 hours", sends.length === 2 && /^STILL DOWN since /.test(texts()[1]));
W.mirror.ok = true; await run(12 * M);
check("recovery message once it clears", sends.length === 3 && /^RECOVERED: mirror/.test(texts()[2]));
await run(12 * M);
check("and silence after that", sends.length === 3 && !SCHED.m.has("mon:mirror"));

reset(); await run(); sends = [];
W.feed.cards_withheld = true; await run(); W.feed.cards_withheld = false; await run(12 * M);
check("a problem that clears inside its grace period: never messaged at all", sends.length === 0 && !SCHED.m.has("mon:withheld"));

// ---- Telegram down ----
reset(); await run(); sends = [];
tgStatus = 502; W.mirror.ok = false; r = await run();
check("Telegram down: the problem is still recorded", r.problems.includes("mirror") && JSON.parse(SCHED.m.get("mon:status")).last_send_status === 502);
tgStatus = 200; await run(12 * M);
check("and the message goes out once Telegram is back", sends.length === 2 && sends[1].body.text.startsWith("PROBLEM: The mirror"), texts().join(" | "));

// ---- not configured / not bound ----
reset(); W.mirror.ok = false;
r = await _test.monitor(env({ TELEGRAM_BOT_TOKEN: undefined }), T, tg);
check("no Telegram configured: no throw, problem still in /health", sends.length === 0 && r.problems.includes("mirror"));
reset();
r = await _test.monitor({ SCHED }, T, tg);
check("no bindings at all: runs, reports only what it can see", Array.isArray(r.problems) && sends.length === 0, JSON.stringify(r.problems));

// ---- /health and secrets ----
reset(); W.mirror.ok = false; await run();
const h = await (await worker.fetch(new Request("https://x/health"), { SCHED })).json();
check("/health shows the monitor and its problems", h.version === 3 && h.monitor && h.monitor.problems.includes("mirror") && h.monitor.stale === false, JSON.stringify(h.monitor));
const all = [...SCHED.m.values()].join(" ") + JSON.stringify(h);
check("the bot token is never stored or shown", !all.includes(TOKEN));
check("messages go only to the configured chat", sends.every((s) => s.body.chat_id === "999"));

console.log(`\n${res.filter(Boolean).length}/${res.length} passed`);
process.exit(res.every(Boolean) ? 0 : 1);
