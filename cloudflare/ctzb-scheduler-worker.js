/**
 * CTZB external scheduler — v2, 10 Nov 2026.
 *
 * GitHub's cron honoured roughly one tick in three on this repo (22 Oct - 4 Nov
 * 2026) and about one in eleven on 10 Nov. This Worker is now the clock. On its
 * first 15.5 hours, v1 fired 32 of 32 ticks.
 *
 * ONE cron trigger fires at 13, 25, 35 and 43 past every hour. The table below
 * decides what, if anything, each tick dispatches. Ticks that match nothing do
 * nothing and write nothing.
 *
 *   daily.yml     :13 and :43 after each 4-hour close (00,04,08,12,16,20 UTC)
 *                 sent with scheduled=true so the workflow's gate skips the :43
 *                 backup when the :13 run already landed the candle.   12/day
 *   watchdog.yml  :35 one hour after each close = 95 min after the close,
 *                 when a still-missing candle means everything else failed.  6/day
 *   pcr.yml       :25 every 3 hours. The watchdog calls put/call stale at 9h.  8/day
 *
 * KV: one write per dispatch, about 26 a day.
 *
 * Bindings required:
 *   SCHED                  KV namespace (binding name must be exactly SCHED)
 *   GITHUB_DISPATCH_TOKEN  secret: fine-grained PAT, Actions: read+write,
 *                          this repo only. NOT the mirror's read-only token.
 *
 * Cron trigger (exactly one): 13,25,35,43 * * * *
 *
 * HEALTH MONITOR (v3, 11 Nov 2026). Every tick also checks everything that can go down
 * without anything else noticing, and messages Jared on Telegram when a problem starts,
 * every 6 hours while it lasts, and when it clears. Optional bindings -- without them the
 * monitor still runs and reports in /health, it just can't reach that part or send:
 *   MIRROR                 Service Binding -> ctzb-feed   (mirror sync, backup, feed)
 *   TRADES                 Service Binding -> ctzb-trades (Coinbase trades relay)
 *   NOTIFY                 KV namespace: the SAME one ctzb-dashboard uses (its heartbeat)
 *   TELEGRAM_BOT_TOKEN     secret: the same bot as ctzb-dashboard
 *   TELEGRAM_CHAT_ID       plain var: Jared's numeric Telegram id
 * The GitHub watchdog reads this Worker's /health, so if Telegram itself is down, or this
 * Worker stops, the alert still arrives by GitHub email.
 *
 * SECURITY. This Worker holds a credential that can trigger CI, which is why it
 * is separate from the public mirror:
 *   - The token is read from env in exactly one function, sent only in an
 *     Authorization header to api.github.com, and never written to KV, never
 *     returned in a response, never logged.
 *   - There is no public data route. /health is the only path that returns
 *     anything; every other path is 404. No route reads caller input, so
 *     nothing a caller sends can influence which workflow is dispatched.
 *   - Workflow names, inputs and the ref are compile-time constants.
 */

const REPO = 'jaredbausch-ai/ctzb-data';
const REF = 'main';
const H = 60 * 60 * 1000;

/** What runs when. `stale` = how long without a successful dispatch is a problem. */
const JOBS = [
  {
    workflow: 'daily.yml',
    minutes: [13, 43],
    hours: [0, 4, 8, 12, 16, 20],
    inputs: { scheduled: 'true' },
    staleAfterMs: 5 * H, // normal gap is 3.5h (:43 to the next :13)
  },
  {
    workflow: 'watchdog.yml',
    minutes: [35],
    hours: [1, 5, 9, 13, 17, 21],
    inputs: null,
    staleAfterMs: 5 * H, // normal gap 4h
  },
  {
    workflow: 'pcr.yml',
    minutes: [25],
    hours: [0, 3, 6, 9, 12, 15, 18, 21],
    inputs: null,
    staleAfterMs: 4 * H, // normal gap 3h
  },
];

const JSON_HEADERS = { 'content-type': 'application/json; charset=utf-8' };
const statusKey = (wf) => `status:${wf}`;

/** Which jobs are due at this scheduled minute. Pure: no I/O. */
function due(scheduledTime) {
  const t = new Date(scheduledTime);
  const m = t.getUTCMinutes();
  const h = t.getUTCHours();
  return JOBS.filter((j) => j.minutes.includes(m) && j.hours.includes(h));
}

/**
 * The ONLY place the token is read or sent.
 * `job` comes from the constant table above, never from a request.
 */
async function dispatch(job, env) {
  const body = { ref: REF };
  if (job.inputs) body.inputs = job.inputs;
  const res = await fetch(
    `https://api.github.com/repos/${REPO}/actions/workflows/${job.workflow}/dispatches`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': 'ctzb-scheduler',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      body: JSON.stringify(body),
    }
  );
  // 204 No Content is success. Keep the status only, never the body:
  // GitHub error bodies can echo request detail.
  return res.status;
}

async function runJob(job, env, at) {
  const prev = (await env.SCHED.get(statusKey(job.workflow), { type: 'json' })) || {};
  let status = 0;
  try {
    status = await dispatch(job, env);
  } catch (_) {
    status = 0; // network-level failure; no detail retained
  }
  const ok = status === 204;
  await env.SCHED.put(
    statusKey(job.workflow),
    JSON.stringify({
      last_attempt_at: at,
      last_status: status,
      last_success_at: ok ? at : prev.last_success_at || null,
      consecutive_failures: ok ? 0 : (prev.consecutive_failures || 0) + 1,
      total_dispatches: (prev.total_dispatches || 0) + (ok ? 1 : 0),
      total_failures: (prev.total_failures || 0) + (ok ? 0 : 1),
    })
  );
}


/* ======================== health monitor (v3, 11 Nov 2026) ======================== */
const M = 60 * 1000;
/** Each check: how long a condition must last before it is a problem. */
const GRACE = {
  scheduler: 0,            // the job's own stale window already allows for a missed tick
  mirror: 0,               // the mirror itself waits an hour (four missed 15-minute syncs)
  backup: 0,
  feed_age: 0,             // 5 hours with no new feed = a 4-hour cycle missed
  withheld: 75 * M,        // a failed run retries within the hour; an hour+ is a problem
  extras: 75 * M,
  kraken: 26 * H,          // skipped on one 4-hour run is noise; a whole day is not
  trades: 10 * M,
  notifier: 0,
};
const FEED_STALE_H = 5;
const TRADES_STALE_MIN = 20;   // the relay refreshes last_ok_at at least every 15 minutes
const NOTIFIER_STALE_MIN = 45; // its cron fires 4 times an hour
const BACKUP_STALE_H = 26;     // daily at 01:00 UTC
const REMIND_EVERY = 6 * H;
const monKey = (id) => `mon:${id}`;
const iso = (t) => (t ? new Date(t).toISOString().slice(0, 16).replace('T', ' ') + ' UTC' : 'never');
const hoursAgo = (t, now) => (t ? ((now - t) / H).toFixed(1) + 'h' : 'never');

async function svcJSON(svc, path) {
  if (!svc || typeof svc.fetch !== 'function') return { status: -1, body: null };
  try {
    const r = await svc.fetch(new Request('https://svc' + path));
    if (!r.ok) return { status: r.status, body: null };
    return { status: r.status, body: await r.json() };
  } catch (_) {
    return { status: 0, body: null };
  }
}

/** Every check, evaluated now. Returns [{id, bad, text}] -- `bad` before any grace period. */
async function evaluate(env, now) {
  const out = [];
  const add = (id, bad, text) => out.push({ id, bad: !!bad, text });

  // 1. this Worker's own dispatches to GitHub
  for (const j of JOBS) {
    const s = await env.SCHED.get(statusKey(j.workflow), { type: 'json' });
    const last = s && s.last_success_at;
    const stale = !last || now - last > j.staleAfterMs;
    const failing = s && s.consecutive_failures >= 3;
    add('scheduler:' + j.workflow, stale || failing,
      `The scheduler can't start ${j.workflow} on GitHub: last success ${iso(last)}` +
      (s ? `, ${s.consecutive_failures} failures in a row (status ${s.last_status})` : '') +
      '. Check the GitHub token on ctzb-scheduler.');
  }

  // 2-4. the mirror, its nightly backup, and the feed it serves
  const mh = await svcJSON(env.MIRROR, '/health');
  if (mh.status === -1) {
    add('mirror', false, 'not bound');
  } else {
    const b = mh.body;
    add('mirror', !b || !b.ok,
      !b ? `The mirror (data for the site, the dashboard and alerts) is unreachable (status ${mh.status}).`
        : `The mirror hasn't synced from GitHub since ${b.last_clean_run_at || 'never'} (${b.consecutive_failures} failed syncs). The site and the alerts are showing old data.`);
    const bk = b && b.backup;
    const bkLast = bk && bk.last_ok_at ? Date.parse(bk.last_ok_at) || bk.last_ok_at : null;
    add('backup', b && (bk === 'not configured' || !bk || bk.consecutive_failures >= 1 || !bkLast || now - bkLast > BACKUP_STALE_H * H),
      bk === 'not configured' ? 'Nightly backups are not configured (no R2 binding on ctzb-feed).'
        : `The nightly backup failed: last good backup ${iso(bkLast)}` + (bk && bk.consecutive_failures ? `, ${bk.consecutive_failures} failures in a row` : '') + '.');

    const fd = await svcJSON(env.MIRROR, '/feed/ctzb_feed.json');
    const f = fd.body;
    const gen = f && Date.parse(f.generated_at);
    add('feed_age', b && b.ok && (!f || !gen || now - gen > FEED_STALE_H * H),
      !f ? 'The feed is missing from the mirror.'
        : `No new data for ${hoursAgo(gen, now)}: the pipeline hasn't produced a feed since ${iso(gen)}. GitHub should also have emailed.`);
    if (f) {
      const failed = (f.checks && f.checks.failed_steps) || [];
      add('withheld', f.cards_withheld,
        `Setups and alerts are being held back: a data check keeps failing (${failed.join(', ') || 'stack check'}). Nothing new reaches the site or your phone until it passes.`);
      add('extras', f.extras_withheld && !f.cards_withheld,
        'The member-card figures (if it misses, odds fade, past paths) are being held back: the extras step keeps failing.');
      const k = f.candle_check && f.candle_check.kraken;
      if (k) {
        const notOk = Object.entries(k).filter(([, v]) => v !== 'ok').map(([a, v]) => `${a} ${v}`);
        add('kraken', notOk.length,
          `The Kraken price cross-check has been skipped for over a day (${notOk.join(', ')}). Candles are still checked for structure, but not against a second exchange.`);
      }
    }
  }

  // 5. the Coinbase trades relay
  const th = await svcJSON(env.TRADES, '/health');
  if (th.status !== -1) {
    const t = th.body;
    const last = t && Date.parse(t.last_ok_at);
    add('trades', !t || !last || now - last > TRADES_STALE_MIN * M || t.consecutive_failures >= 3,
      !t ? `The trades relay is unreachable (status ${th.status}).`
        : `The trades relay can't read Coinbase: last good read ${iso(last)}, ${t.consecutive_failures || 0} failures in a row${t.last_error ? ` (${String(t.last_error).slice(0, 80)})` : ''}. Your trades won't post.`);
  }

  // 6. the Telegram setup-alert sender (ctzb-dashboard's cron)
  if (env.NOTIFY) {
    const hb = await env.NOTIFY.get('heartbeat', { type: 'json' });
    const ns = await env.NOTIFY.get('status', { type: 'json' });
    const stopped = !hb || now - hb.at > NOTIFIER_STALE_MIN * M;
    const failing = ns && ns.consecutive_failures >= 2;
    add('notifier', stopped || failing,
      stopped ? `The setup-alert sender has stopped (last ran ${iso(hb && hb.at)}). New setups will NOT reach your phone until it's fixed: check ctzb-dashboard's cron.`
        : `Setup alerts are failing to send (${ns.consecutive_failures} tries in a row, Telegram status ${ns.last_status}).`);
  }
  return out;
}

async function telegram(env, text, fetchImpl) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return -1;
  try {
    const r = await fetchImpl(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text, disable_web_page_preview: true }),
    });
    return r.status; // status only, never the body
  } catch (_) {
    return 0;
  }
}

/**
 * One pass. Per check, KV holds {since, alerted_at, reminded_at} while the condition lasts
 * and nothing once it clears, so KV is written only when something changes, plus one
 * small status record per tick. A message that fails to send is retried next tick.
 */
async function monitor(env, now, fetchImpl = fetch) {
  const results = await evaluate(env, now);
  const sent = [], problems = [];
  let lastSend = null;
  if (!(await env.SCHED.get('mon:hello')) && env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_CHAT_ID) {
    const st = await telegram(env, 'CTZB health monitor connected. You will get a message here when anything in the pipeline, the mirror, the backup, the trades relay or the alert sender goes down, and again when it recovers.', fetchImpl);
    if (st === 200) await env.SCHED.put('mon:hello', String(now));
    lastSend = st;
  }
  for (const r of results) {
    const key = monKey(r.id);
    const st = await env.SCHED.get(key, { type: 'json' });
    if (!r.bad) {
      if (st) {
        if (st.alerted_at) {
          const s2 = await telegram(env, `RECOVERED: ${r.id.split(':')[0]} is working again (problem since ${iso(st.since)}).`, fetchImpl);
          lastSend = s2;
          if (s2 !== 200 && s2 !== -1) continue; // keep the record; say it next tick
          sent.push('recovered:' + r.id);
        }
        await env.SCHED.delete(key);
      }
      continue;
    }
    const since = st ? st.since : now;
    const grace = GRACE[r.id.split(':')[0]] || 0;
    if (now - since < grace) {
      if (!st) await env.SCHED.put(key, JSON.stringify({ since }));
      continue;
    }
    problems.push(r.id);
    const remind = !st || !st.alerted_at || now - (st.reminded_at || st.alerted_at) >= REMIND_EVERY;
    if (!remind) continue;
    const first = !st || !st.alerted_at;
    const s2 = await telegram(env, (first ? 'PROBLEM: ' : `STILL DOWN since ${iso(since)}: `) + r.text, fetchImpl);
    lastSend = s2;
    if (s2 === 200) {
      sent.push(r.id);
      await env.SCHED.put(key, JSON.stringify({ since, alerted_at: first ? now : st.alerted_at, reminded_at: now }));
    } else if (!st) {
      await env.SCHED.put(key, JSON.stringify({ since }));
    }
  }
  const status = { last_run_at: now, problems, last_send_status: lastSend, telegram_configured: !!(env.TELEGRAM_BOT_TOKEN && env.TELEGRAM_CHAT_ID),
    watching: { mirror: !!env.MIRROR, trades: !!env.TRADES, notifier: !!env.NOTIFY } };
  const prev = await env.SCHED.get('mon:status', { type: 'json' });
  if (lastSend !== null) status.last_send_at = now; else if (prev) { status.last_send_at = prev.last_send_at || null; status.last_send_status = prev.last_send_status ?? null; }
  await env.SCHED.put('mon:status', JSON.stringify(status));
  return { problems, sent };
}

async function health(env) {
  const now = Date.now();
  const jobs = {};
  let allOk = true;
  for (const j of JOBS) {
    const s = await env.SCHED.get(statusKey(j.workflow), { type: 'json' });
    const last = s && s.last_success_at ? s.last_success_at : null;
    const stale = !last || now - last > j.staleAfterMs;
    if (stale) allOk = false;
    jobs[j.workflow] = {
      ok: !stale,
      stale,
      stale_after_hours: j.staleAfterMs / H,
      last_success_at: last ? new Date(last).toISOString() : null,
      last_attempt_at: s && s.last_attempt_at ? new Date(s.last_attempt_at).toISOString() : null,
      last_status: s ? s.last_status : null,
      consecutive_failures: s ? s.consecutive_failures : null,
      total_dispatches: s ? s.total_dispatches : null,
      total_failures: s ? s.total_failures : null,
    };
  }
  const mon = await env.SCHED.get('mon:status', { type: 'json' });
  const monitorOut = mon ? {
    last_run_at: new Date(mon.last_run_at).toISOString(),
    stale: now - mon.last_run_at > 40 * 60 * 1000,
    problems: mon.problems,
    telegram_configured: mon.telegram_configured,
    last_send_at: mon.last_send_at ? new Date(mon.last_send_at).toISOString() : null,
    last_send_status: mon.last_send_status,
    watching: mon.watching,
  } : null;
  return new Response(JSON.stringify({ ok: allOk, version: 3, jobs, monitor: monitorOut }, null, 2), {
    status: 200,
    headers: JSON_HEADERS,
  });
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return new Response(JSON.stringify({ error: 'read-only' }), { status: 405, headers: JSON_HEADERS });
    }
    if (pathname === '/health') return health(env);
    // No other route exists. Nothing here is built from caller input.
    return new Response(JSON.stringify({ error: 'not found' }), { status: 404, headers: JSON_HEADERS });
  },

  async scheduled(event, env, ctx) {
    const at = event.scheduledTime;
    for (const job of due(at)) ctx.waitUntil(runJob(job, env, at));
    ctx.waitUntil(monitor(env, at).catch(() => {}));
  },
};

