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
  return new Response(JSON.stringify({ ok: allOk, version: 2, jobs }, null, 2), {
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
  },
};

