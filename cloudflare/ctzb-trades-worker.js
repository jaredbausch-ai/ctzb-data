// ctzb-trades — the lead trader's real trades, relayed from Coinbase (item 13a).
/*
 * Reads Jared's Coinbase futures fills with a VIEW-ONLY Coinbase (CDP) API key and turns
 * them into their own clearly labelled stream: "the lead trader's real trades". It never
 * touches the computed signals or their odds, and nothing here can place, change or move
 * anything: the key it holds can only read.
 *
 * What a trade shows: time, asset (BTC / ETH), long or short, open / add / reduce / close,
 * the fill price, leverage, and size as a percentage of the account. On a reduce or close
 * it adds the price move from the average entry and the result as a percentage of the
 * account. NEVER dollar amounts, contract counts, notional or balances (Jared's privacy
 * rule, CFTC Q7): every stored and served record is built from an allow-list of fields.
 *
 * Definitions (match how Jared describes his trades, CONTEXT.md 29 Oct):
 *   leverage   = open notional / initial margin (cross margin, so it is account-wide)
 *   size_pct   = this position's share of the initial margin / account balance x 100
 *   move_pct   = (exit price / average entry - 1) x 100, signed for the direction
 *   account_pct= realised result after fees / account balance before it x 100
 * If the account shows no initial margin, leverage is left blank and size_pct is the
 * position's notional as a share of the balance.
 *
 * MODE (plain var): "live" publishes /trades.json. Anything else, unset included, is a
 * DRY RUN: everything is computed and kept privately, nothing is public, and the gated
 * /dry page shows what would have been posted. Events record the mode they were made in,
 * so switching to live never publishes dry-run history.
 *
 * Routes: /health (public, no trade data), /trades.json (public in live mode only),
 * /dry (password gate; fails closed if DRY_VIEW_PASSWORD is unset).
 *
 * Bindings: KV `TRADES`. Secrets: COINBASE_KEY_NAME, COINBASE_PRIVATE_KEY (ECDSA, PEM),
 * DRY_VIEW_PASSWORD. Var: MODE. Cron: `* * * * *` (every minute).
 *
 * The first run takes a baseline: positions already open are recorded, not posted.
 * Every fill is de-duplicated by its entry id. Positions are reconciled against
 * Coinbase every time trades come in and every 15 minutes otherwise; a mismatch is
 * corrected and logged for review, never posted.
 */

const API = "https://api.coinbase.com";
const HOST = "api.coinbase.com";
const FILLS = "/api/v3/brokerage/orders/historical/fills";
const POSITIONS = "/api/v3/brokerage/cfm/positions";
const BALANCE = "/api/v3/brokerage/cfm/balance_summary";
const PRODUCT = "/api/v3/brokerage/products/";
const ASSETS = new Set(["BTC", "ETH"]);
const LABEL = "The lead trader's real trades. Posted automatically from his own account when they fill. Not a signal and not advice.";
const DISCLOSURE = "The lead trader trades his own account on his own judgement: sometimes before an alert, sometimes after, sometimes not at all. Every trade is posted live.";
const OVERLAP_MS = 10 * 60 * 1000;
const SEEN_CAP = 2000, EVENTS_CAP = 500, NOTES_CAP = 100, MAX_PAGES = 20, PAGE = 100;
const HEARTBEAT_MIN = 15;
const EVENT_FIELDS = ["id", "mode", "time", "asset", "instrument", "direction", "action", "price",
  "leverage", "size_pct", "reduced_pct", "move_pct", "account_pct", "held_days"];

/* ---------- encoding and the Coinbase JWT (ES256) ---------- */
const enc = new TextEncoder();
function b64url(u8) {
  let s = "";
  for (const b of u8) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
const b64json = (o) => b64url(enc.encode(JSON.stringify(o)));
const hex = (u8) => Array.from(u8, (b) => b.toString(16).padStart(2, "0")).join("");

function pemBlock(pem) {
  const text = String(pem).replace(/\\n/g, "\n");
  const m = text.match(/-----BEGIN ([A-Z ]+)-----([\s\S]*?)-----END \1-----/);
  if (!m) throw new Error("COINBASE_PRIVATE_KEY is not a PEM block");
  const raw = atob(m[2].replace(/\s+/g, ""));
  const der = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) der[i] = raw.charCodeAt(i);
  return { type: m[1], der };
}
function derLen(n) {
  if (n < 128) return [n];
  const b = [];
  while (n) { b.unshift(n & 255); n >>= 8; }
  return [0x80 | b.length, ...b];
}
const der = (tag, bytes) => [tag, ...derLen(bytes.length), ...bytes];
// AlgorithmIdentifier { id-ecPublicKey, prime256v1 }
const EC_P256 = [0x30, 0x13, 0x06, 0x07, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01,
  0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07];
// Coinbase hands out SEC1 ("EC PRIVATE KEY"); WebCrypto imports PKCS#8, so wrap it.
const sec1ToPkcs8 = (sec1) => new Uint8Array(der(0x30, [0x02, 0x01, 0x00, ...EC_P256, ...der(0x04, [...sec1])]));

async function signingKey(env) {
  if (!env.COINBASE_PRIVATE_KEY) throw new Error("COINBASE_PRIVATE_KEY is not set");
  const { type, der: body } = pemBlock(env.COINBASE_PRIVATE_KEY);
  const pkcs8 = type === "EC PRIVATE KEY" ? sec1ToPkcs8(body) : type === "PRIVATE KEY" ? body : null;
  if (!pkcs8) throw new Error(`unsupported key type "${type}": create the key with the ECDSA algorithm`);
  try {
    return await crypto.subtle.importKey("pkcs8", pkcs8, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
  } catch (_) {
    throw new Error("COINBASE_PRIVATE_KEY could not be read as an ECDSA P-256 key");
  }
}

async function makeJwt(env, key, method, path, nowSec) {
  if (!env.COINBASE_KEY_NAME) throw new Error("COINBASE_KEY_NAME is not set");
  const header = { alg: "ES256", kid: env.COINBASE_KEY_NAME, nonce: hex(crypto.getRandomValues(new Uint8Array(16))), typ: "JWT" };
  const claims = { iss: "cdp", sub: env.COINBASE_KEY_NAME, nbf: nowSec, exp: nowSec + 120, uri: `${method} ${HOST}${path}` };
  const input = `${b64json(header)}.${b64json(claims)}`;
  const sig = new Uint8Array(await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, enc.encode(input)));
  return `${input}.${b64url(sig)}`;
}

/** A GET-only Coinbase client. One fresh JWT per request, as Coinbase requires. */
function client(env, fx, now) {
  let keyP = null;
  return async function get(path, query = "") {
    keyP = keyP || signingKey(env);
    const key = await keyP;
    const jwt = await makeJwt(env, key, "GET", path, Math.floor(now() / 1000));
    const r = await fx(API + path + (query ? "?" + query : ""), {
      method: "GET", headers: { authorization: `Bearer ${jwt}`, accept: "application/json" } });
    if (!r.ok) throw new Error(`Coinbase ${path.startsWith(PRODUCT) ? PRODUCT + "{id}" : path} returned HTTP ${r.status}`);
    return r.json();
  };
}

/* ---------- numbers ---------- */
const num = (v) => { const x = parseFloat(v && typeof v === "object" ? v.value : v); return Number.isFinite(x) ? x : null; };
const r1 = (x) => (x === null || x === undefined || !Number.isFinite(x)) ? null : Math.round(x * 10) / 10;
const r2 = (x) => (x === null || x === undefined || !Number.isFinite(x)) ? null : Math.round(x * 100) / 100;
const iso = (ms) => new Date(ms).toISOString();
const minutesSince = (when, t) => (when ? (t - Date.parse(when)) / 60000 : Infinity);
const EPS = 1e-9;

/* ---------- state ---------- */
const freshState = () => ({
  v: 1, baseline_at: null, cursor_at: null, seen: [], positions: {}, products: {}, notes: [],
  last_ok_at: null, last_error: null, last_error_at: null, consecutive_failures: 0,
  last_reconcile_at: null, last_written_at: null, reconciles: 0, ignored_fills: 0 });

function note(state, t, text) {
  state.notes.unshift({ time: iso(t), text });
  state.notes.length = Math.min(state.notes.length, NOTES_CAP);
}

async function productInfo(state, get, pid) {
  if (state.products[pid]) return state.products[pid];
  const p = await get(PRODUCT + encodeURIComponent(pid));
  const fd = p.future_product_details || {};
  let asset = String(fd.contract_root_unit || p.base_currency_id || p.base_display_symbol || "").toUpperCase();
  if (!ASSETS.has(asset)) asset = /^ET/i.test(pid) ? "ETH" : /^(BI|BT)/i.test(pid) ? "BTC" : asset;
  const perp = fd.contract_expiry_type === "PERPETUAL" || /20DEC30/i.test(pid) || !!fd.perpetual_details;
  return (state.products[pid] = { asset, contract_size: num(fd.contract_size) || 1, instrument: perp ? "perp" : "future" });
}

/* ---------- reading Coinbase ---------- */
async function baseline(state, get, t) {
  const pos = (await get(POSITIONS)).positions || [];
  state.positions = {};
  for (const p of pos) {
    const info = await productInfo(state, get, p.product_id);
    if (!ASSETS.has(info.asset)) continue;
    const q = (num(p.number_of_contracts) || 0) * (p.side === "SHORT" ? -1 : 1);
    if (Math.abs(q) > EPS) state.positions[p.product_id] = { qty: q, avg: num(p.avg_entry_price), opened_at: null, entry_leverage: null, entry_size_pct: null, baseline: true };
  }
  state.baseline_at = iso(t);
  state.cursor_at = iso(t);
  state.last_reconcile_at = iso(t);
  note(state, t, `Baseline taken: ${Object.keys(state.positions).length} BTC/ETH position(s) already open. Recorded, not posted.`);
}

async function newFills(state, get) {
  const start = iso(Math.max(0, Date.parse(state.cursor_at) - OVERLAP_MS));
  const all = [];
  let cursor = "", pages = 0, batch;
  do {
    const qs = new URLSearchParams({ start_sequence_timestamp: start, limit: String(PAGE) });
    qs.append("product_types", "FUTURE");
    if (cursor) qs.set("cursor", cursor);
    const r = await get(FILLS, qs.toString());
    batch = r.fills || [];
    all.push(...batch);
    cursor = r.cursor || "";
    pages++;
  } while (cursor && batch.length >= PAGE && pages < MAX_PAGES);
  const seen = new Set(state.seen);
  const fresh = [];
  let maxT = Date.parse(state.cursor_at);
  for (const f of all) {
    const ft = Date.parse(f.trade_time || f.sequence_timestamp);
    if (Number.isFinite(ft)) maxT = Math.max(maxT, ft);
    if (!f.entry_id || seen.has(f.entry_id)) continue;
    seen.add(f.entry_id);
    state.seen.push(f.entry_id);
    if ((f.trade_type || "FILL") !== "FILL") { state.flagged_adjustment = (state.flagged_adjustment || 0) + 1; fresh.adjusted = true; continue; }
    fresh.push(f);
  }
  if (state.seen.length > SEEN_CAP) state.seen = state.seen.slice(-SEEN_CAP);
  state.cursor_at = iso(maxT);
  fresh.sort((a, b) => Date.parse(a.trade_time) - Date.parse(b.trade_time) || String(a.entry_id).localeCompare(String(b.entry_id)));
  return fresh;
}

/** Fills of the same order in one read become one trade, at their volume-weighted price. */
function groupOrders(fills) {
  const orders = [], byId = new Map();
  for (const f of fills) {
    const k = f.order_id || f.entry_id;
    let o = byId.get(k);
    if (!o) { o = { id: f.entry_id, product: f.product_id, side: f.side, contracts: 0, pxq: 0, fee: 0, time: f.trade_time }; byId.set(k, o); orders.push(o); }
    const s = num(f.size) || 0, p = num(f.price) || 0;
    o.contracts += s; o.pxq += s * p; o.fee += num(f.commission) || 0;
    if (Date.parse(f.trade_time) > Date.parse(o.time)) o.time = f.trade_time;
  }
  for (const o of orders) o.price = o.contracts ? o.pxq / o.contracts : 0;
  return orders;
}

/** Apply one order to the tracked position. Returns raw events (dollar fields kept internal). */
function applyOrder(state, o, info, mode) {
  const sgn = o.side === "SELL" ? -1 : 1;
  const q = o.contracts * sgn;
  const pos = state.positions[o.product] || { qty: 0, avg: 0, opened_at: null, entry_leverage: null, entry_size_pct: null };
  const prev = pos.qty, next = prev + q;
  const base = { mode, time: o.time, asset: info.asset, instrument: info.instrument, price: o.price, product: o.product };
  const out = [];
  const close = (qtyClosed, action) => {
    const dir = Math.sign(prev);
    const feeShare = o.fee * (qtyClosed / Math.abs(q));
    out.push({ ...base, id: `${o.id}:${action}`, action, direction: dir > 0 ? "long" : "short",
      reduced_pct: action === "reduce" ? (qtyClosed / Math.abs(prev)) * 100 : null,
      move_pct: pos.avg ? (o.price / pos.avg - 1) * 100 * dir : null,
      _realized: (o.price - pos.avg) * dir * qtyClosed * info.contract_size - feeShare,
      _entry_leverage: pos.entry_leverage, _entry_size_pct: pos.entry_size_pct,
      held_days: pos.opened_at ? (Date.parse(o.time) - Date.parse(pos.opened_at)) / 86400000 : null });
  };
  if (Math.abs(prev) < EPS) {
    out.push({ ...base, id: `${o.id}:open`, action: "open", direction: sgn > 0 ? "long" : "short" });
    state.positions[o.product] = { qty: next, avg: o.price, opened_at: o.time, entry_leverage: null, entry_size_pct: null };
  } else if (Math.sign(prev) === sgn) {
    out.push({ ...base, id: `${o.id}:add`, action: "add", direction: sgn > 0 ? "long" : "short" });
    pos.avg = (Math.abs(prev) * pos.avg + Math.abs(q) * o.price) / Math.abs(next);
    pos.qty = next;
    state.positions[o.product] = pos;
  } else if (Math.abs(q) < Math.abs(prev) - EPS) {
    close(Math.abs(q), "reduce");
    pos.qty = next;
    state.positions[o.product] = pos;
  } else {
    close(Math.abs(prev), "close");
    delete state.positions[o.product];
    if (Math.abs(next) > EPS) {   // flipped through zero: the rest opens the other way
      out.push({ ...base, id: `${o.id}:open`, action: "open", direction: sgn > 0 ? "long" : "short" });
      state.positions[o.product] = { qty: next, avg: o.price, opened_at: o.time, entry_leverage: null, entry_size_pct: null };
    }
  }
  return out;
}

/** Measure leverage and size from the account as it stands after the fills, then reconcile. */
async function measureAndReconcile(state, get, t, raw) {
  const [bsr, pr] = [await get(BALANCE), await get(POSITIONS)];
  const bs = bsr.balance_summary || {};
  const balance = num(bs.total_usd_balance);
  const margin = num(bs.initial_margin);
  const live = {};
  let total = 0;
  for (const p of pr.positions || []) {
    const info = await productInfo(state, get, p.product_id);
    if (!ASSETS.has(info.asset)) continue;
    const contracts = num(p.number_of_contracts) || 0;
    const notional = contracts * (num(p.current_price) || 0) * info.contract_size;
    live[p.product_id] = { qty: contracts * (p.side === "SHORT" ? -1 : 1), avg: num(p.avg_entry_price), notional };
    total += notional;
  }
  const leverage = margin > 0 ? total / margin : null;
  const sizePct = (pid) => {
    const n = live[pid] ? live[pid].notional : 0;
    if (!n || !balance) return null;
    return margin > 0 ? (margin * (n / total)) / balance * 100 : n / balance * 100;
  };
  const realizedNow = raw.reduce((s, e) => s + (e._realized || 0), 0);
  const balanceBefore = balance !== null ? balance - realizedNow : null;
  for (const e of raw) {
    if (e.action === "open" || e.action === "add") {
      e.leverage = leverage;
      e.size_pct = sizePct(e.product);
      const pos = state.positions[e.product];
      if (pos) { pos.entry_leverage = e.leverage; pos.entry_size_pct = e.size_pct; }
    } else {
      e.leverage = e._entry_leverage;
      e.size_pct = e._entry_size_pct;
      e.account_pct = balanceBefore ? (e._realized / balanceBefore) * 100 : null;
    }
  }
  // Reconcile: Coinbase's positions are the truth. Correct and log; never post.
  const pids = new Set([...Object.keys(state.positions), ...Object.keys(live)]);
  for (const pid of pids) {
    const mine = state.positions[pid] ? state.positions[pid].qty : 0;
    const theirs = live[pid] ? live[pid].qty : 0;
    if (Math.abs(mine - theirs) > 1e-6) {
      state.reconciles++;
      note(state, t, `Reconciled ${pid}: tracked ${r2(mine)} contracts, Coinbase shows ${r2(theirs)}. Corrected; nothing posted.`);
      if (Math.abs(theirs) > EPS) {
        state.positions[pid] = { ...(state.positions[pid] || { opened_at: null, entry_leverage: null, entry_size_pct: null }), qty: theirs, avg: live[pid].avg };
      } else delete state.positions[pid];
    }
  }
  state.last_reconcile_at = iso(t);
}

/** The only shape that is ever stored or served: an allow-list, rounded. */
function publicEvent(e) {
  const o = {};
  for (const k of EVENT_FIELDS) {
    let v = e[k];
    if (v === undefined) continue;
    if (k === "price") v = r2(v);
    else if (["leverage", "size_pct", "reduced_pct", "move_pct", "account_pct", "held_days"].includes(k)) v = r1(v);
    if (v !== null) o[k] = v;
  }
  return o;
}

async function appendEvents(kv, events) {
  const cur = (await kv.get("events", { type: "json" })) || [];
  const ids = new Set(cur.map((e) => e.id));
  const add = events.filter((e) => !ids.has(e.id));
  if (!add.length) return 0;
  const next = [...add.reverse(), ...cur].slice(0, EVENTS_CAP);
  await kv.put("events", JSON.stringify(next));
  return add.length;
}

/* ---------- one cron tick ---------- */
const VOLATILE = ["last_ok_at", "last_error_at", "consecutive_failures", "last_written_at"];
const comparable = (s) => JSON.stringify(s, (k, v) => (VOLATILE.includes(k) ? undefined : v));

async function tick(env, fx = fetch, now = () => Date.now()) {
  const kv = env.TRADES;
  if (!kv) throw new Error("KV binding TRADES is missing");
  const t = now();
  const state = { ...freshState(), ...((await kv.get("state", { type: "json" })) || {}) };
  const was = comparable(state);
  const mode = env.MODE === "live" ? "live" : "dry";
  let posted = 0;
  try {
    const get = client(env, fx, now);
    if (!state.baseline_at) {
      await baseline(state, get, t);
    } else {
      const fills = await newFills(state, get);
      if (fills.adjusted) note(state, t, "Coinbase reported an adjusted fill (reversal or correction). Not posted; positions reconciled.");
      const raw = [];
      for (const o of groupOrders(fills)) {
        const info = await productInfo(state, get, o.product);
        if (!ASSETS.has(info.asset)) { state.ignored_fills++; continue; }
        raw.push(...applyOrder(state, o, info, mode));
      }
      if (raw.length || fills.adjusted || minutesSince(state.last_reconcile_at, t) >= HEARTBEAT_MIN) {
        await measureAndReconcile(state, get, t, raw);
      }
      if (raw.length) posted = await appendEvents(kv, raw.map(publicEvent));
    }
    state.last_ok_at = iso(t);
    state.consecutive_failures = 0;
    state.last_error = null;
  } catch (e) {
    state.consecutive_failures++;
    state.last_error = String((e && e.message) || e).slice(0, 200);
    state.last_error_at = iso(t);
  }
  if (comparable(state) !== was || minutesSince(state.last_written_at, t) >= HEARTBEAT_MIN) {
    state.last_written_at = iso(t);
    await kv.put("state", JSON.stringify(state));
  }
  return { posted, state };
}

/* ---------- HTTP ---------- */
async function sameSecret(a, b) {
  const [x, y] = await Promise.all([crypto.subtle.digest("SHA-256", enc.encode(a)), crypto.subtle.digest("SHA-256", enc.encode(b))]);
  const u = new Uint8Array(x), v = new Uint8Array(y);
  let diff = 0;
  for (let i = 0; i < u.length; i++) diff |= u[i] ^ v[i];
  return diff === 0;
}
async function gateOk(req, env) {
  if (!env.DRY_VIEW_PASSWORD) return false;
  const h = req.headers.get("authorization") || "";
  if (!h.startsWith("Basic ")) return false;
  let d = "";
  try { d = atob(h.slice(6)); } catch (_) { return false; }
  return sameSecret(d.slice(d.indexOf(":") + 1), env.DRY_VIEW_PASSWORD);
}
const json = (body, status = 200, extra = {}) => new Response(JSON.stringify(body, null, 2), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });

async function handle(req, env) {
  const url = new URL(req.url);
  if (req.method !== "GET") return json({ error: "GET only" }, 405);
  const kv = env.TRADES;
  const state = kv ? ((await kv.get("state", { type: "json" })) || freshState()) : freshState();
  const mode = env.MODE === "live" ? "live" : "dry";
  if (url.pathname === "/health") {
    const fresh = minutesSince(state.last_ok_at, Date.now()) < 10;
    return json({ ok: !!kv && fresh && !state.consecutive_failures, mode, baseline_at: state.baseline_at,
      last_ok_at: state.last_ok_at, consecutive_failures: state.consecutive_failures, last_error: state.last_error });
  }
  if (url.pathname === "/trades.json") {
    if (mode !== "live") return json({ error: "Not live yet: dry run." }, 404);
    const events = ((kv && (await kv.get("events", { type: "json" }))) || []).filter((e) => e.mode === "live");
    return json({ label: LABEL, disclosure: DISCLOSURE, updated_at: state.last_ok_at, trades: events }, 200,
      { "access-control-allow-origin": "*" });
  }
  if (url.pathname === "/dry") {
    if (!env.DRY_VIEW_PASSWORD) return json({ error: "Dry-run view not configured" }, 503);
    if (!(await gateOk(req, env))) return json({ error: "Login required" }, 401, { "www-authenticate": 'Basic realm="ctzb-trades dry run", charset="UTF-8"' });
    const events = (kv && (await kv.get("events", { type: "json" }))) || [];
    const open = Object.entries(state.positions || {}).map(([pid, p]) => ({
      product: pid, direction: p.qty > 0 ? "long" : "short", avg_entry: r2(p.avg), leverage: r1(p.entry_leverage),
      size_pct: r1(p.entry_size_pct), opened_at: p.opened_at, from_baseline: !!p.baseline }));
    return json({ mode, label: LABEL, disclosure: DISCLOSURE, note: "Dry run: this is what would be posted. Nothing here is public.",
      health: { last_ok_at: state.last_ok_at, consecutive_failures: state.consecutive_failures, last_error: state.last_error,
        reconciles: state.reconciles, ignored_fills: state.ignored_fills, baseline_at: state.baseline_at },
      open_positions: open, trades: events, review_notes: state.notes || [] });
  }
  return json({ error: "Not found" }, 404);
}

export default {
  async scheduled(_event, env, ctx) { ctx.waitUntil(tick(env)); },
  async fetch(req, env) { return handle(req, env); },
};
