/**
 * ctzb-status — Joe's read-only status panel (25 Nov 2026).
 *
 * Joe asked (24 Nov) for a small module on his dashboard showing ETHKROS status at a glance. Two routes:
 *   /             a small HTML panel, made to sit in an iframe; it reloads itself every 5 minutes
 *   /status.json  the same figures as JSON, for his developer to wire in directly (CORS open)
 * Everything else is 404. GET, HEAD and OPTIONS only.
 *
 * What it shows, and nothing else:
 *   - the pipeline: running, held (a data check failed, the site withholds its cards), late (no new feed for
 *     FEED_LATE_H hours) or unreachable
 *   - when the data last updated (the feed's generated_at)
 *   - how many setups are forming (feed cards[]) and live (feed open_signals[]: confirmed in the last 60 days,
 *     every grade, ETH and BTC 1D to 5D); none while the feed is held
 *   - the lead-trader relay: up or down, and its mode (dry run)
 *   - the day of the private dry run (from 24 Nov 2026, New York date)
 * No trades, prices, balances, keys, error texts or account details. The relay's /health is read for its ok flag
 * and mode only.
 *
 * Bindings (set in the dashboard, Settings -> Bindings), both Service Bindings:
 *   MIRROR -> ctzb-feed    (the feed)
 *   TRADES -> ctzb-trades  (the relay's /health)
 * No secrets, no KV, no cron.
 *
 * Every figure on it is a computed signal measuring entry quality only: not a trade, a fill or a track record.
 */

const DRY_RUN_START = '2026-11-24';
const DRY_RUN_EARLIEST_END = '2026-12-24';
const DRY_RUN_LATEST_END = '2027-01-24';
const FEED_LATE_H = 5;          // as the health monitor: the normal gap is 4 hours
const REFRESH_S = 300;
const TZ = 'America/New_York';
const NOTE = 'Computed signals measuring entry quality only: not trades, fills or a track record.';
const H = 3600 * 1000;

const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-methods': 'GET, HEAD, OPTIONS', 'access-control-max-age': '86400' };

async function svcJSON(svc, path) {
  if (!svc || typeof svc.fetch !== 'function') return null;
  try {
    const r = await svc.fetch(new Request('https://svc' + path));
    if (!r.ok) return null;
    return await r.json();
  } catch (_) {
    return null;
  }
}

/** New York calendar date of a moment, YYYY-MM-DD. */
function nyDate(ms) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(ms));
}

function dryRunDay(now) {
  const [y, m, d] = nyDate(now).split('-').map(Number);
  const [sy, sm, sd] = DRY_RUN_START.split('-').map(Number);
  const day = Math.round((Date.UTC(y, m - 1, d) - Date.UTC(sy, sm - 1, sd)) / 86400000) + 1;
  return day >= 1 ? day : null;
}

/** Every figure the panel shows, worked out now. */
async function status(env, now) {
  const feed = await svcJSON(env.MIRROR, '/feed/ctzb_feed.json');
  const relay = await svcJSON(env.TRADES, '/health');

  const gen = feed && typeof feed.generated_at === 'string' ? Date.parse(feed.generated_at) : NaN;
  let pipeline;
  if (!feed || !Number.isFinite(gen)) {
    pipeline = { state: 'unreachable', text: "The status panel can't read the feed right now." };
  } else if (feed.cards_withheld !== false) {
    pipeline = { state: 'held', text: 'A data check failed, so the site is holding back its setups until a run passes. This is the system working as designed.' };
  } else if (now - gen > FEED_LATE_H * H) {
    pipeline = { state: 'late', text: `No new data for over ${FEED_LATE_H} hours. Jared gets an alert when this happens.` };
  } else {
    pipeline = { state: 'running', text: 'Every check passed on the last run. Data updates every 4 hours.' };
  }

  const counted = feed && feed.cards_withheld === false && Array.isArray(feed.cards) && Array.isArray(feed.open_signals);
  const setups = counted ? { forming: feed.cards.length, live: feed.open_signals.length } : null;

  let rel;
  if (!relay) rel = { state: 'unreachable', mode: null };
  else rel = { state: relay.ok === true ? 'up' : 'down', mode: relay.mode === 'live' ? 'live' : 'dry' };

  const day = dryRunDay(now);
  return {
    as_of: new Date(now).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    pipeline,
    data_updated_at: Number.isFinite(gen) ? new Date(gen).toISOString().replace(/\.\d{3}Z$/, 'Z') : null,
    setups,
    setups_note: 'Forming: lows waiting to confirm. Live: confirmed in the last 60 days, every grade, ETH and BTC 1D to 5D.',
    relay: rel,
    dry_run: { started: DRY_RUN_START, day, earliest_end: DRY_RUN_EARLIEST_END, latest_planned_end: DRY_RUN_LATEST_END },
    note: NOTE,
  };
}

// ---------- the panel ----------

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function nyTime(ms, withDate = true) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-US', { timeZone: TZ, year: 'numeric', month: 'numeric', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true }).formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
  const t = `${p.hour}:${p.minute} ${String(p.dayPeriod || '').toLowerCase()} ET`;
  return withDate ? `${p.day} ${MONTHS[Number(p.month) - 1]} ${p.year}, ${t}` : t;
}
const longDate = (iso) => { const [y, m, d] = iso.split('-').map(Number); return `${d} ${MONTHS[m - 1]} ${y}`; };
function ago(ms, now) {
  const m = Math.max(0, Math.round((now - ms) / 60000));
  if (m < 60) return `${m} min ago`;
  return `${(m / 60).toFixed(1)} h ago`;
}

const LABEL = { running: 'Running', held: 'Held', late: 'Late', unreachable: "Can't reach", up: 'Up', down: 'Down' };

function panel(s, now) {
  const pill = (state) => `<span class="pill ${esc(state)}">${esc(LABEL[state] || state)}</span>`;
  const upd = s.data_updated_at ? `${esc(nyTime(Date.parse(s.data_updated_at)))} <span class="dim">(${esc(ago(Date.parse(s.data_updated_at), now))})</span>` : '<span class="dim">Not available</span>';
  const setups = s.setups
    ? `<b>${s.setups.forming}</b> forming &middot; <b>${s.setups.live}</b> live`
    : `<span class="dim">${s.pipeline.state === 'held' ? 'Held back with the data' : 'Not available'}</span>`;
  const relay = s.relay.state === 'unreachable' ? pill('unreachable')
    : `${pill(s.relay.state)} <span class="dim">${s.relay.mode === 'live' ? 'live: publishing the lead trader’s trades' : 'dry run: private, nothing published'}</span>`;
  const dry = s.dry_run.day ? `Day <b>${s.dry_run.day}</b> <span class="dim">&middot; started ${esc(longDate(s.dry_run.started))}, earliest end ${esc(longDate(s.dry_run.earliest_end))}</span>` : '<span class="dim">Not started</span>';
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="${REFRESH_S}"><title>ETHKROS status</title>
<style>
:root{--bg:#07060F;--panel:#110E22;--line:#2B2350;--text:#F4F1FF;--soft:#D6D1F0;--muted:#A9A3C9;--ok:#2DE2E6;--warn:#FFC857;--bad:#FF6AC1}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--text);font:14px/1.45 Inter,system-ui,-apple-system,"Segoe UI",sans-serif;padding:12px}
.card{max-width:520px;border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:16px 18px}
h1{font-size:13px;letter-spacing:3px;color:var(--soft);font-weight:600;text-transform:uppercase;margin-bottom:10px}
.row{display:grid;grid-template-columns:150px 1fr;gap:10px;padding:9px 0;border-top:1px solid var(--line)}
.k{color:var(--muted)}
.why{color:var(--muted);font-size:13px;margin-top:3px}
.dim{color:var(--muted)}
.pill{display:inline-block;padding:1px 9px;border-radius:999px;font-weight:700;font-size:13px;border:1px solid}
.running,.up{color:var(--ok);border-color:#1F5560;background:#0C1E24}
.held,.late{color:var(--warn);border-color:#5c4a1c;background:#1f1a0b}
.unreachable,.down{color:var(--bad);border-color:#6a2850;background:#22101e}
.foot{color:var(--muted);font-size:12px;margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}
@media (max-width:420px){.row{grid-template-columns:1fr;gap:2px}}
</style></head><body>
<div class="card">
<h1>ETHKROS status</h1>
<div class="row"><div class="k">Pipeline</div><div>${pill(s.pipeline.state)}<div class="why">${esc(s.pipeline.text)}</div></div></div>
<div class="row"><div class="k">Data last updated</div><div>${upd}</div></div>
<div class="row"><div class="k">Setups</div><div>${setups}<div class="why">${esc(s.setups_note)}</div></div></div>
<div class="row"><div class="k">Lead-trader relay</div><div>${relay}</div></div>
<div class="row"><div class="k">Private dry run</div><div>${dry}</div></div>
<div class="foot">${esc(s.note)} Checked ${esc(nyTime(now, false))}; refreshes every 5 minutes.</div>
</div>
</body></html>`;
}

async function handle(request, env, now = Date.now()) {
  const { pathname } = new URL(request.url);
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return new Response('read-only', { status: 405, headers: { 'content-type': 'text/plain; charset=utf-8', ...CORS } });
  }
  const head = request.method === 'HEAD';
  if (pathname === '/status.json') {
    const s = await status(env, now);
    return new Response(head ? null : JSON.stringify(s, null, 2), {
      headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...CORS } });
  }
  if (pathname === '/' || pathname === '') {
    const s = await status(env, now);
    return new Response(head ? null : panel(s, now), {
      headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store',
        'content-security-policy': "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors *", 'referrer-policy': 'no-referrer' } });
  }
  return new Response('not found', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8', ...CORS } });
}

export default {
  async fetch(request, env) {
    return handle(request, env);
  },
};
