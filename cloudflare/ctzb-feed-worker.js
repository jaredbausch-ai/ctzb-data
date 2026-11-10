/**
 * CTZB read-only mirror.
 *
 * Serves a fixed, allowlisted set of files from the private GitHub repo
 * jaredbausch-ai/ctzb-data, so that consumers which read the public repo today
 * can keep working after it is made private by changing only their base URL.
 *
 * Bindings required:
 *   FEED           KV namespace (binding name must be exactly FEED)
 *   GITHUB_TOKEN   secret: fine-grained PAT, Contents: read-only, this repo only
 *
 * Cron: every 15 minutes. Writes to KV only when a file's git SHA has changed,
 * so an unchanged repo costs no KV writes.
 *
 * SECURITY — the two properties this file is built to guarantee:
 *
 *   1. The token cannot leak. It is read from env only inside ghFetch(), sent
 *      only in an Authorization header to api.github.com, and never written to
 *      KV, never put in a response body or header, and never logged. No
 *      upstream error body is ever forwarded to a caller; failures return a
 *      fixed generic string.
 *
 *   2. No path can reach outside the repo. Caller input is never concatenated
 *      into a GitHub path. Fixed paths come from an allowlist object; the only
 *      variable part is a dataset filename matched against /^[a-z0-9_]{1,64}\.csv$/,
 *      which cannot express "/", "." or ".." and so cannot traverse. Anything
 *      not matching is 404 before any upstream call is made.
 *
 * Read-only: only GET, HEAD and OPTIONS are accepted. There is no code path
 * that writes to GitHub, and no directory listing is exposed.
 *
 * BACKUPS (item 17e, 10 Nov 2026). Optional R2 binding BACKUPS. Once a day, on the
 * 01:00 UTC tick (after the daily-close run has committed), the cron stores a
 * snapshot of the exact current commit as daily/ctzb-data-YYYY-MM-DD.tar.gz, tagged
 * with the commit sha, and on the 1st of the month also monthly/ctzb-data-YYYY-MM.
 * Write-once: an existing key is never overwritten. Daily copies are expired by an
 * R2 lifecycle rule, not by code. Nothing a caller sends reaches this path; it runs
 * only from the cron. Without the binding, it does nothing.
 */

const REPO = 'jaredbausch-ai/ctzb-data';
const BRANCH = 'main';

/** Fixed public path -> repo path. The only entries that will ever be served. */
const FIXED = {
  '/feed/ctzb_feed.json': 'feed/ctzb_feed.json',
  '/keep.json':           'keep.json',
  '/odds.json':           'odds.json',
  '/troughs.json':        'troughs.json',
};

/** A dataset filename, and nothing else. No slash, no dot except the extension. */
const DATASET = /^[a-z0-9_]{1,64}\.csv$/;

/**
 * Staleness is about THE MIRROR, not the content.
 *
 * A file that has not changed in days is not stale -- a quiet market is the
 * system working. What matters is whether the cron is still completing cleanly.
 * The cron runs every 15 minutes, so an hour without a clean run means four
 * consecutive misses and something is genuinely wrong.
 */
const MIRROR_STALE_AFTER_MS = 60 * 60 * 1000;
const MAX_BYTES = 20 * 1024 * 1024;

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
  'Access-Control-Max-Age': '86400',
};

const kvKey = (repoPath) => `f:${repoPath}`;
const metaKey = (repoPath) => `m:${repoPath}`;

function contentType(repoPath) {
  if (repoPath.endsWith('.csv')) return 'text/csv; charset=utf-8';
  if (repoPath.endsWith('.json')) return 'application/json; charset=utf-8';
  return 'text/plain; charset=utf-8';
}

function fail(status, message) {
  // Deliberately fixed strings. Upstream error detail is never forwarded.
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', ...CORS },
  });
}

/**
 * The ONLY place the token is read or sent. Both helpers below go through this.
 * `url` is always built by this worker, never from raw caller input.
 */
async function gh(url, env, raw) {
  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: raw ? 'application/vnd.github.raw' : 'application/vnd.github+json',
      'User-Agent': 'ctzb-feed-worker',
      'X-GitHub-Api-Version': '2022-11-28',
    },
  });
  if (!res.ok) throw new Error(`upstream ${res.status}`); // status only, never the body
  return res;
}

/** One file or directory from the repo. `repoPath` comes from the allowlist. */
const ghFetch = (repoPath, env, raw = true) =>
  gh(`https://api.github.com/repos/${REPO}/contents/${repoPath}?ref=${BRANCH}`, env, raw);

/** The full file tree, for SHAs, in a single request. */
const ghTree = (env) =>
  gh(`https://api.github.com/repos/${REPO}/git/trees/${BRANCH}?recursive=1`, env, false);

/** Current dataset filenames in the repo. Internal only; never served. */
async function listDatasets(env) {
  const res = await ghFetch('datasets', env, false);
  const items = await res.json();
  if (!Array.isArray(items)) return [];
  return items
    .filter((it) => it && it.type === 'file' && DATASET.test(it.name))
    .map((it) => it.name);
}

/**
 * Fetch one file and write it to KV only if its SHA changed.
 *
 * An unchanged file performs ZERO writes -- not even a timestamp. The free KV
 * plan allows 1000 writes/day; at 96 cron ticks over ~25 files, a per-file
 * touch would cost ~2600/day and the mirror would stop saving about 9 hours
 * into each day. "When did we last check?" is answered once per run by the
 * `status` key instead, which is why there is no checked_at here.
 */
async function syncOne(repoPath, env, sha) {
  const prev = await env.FEED.get(metaKey(repoPath), { type: 'json' });
  if (prev && sha && prev.sha === sha) return 'unchanged';
  const res = await ghFetch(repoPath, env);
  const body = await res.text();
  if (body.length > MAX_BYTES) throw new Error('too large');
  await env.FEED.put(kvKey(repoPath), body);
  await env.FEED.put(
    metaKey(repoPath),
    JSON.stringify({ sha: sha || null, fetched_at: Date.now(), bytes: body.length })
  );
  return 'updated';
}

/** Refresh every allowlisted file. Never throws; records failures instead. */
async function refresh(env) {
  const report = { at: Date.now(), updated: 0, unchanged: 0, failed: 0, errors: [] };

  // One tree call gives every SHA at once, so we avoid a request per file.
  const shas = new Map();
  try {
    const tree = await (await ghTree(env)).json();
    for (const node of tree.tree || []) if (node.type === 'blob') shas.set(node.path, node.sha);
  } catch (_) {
    // No SHA map this tick: every file is fetched unconditionally instead.
    report.errors.push('tree listing failed');
  }

  let paths = Object.values(FIXED);
  try {
    const names = await listDatasets(env);
    paths = paths.concat(names.map((n) => `datasets/${n}`));
    const prevIdx = await env.FEED.get('idx:datasets', { type: 'json' });
    const changed =
      !prevIdx || !Array.isArray(prevIdx.names) || prevIdx.names.join(',') !== names.join(',');
    if (changed) await env.FEED.put('idx:datasets', JSON.stringify({ names, at: Date.now() }));
  } catch (_) {
    const cached = await env.FEED.get('idx:datasets', { type: 'json' });
    if (cached && Array.isArray(cached.names)) {
      paths = paths.concat(cached.names.map((n) => `datasets/${n}`));
    }
    report.errors.push('datasets listing failed');
  }

  for (const p of paths) {
    try {
      const r = await syncOne(p, env, shas.get(p));
      report[r === 'updated' ? 'updated' : 'unchanged']++;
    } catch (_) {
      report.failed++;
      report.errors.push(p); // path only; never the upstream message
    }
  }

  const prev = (await env.FEED.get('status', { type: 'json' })) || { consecutive_failures: 0 };
  await env.FEED.put(
    'status',
    JSON.stringify({
      last_run_at: report.at,
      updated: report.updated,
      unchanged: report.unchanged,
      failed: report.failed,
      errors: report.errors.slice(0, 20),
      consecutive_failures: report.failed > 0 ? (prev.consecutive_failures || 0) + 1 : 0,
      last_clean_run_at: report.failed === 0 ? report.at : prev.last_clean_run_at || null,
    })
  );
  return report;
}

/** Resolve a public path to a repo path, or null. No traversal is possible. */
function resolve(pathname) {
  if (Object.prototype.hasOwnProperty.call(FIXED, pathname)) return FIXED[pathname];
  if (pathname.startsWith('/datasets/')) {
    const name = pathname.slice('/datasets/'.length);
    if (DATASET.test(name)) return `datasets/${name}`;
  }
  return null;
}

async function serve(repoPath, env, headOnly) {
  const [body, meta] = await Promise.all([
    env.FEED.get(kvKey(repoPath)),
    env.FEED.get(metaKey(repoPath), { type: 'json' }),
  ]);
  if (body === null) return fail(503, 'not cached yet');

  const status = await env.FEED.get('status', { type: 'json' });
  const lastClean = status && status.last_clean_run_at ? status.last_clean_run_at : null;
  // Stale = the MIRROR has not completed a clean run recently. Unchanged
  // content is not stale: a file nobody edited is the system working.
  const stale = !lastClean || Date.now() - lastClean > MIRROR_STALE_AFTER_MS;
  const fetchedAt = meta && meta.fetched_at ? meta.fetched_at : null;

  return new Response(headOnly ? null : body, {
    status: 200,
    headers: {
      'content-type': contentType(repoPath),
      'cache-control': 'public, max-age=60',
      // when this FILE last changed
      'x-ctzb-content-changed-at': fetchedAt ? new Date(fetchedAt).toISOString() : 'unknown',
      // when the MIRROR last ran clean
      'x-ctzb-checked-at': lastClean ? new Date(lastClean).toISOString() : 'never',
      'x-ctzb-stale': stale ? 'true' : 'false',
      ...CORS,
    },
  });
}

/**
 * `ok` answers one question: is the mirror working? It does NOT go false
 * because the repo has been quiet. Content age is reported separately as
 * feed_content_age_hours so a consumer can judge that itself.
 */
/** Hour/minute (UTC) of the daily backup tick. The cron fires every 15 minutes. */
const BACKUP_AT = { hour: 1, minute: 0 };
const MAX_BACKUP_BYTES = 200 * 1024 * 1024;

const isBackupTick = (t) => {
  const d = new Date(t);
  return d.getUTCHours() === BACKUP_AT.hour && d.getUTCMinutes() === BACKUP_AT.minute;
};

/** One daily snapshot. Never throws; records the outcome in KV (one write a day). */
async function backup(env, at) {
  if (!env.BACKUPS) return { skipped: 'no binding' };
  const day = new Date(at).toISOString().slice(0, 10);
  const keys = [`daily/ctzb-data-${day}.tar.gz`];
  if (day.endsWith('-01')) keys.push(`monthly/ctzb-data-${day.slice(0, 7)}.tar.gz`);
  const result = { at: new Date(at).toISOString(), keys: [], skipped: [], ok: false, error: null };
  try {
    const todo = [];
    for (const k of keys) ((await env.BACKUPS.head(k)) ? result.skipped : todo).push(k);
    if (todo.length) {
      // Pin the snapshot to one commit, so the tag says exactly what is inside.
      const commit = await (await gh(`https://api.github.com/repos/${REPO}/commits/${BRANCH}`, env, false)).json();
      const sha = commit && commit.sha;
      if (!/^[0-9a-f]{40}$/.test(sha || '')) throw new Error('no commit sha');
      const tar = await (await gh(`https://api.github.com/repos/${REPO}/tarball/${sha}`, env, false)).arrayBuffer();
      if (tar.byteLength > MAX_BACKUP_BYTES) throw new Error('snapshot too large');
      if (tar.byteLength < 1024) throw new Error('snapshot too small');
      for (const k of todo) {
        await env.BACKUPS.put(k, tar, {
          httpMetadata: { contentType: 'application/gzip' },
          customMetadata: { sha, repo: REPO, taken_at: result.at },
        });
        result.keys.push(k);
      }
      result.sha = sha;
      result.bytes = tar.byteLength;
    }
    result.ok = true;
  } catch (e) {
    result.error = String((e && e.message) || 'failed').slice(0, 80); // our own messages only
  }
  const prev = (await env.FEED.get('backup', { type: 'json' })) || {};
  await env.FEED.put('backup', JSON.stringify({
    ...result,
    last_ok_at: result.ok ? result.at : prev.last_ok_at || null,
    last_ok_key: result.ok && result.keys.length ? result.keys[0] : prev.last_ok_key || null,
    consecutive_failures: result.ok ? 0 : (prev.consecutive_failures || 0) + 1,
  }));
  return result;
}

async function health(env) {
  const status = (await env.FEED.get('status', { type: 'json' })) || null;
  const feedMeta = await env.FEED.get(metaKey(FIXED['/feed/ctzb_feed.json']), { type: 'json' });
  const idx = await env.FEED.get('idx:datasets', { type: 'json' });

  const lastClean = status && status.last_clean_run_at ? status.last_clean_run_at : null;
  const mirrorStale = !lastClean || Date.now() - lastClean > MIRROR_STALE_AFTER_MS;
  const contentAt = feedMeta && feedMeta.fetched_at ? feedMeta.fetched_at : null;

  return new Response(
    JSON.stringify(
      {
        ok: !!lastClean && !mirrorStale,
        mirror_stale: mirrorStale,
        mirror_stale_after_minutes: MIRROR_STALE_AFTER_MS / 60000,
        last_run_at: status && status.last_run_at ? new Date(status.last_run_at).toISOString() : null,
        last_clean_run_at: lastClean ? new Date(lastClean).toISOString() : null,
        consecutive_failures: status ? status.consecutive_failures : null,
        failed_last_run: status ? status.failed : null,
        failed_paths: status ? status.errors : [],
        updated_last_run: status ? status.updated : null,
        feed_available: !!contentAt,
        feed_content_changed_at: contentAt ? new Date(contentAt).toISOString() : null,
        feed_content_age_hours: contentAt ? +((Date.now() - contentAt) / 3600000).toFixed(1) : null,
        dataset_count: idx && idx.names ? idx.names.length : null,
        backup: env.BACKUPS ? await env.FEED.get('backup', { type: 'json' }) : 'not configured',
      },
      null,
      2
    ),
    { status: 200, headers: { 'content-type': 'application/json; charset=utf-8', ...CORS } }
  );
}

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return fail(405, 'read-only');
    }

    if (pathname === '/health') return health(env);

    if (pathname === '/' || pathname === '') {
      return serve(FIXED['/feed/ctzb_feed.json'], env, false);
    }

    const repoPath = resolve(pathname);
    if (!repoPath) return fail(404, 'not found');

    return serve(repoPath, env, request.method === 'HEAD');
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(refresh(env));
    if (isBackupTick(event.scheduledTime)) ctx.waitUntil(backup(env, event.scheduledTime));
  },
};
