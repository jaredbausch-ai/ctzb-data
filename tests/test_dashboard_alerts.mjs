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
  rose10_within60d_pct: 88, rose10_never_fell25_within60d_pct: 78, rose20_within60d_pct: 61, typical_deepest_dip_pct: -10.5 };
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
check("forming message carries the card's numbers", text.startsWith("FORMING \u00b7 ETH \u00b7 2-day chart\n") && text.includes("Confirms 12 Nov 2026 if it closes above 2,124.00. It can still vanish.") && text.includes("\nTOP GRADE\n") && text.includes("88% of 33 past signals rose 10% within 60 days") && text.includes("Typical drop from entry: \u221210.5%"), JSON.stringify(text));
check("message carries the computed-signal label", text.includes("Computed signal, not a trade"));
sends = []; for (let i = 0; i < 16; i++) await _test.notify(env(k), tg);
check("16 more ticks on the same feed (a 4h feed read every 15 min): no resend", sends.length === 0);

feed = feedWith([A("confirmed")], { cards: [], prints: [{ signal_id: "ETH-2D-2026-11-12", confirms_on: "2026-11-12", entry_close: 2131.5, tags: "A + filled diamond" }] });
sends = []; await _test.notify(env(k), tg);
check("confirmed is its own alert, sent once", sends.length === 1 && sends[0].body.text.startsWith("CONFIRMED \u00b7 ETH \u00b7 2-day chart") && sends[0].body.text.includes("Entry: close 2,131.50 on 12 Nov 2026"));
feed = feedWith([A("vanished", "BTC-1D-2026-11-13", "BTC 1D")]); sends = []; await _test.notify(env(k), tg);
check("vanished alert sent", sends.length === 1 && sends[0].body.text.startsWith("VANISHED \u00b7 BTC \u00b7 1-day chart\nThe forming low didn't confirm."));

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

// 27 Nov 2026 (Jared): one plain format. Top grade = A+, no letter, no lens codes, no tags, no 25.3% or +20% figures
{ const T = (a, f) => _test.alertText(a, f);
  const oc = { rose10_within60d_pct: 71, past_trades: 38, typical_deepest_dip_pct: -13.5, sample: "all 38 past BTC 2D signals with exactly the same confirmations",
    rose10_never_fell25_within60d_pct: 63, rose20_within60d_pct: 52 };
  const open = (grade, extra = {}) => ({ signal_id: "BTC-2D-2026-11-26", grade, confirmations: "BTCX", tags: "A + filled diamond", entry_date: "2026-11-26", entry_close: 60495.57, card: { ...oc, ...extra } });
  const fc = (grade, extra) => ({ cards: [], prints: [{ signal_id: "BTC-2D-2026-11-26", confirms_on: "2026-11-26", entry_close: 60495.57, tags: "A + filled diamond" }], open_signals: [open(grade, extra)] });
  const C = A("confirmed", "BTC-2D-2026-11-26", "BTC 2D");
  let t = T(C, fc("C"));
  check("confirmed, grade C: the whole message", t === "CONFIRMED \u00b7 BTC \u00b7 2-day chart\nEntry: close 60,495.57 on 26 Nov 2026\nNot top grade\n71% of 38 past signals rose 10% within 60 days\nTypical drop from entry: \u221213.5%\n\nComputed signal, not a trade. Entry quality only.", JSON.stringify(t));
  check("no letter grade, lens code, tag, 25.3% or +20% figure anywhere", !/Grade|\bC\b|BTCX|Bucket|Tags|diamond|A \+|25\.3|63%|52%/.test(t), t);
  for (const g of ["A", "B", "C"]) check(`grade ${g} reads "Not top grade"`, T(C, fc(g)).split("\n")[2] === "Not top grade");
  t = T(C, fc("A+"));
  check("grade A+ reads TOP GRADE", t.split("\n")[2] === "TOP GRADE" && !t.includes("A+"), t);
  t = T(C, fc("B", { sample: "all 30 past signals of grade B across the ETH 1D, 2D, 3D and 5D charts (ETH 2D alone has only 9, too few to use)", past_trades: 30 }));
  check("a pooled sample says it is pooled across the asset's charts", t.includes("of 30 past BTC signals across its 1- to 5-day charts rose 10%"), t);
  t = T(C, { cards: [], prints: [{ signal_id: "BTC-2D-2026-11-26", confirms_on: "2026-11-26", entry_close: 60495.57 }], open_signals: [] });
  check("confirmed with no open signal yet: what and when only, no label or odds", t.startsWith("CONFIRMED \u00b7 BTC \u00b7 2-day chart\nEntry: close 60,495.57 on 26 Nov 2026\n\nComputed signal"), JSON.stringify(t));
  t = T(C, fc("C", { rose10_within60d_pct: null }));
  check("a card with no odds says so", t.includes("Not top grade\nOdds not available\n"), JSON.stringify(t));
  t = T(A("forming", "X", "ETH 3D"), { cards: [], prints: [], open_signals: [] });
  check("forming with no card: still says it can vanish", t === "FORMING \u00b7 ETH \u00b7 3-day chart\nNot confirmed yet. It can still vanish.\n\nComputed signal, not a trade. Entry quality only.", JSON.stringify(t));
  t = T(A("forming"), feedWith([], { cards: [{ ...card, grade: "B", must_close_above: 1459.5 }] }));
  check("forming B: Not top grade, price with a thousands separator", t.includes("if it closes above 1,459.50.") && t.includes("\nNot top grade\n"), JSON.stringify(t));
  t = T(A("forming"), feedWith([], { cards: [{ ...card, must_close_above: null }] }));
  check("forming with no price line: the date only", t.includes("Confirms 12 Nov 2026. It can still vanish."), JSON.stringify(t));
  t = T(A("vanished", "X", "ETH weekly"), feedWith([]));
  check("a chart name outside the pattern is shown as it is", t.startsWith("VANISHED \u00b7 ETH weekly\n"), t); }
// 27 Nov 2026: a second recipient (Joe) through TELEGRAM_EXTRA_CHAT_IDS
{ const env2 = (k, extra) => ({ ...env(k), TELEGRAM_EXTRA_CHAT_IDS: extra });
  let k2 = kv(); feed = feedWith([A("forming")]); sends = []; tgStatus = 200;
  let r2 = await _test.notify(env2(k2, "555666777"), tg);
  check("two recipients: each gets the alert once", sends.length === 2 && sends[0].body.chat_id === "999" && sends[1].body.chat_id === "555666777" && r2.sent === 2, JSON.stringify(sends.map((x) => x.body.chat_id)));
  check("Jared's sent-key is unchanged; Joe's has his own", k2.m.has("sent:ETH-2D-2026-11-12:forming") && k2.m.has("sent:ETH-2D-2026-11-12:forming@555666777"));
  sends = []; await _test.notify(env2(k2, "555666777"), tg);
  check("next tick: nothing resent to either", sends.length === 0);
  k2 = kv(); k2.m.set("sent:ETH-2D-2026-11-12:forming", "1"); sends = [];
  await _test.notify(env2(k2, "555666777"), tg);
  check("adding Joe later: he gets the alert, Jared doesn't get it twice", sends.length === 1 && sends[0].body.chat_id === "555666777");
  k2 = kv(); sends = [];
  const tgJoeDown = async (url, init) => { const b = JSON.parse(init.body); sends.push({ url: String(url), body: b }); return new Response("{}", { status: b.chat_id === "555666777" ? 403 : 200 }); };
  r2 = await _test.notify(env2(k2, "555666777"), tgJoeDown);
  check("Joe's send fails (he never pressed Start): Jared still gets it, Joe's is retried", r2.sent === 1 && r2.failed === 1 && k2.m.has("sent:ETH-2D-2026-11-12:forming") && !k2.m.has("sent:ETH-2D-2026-11-12:forming@555666777"));
  sends = []; await _test.notify(env2(k2, "555666777"), tgJoeDown);
  check("...and the retry goes to Joe only, never to Jared again", sends.length === 1 && sends[0].body.chat_id === "555666777");
  k2 = kv(); sends = [];
  await _test.notify(env2(k2, " 555666777 , 999, abc, 555666777, -1001234567890 "), tg);
  check("ids are trimmed; Jared's own id, duplicates and non-numbers are ignored", JSON.stringify(sends.map((x) => x.body.chat_id)) === JSON.stringify(["999", "555666777", "-1001234567890"]), JSON.stringify(sends.map((x) => x.body.chat_id)));
  k2 = kv(); sends = [];
  await _test.notify(env2(k2, ""), tg);
  check("no extra ids: Jared only, as before", sends.length === 1 && sends[0].body.chat_id === "999");
  check("the token never appears in a recipient key", ![...k2.m.keys()].some((x) => x.includes(TOKEN))); }
console.log(`\n${res.filter(Boolean).length}/${res.length} passed`);
process.exit(res.every(Boolean) ? 0 : 1);
