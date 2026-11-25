// Tests for the ctzb-status Worker (Joe's read-only status panel, 25 Nov 2026).
// The mirror and the relay are mocked Service Bindings; the feed is this repo's real feed with its time moved.
// Run: node tests/test_status_worker.mjs
import fs from "node:fs"; import os from "node:os"; import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "ctzbstatus-")), "w.mjs");
fs.writeFileSync(tmp, fs.readFileSync(path.join(ROOT, "cloudflare/ctzb-status-worker.js"), "utf8") +
  "\nexport const _test = { status, handle, dryRunDay };\n");
const { _test, default: worker } = await import(pathToFileURL(tmp));

const res = []; const check = (n, c, d = "") => { res.push(!!c); console.log(`  ${c ? "PASS" : "*** FAIL ***"}  ${n}${d ? "  -- " + d : ""}`); };
const REAL = JSON.parse(fs.readFileSync(path.join(ROOT, "feed/ctzb_feed.json"), "utf8"));
const NOW = Date.parse("2026-11-25T20:30:00Z");
const svc = (routes) => ({ fetch: async (req) => {
  const p = new URL(req.url).pathname; const r = routes[p];
  if (r === undefined) return new Response("nf", { status: 404 });
  if (r === "throw") throw new Error("down");
  if (typeof r === "number") return new Response("x", { status: r });
  return new Response(JSON.stringify(r), { status: 200, headers: { "content-type": "application/json" } });
} });
const feedAt = (iso, extra = {}) => ({ ...JSON.parse(JSON.stringify(REAL)), generated_at: iso, ...extra });
const RELAY_OK = { ok: true, mode: "dry", baseline_at: "2026-11-24T18:00:00Z", last_ok_at: "2026-11-25T20:25:00Z", consecutive_failures: 0, last_error: null };
const env = (feed, relay) => ({ MIRROR: svc({ "/feed/ctzb_feed.json": feed }), TRADES: svc({ "/health": relay }) });
const get = async (e, p, method = "GET", now = NOW) => _test.handle(new Request("https://ctzb-status.example" + p, { method }), e, now);

// 1. running
let s = await _test.status(env(feedAt("2026-11-25T20:14:14Z"), RELAY_OK), NOW);
check("a fresh, passing feed reads as running", s.pipeline.state === "running", JSON.stringify(s.pipeline));
check("data last updated is the feed's generated_at", s.data_updated_at === "2026-11-25T20:14:14Z", s.data_updated_at);
check("forming = the feed's cards, live = its open signals", s.setups && s.setups.forming === REAL.cards.length && s.setups.live === REAL.open_signals.length,
  JSON.stringify(s.setups));
check("relay up, dry run", s.relay.state === "up" && s.relay.mode === "dry", JSON.stringify(s.relay));
check("dry run day 2 on 25 Nov", s.dry_run.day === 2 && s.dry_run.earliest_end === "2026-12-24", JSON.stringify(s.dry_run));
check("it carries the entry-quality note", /entry quality only/.test(s.note) && /not trades, fills or a track record/.test(s.note));

// 2. held
s = await _test.status(env(feedAt("2026-11-25T20:14:14Z", { cards_withheld: true, cards: [], open_signals: [] }), RELAY_OK), NOW);
check("a withheld feed reads as held, with no counts", s.pipeline.state === "held" && s.setups === null, JSON.stringify(s));
s = await _test.status(env(feedAt("2026-11-25T20:14:14Z", { cards_withheld: undefined }), RELAY_OK), NOW);
check("a feed without cards_withheld is not taken as cleared", s.pipeline.state === "held" && s.setups === null, s.pipeline.state);

// 3. late
s = await _test.status(env(feedAt("2026-11-25T15:29:00Z"), RELAY_OK), NOW);
check("no new feed for over 5 hours reads as late", s.pipeline.state === "late", s.pipeline.state);
s = await _test.status(env(feedAt("2026-11-25T15:31:00Z"), RELAY_OK), NOW);
check("...and 4h59m is still running", s.pipeline.state === "running", s.pipeline.state);

// 4. unreachable
s = await _test.status({ TRADES: svc({ "/health": RELAY_OK }) }, NOW);
check("no mirror binding: pipeline unreachable, no counts, no time", s.pipeline.state === "unreachable" && s.setups === null && s.data_updated_at === null);
s = await _test.status(env(500, RELAY_OK), NOW);
check("mirror answers 500: unreachable", s.pipeline.state === "unreachable");
s = await _test.status(env("throw", RELAY_OK), NOW);
check("mirror throws: unreachable", s.pipeline.state === "unreachable");
s = await _test.status(env(feedAt("not a date"), RELAY_OK), NOW);
check("a feed with no readable time: unreachable", s.pipeline.state === "unreachable");

// 5. relay
s = await _test.status(env(feedAt("2026-11-25T20:14:14Z"), { ...RELAY_OK, ok: false, consecutive_failures: 4, last_error: "SECRET-ERROR-TEXT 401" }), NOW);
check("relay ok:false reads as down", s.relay.state === "down", JSON.stringify(s.relay));
s = await _test.status(env(feedAt("2026-11-25T20:14:14Z"), 503), NOW);
check("relay unreachable", s.relay.state === "unreachable" && s.relay.mode === null);
s = await _test.status({ MIRROR: svc({ "/feed/ctzb_feed.json": feedAt("2026-11-25T20:14:14Z") }) }, NOW);
check("no relay binding: unreachable", s.relay.state === "unreachable");
s = await _test.status(env(feedAt("2026-11-25T20:14:14Z"), { ...RELAY_OK, ok: "yes" }), NOW);
check("relay ok must be exactly true", s.relay.state === "down");

// 6. dry-run day, New York date
const day = (iso) => _test.dryRunDay(Date.parse(iso));
check("24 Nov 00:00 ET is day 1", day("2026-11-24T05:00:00Z") === 1);
check("25 Nov 04:59 UTC is still 24 Nov in New York: day 1", day("2026-11-25T04:59:00Z") === 1);
check("25 Nov 05:00 UTC: day 2", day("2026-11-25T05:00:00Z") === 2);
check("before the start: none", day("2026-11-24T04:59:00Z") === null);
check("24 Dec (earliest end): day 31", day("2026-12-24T17:00:00Z") === 31);
check("across the DST-free winter into January: 24 Jan is day 62", day("2027-01-24T17:00:00Z") === 62);

// 7. nothing private leaks, on either route
const leakEnv = env(feedAt("2026-11-25T20:14:14Z"), { ...RELAY_OK, ok: false, last_error: "SECRET-ERROR-TEXT", baseline_at: "2026-11-24T18:00:00Z" });
const bodies = [await (await get(leakEnv, "/status.json")).text(), await (await get(leakEnv, "/")).text()];
const NOTE_RE = /Computed signals measuring entry quality only: not trades, fills or a track record\./g;
const prices = new Set();
for (const c of [...REAL.cards, ...REAL.open_signals.map((o) => o.card).filter(Boolean)]) for (const k of ["price_now", "entry_close", "must_close_above"]) if (c[k] != null) prices.add(String(c[k]));
for (const o of REAL.open_signals) if (o.entry_close != null) prices.add(String(o.entry_close));
bodies.forEach((b, i) => {
  const name = i ? "panel" : "status.json";
  check(`${name}: no relay error text, read times or baseline`, !/SECRET-ERROR-TEXT|20:25:00|2026-11-24T18/.test(b));
  check(`${name}: no price from the feed`, ![...prices].some((p) => b.includes(p)), [...prices].filter((p) => b.includes(p)).slice(0, 3).join(","));
  check(`${name}: no signal ids, grades or charts`, !REAL.open_signals.some((o) => b.includes(o.signal_id)) && !/A\+|ETH 1D|BTC 2D/.test(b));
  check(`${name}: no trade or money words`, !/balance|leverage|\$|fill(ed)?\b(?! or)|position/i.test(b.replace(NOTE_RE, "")));
});

// 8. the routes
let r = await get(env(feedAt("2026-11-25T20:14:14Z"), RELAY_OK), "/status.json");
check("/status.json: 200, JSON, CORS open, not cached", r.status === 200 && /json/.test(r.headers.get("content-type")) &&
  r.headers.get("access-control-allow-origin") === "*" && r.headers.get("cache-control") === "no-store");
r = await get(env(feedAt("2026-11-25T20:14:14Z"), RELAY_OK), "/");
const html = await r.text();
check("/: 200 HTML that may sit in any iframe and loads nothing", r.status === 200 && /text\/html/.test(r.headers.get("content-type")) &&
  /frame-ancestors \*/.test(r.headers.get("content-security-policy")) && /default-src 'none'/.test(r.headers.get("content-security-policy")) && !r.headers.get("x-frame-options"));
check("/: reloads itself every 5 minutes", /http-equiv="refresh" content="300"/.test(html));
check("/: shows running, the counts, relay up, day 2", />Running</.test(html) && new RegExp(`<b>${REAL.cards.length}</b> forming`).test(html) &&
  new RegExp(`<b>${REAL.open_signals.length}</b> live`).test(html) && />Up</.test(html) && /Day <b>2<\/b>/.test(html), "");
check("/: last update in New York time", /25 Nov 2026, 3:14 pm ET/.test(html) && /16 min ago/.test(html));
check("/: no script on the page", !/<script/i.test(html));
r = await get(env(feedAt("2026-11-25T20:14:14Z", { cards_withheld: true, cards: [], open_signals: [] }), RELAY_OK), "/");
const heldHtml = await r.text();
check("/ when held: says held, no counts", />Held</.test(heldHtml) && /Held back with the data/.test(heldHtml) && !/ forming &middot;/.test(heldHtml));
r = await get({}, "/");
check("/ with nothing reachable still renders", r.status === 200 && /Can&#39;t reach|Can't reach/.test(await r.text()));
r = await get(env(feedAt("2026-11-25T20:14:14Z"), RELAY_OK), "/status.json", "HEAD");
check("HEAD: headers, no body", r.status === 200 && (await r.text()) === "");
r = await get({}, "/status.json", "POST");
check("POST refused (read-only)", r.status === 405);
r = await get({}, "/dry");
check("any other path is 404 (no route to the relay's private page)", r.status === 404);
r = await get({}, "/status.json", "OPTIONS");
check("OPTIONS: CORS preflight", r.status === 204 && r.headers.get("access-control-allow-origin") === "*");
r = await worker.fetch(new Request("https://x/status.json"), env(feedAt(new Date().toISOString()), RELAY_OK));
check("the exported fetch answers with the wall clock", r.status === 200 && (await r.json()).pipeline.state === "running");

console.log(`\n${res.filter(Boolean).length}/${res.length} passed`);
process.exit(res.every(Boolean) ? 0 : 1);
