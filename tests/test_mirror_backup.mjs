// Tests for the ctzb-feed mirror's daily R2 backup (item 17e). GitHub, R2 and KV mocked.
// Run: node tests/test_mirror_backup.mjs   -- exits 1 if any case fails.
import fs from "node:fs"; import os from "node:os"; import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "ctzbmirror-")), "m.mjs");
fs.writeFileSync(tmp, fs.readFileSync(path.join(ROOT, "cloudflare/ctzb-feed-worker.js"), "utf8") +
  "\nexport const _test = { backup, isBackupTick };\n");
const { _test, default: worker } = await import(pathToFileURL(tmp));
const TOKEN = "github_pat_SECRET123";
const SHA = "a".repeat(40);
let ghCalls = [], ghFail = false, tarSize = 9_000_000;
globalThis.fetch = async (url, init) => {
  const u = String(url); ghCalls.push(u);
  if (ghFail) return new Response("boom " + TOKEN, { status: 502 });
  if (u.endsWith("/commits/main")) return new Response(JSON.stringify({ sha: SHA }));
  if (u.includes("/tarball/")) return new Response(new Uint8Array(tarSize));
  return new Response("{}");
};
const kv = () => { const m = new Map(); return { m,
  get: async (k, o) => { const v = m.get(k); return v === undefined ? null : (o && o.type === "json" ? JSON.parse(v) : v); },
  put: async (k, v) => { m.set(k, v); } }; };
const r2 = () => { const m = new Map(); return { m, puts: 0,
  head: async (k) => (m.has(k) ? { key: k } : null),
  put: async function (k, v, o) { this.puts++; m.set(k, { size: v.byteLength, meta: o.customMetadata, type: o.httpMetadata.contentType }); } }; };
const res = []; const check = (n, c, d = "") => { res.push(!!c); console.log(`  ${c ? "PASS" : "*** FAIL ***"}  ${n}${d ? "  -- " + d : ""}`); };
const T = (iso) => Date.parse(iso);

check("01:00 UTC is the backup tick", _test.isBackupTick(T("2026-11-11T01:00:00Z")));
check("01:15 and 00:00 are not", !_test.isBackupTick(T("2026-11-11T01:15:00Z")) && !_test.isBackupTick(T("2026-11-11T00:00:00Z")));

let B = r2(), K = kv(); const env = () => ({ BACKUPS: B, FEED: K, GITHUB_TOKEN: TOKEN });
let r = await _test.backup(env(), T("2026-11-11T01:00:00Z"));
const o = B.m.get("daily/ctzb-data-2026-11-11.tar.gz");
check("daily snapshot written", r.ok && o && o.size === 9_000_000 && o.type === "application/gzip");
check("tagged with the exact commit", o && o.meta.sha === SHA);
check("no monthly copy on the 11th", !B.m.has("monthly/ctzb-data-2026-11.tar.gz"));
const st = JSON.parse(K.m.get("backup"));
check("status recorded", st.ok && st.last_ok_key === "daily/ctzb-data-2026-11-11.tar.gz" && st.consecutive_failures === 0);

ghCalls = []; const putsBefore = B.puts;
r = await _test.backup(env(), T("2026-11-11T01:00:00Z"));
check("same day again: skipped, nothing downloaded, nothing overwritten", ghCalls.length === 0 && B.puts === putsBefore && r.skipped.length === 1);

ghCalls = [];
r = await _test.backup(env(), T("2026-12-01T01:00:00Z"));
check("1st of the month: daily AND monthly, from ONE download",
  B.m.has("daily/ctzb-data-2026-12-01.tar.gz") && B.m.has("monthly/ctzb-data-2026-12.tar.gz") && ghCalls.filter(u => u.includes("/tarball/")).length === 1);

B = r2(); K = kv(); ghFail = true;
r = await _test.backup(env(), T("2026-11-12T01:00:00Z"));
check("GitHub down: nothing written, no throw", !r.ok && B.puts === 0);
r = await _test.backup(env(), T("2026-11-13T01:00:00Z"));
const st2 = JSON.parse(K.m.get("backup"));
check("failures counted", st2.consecutive_failures === 2 && !st2.ok);
check("upstream error body (which could echo detail) is not stored", !K.m.get("backup").includes(TOKEN) && !K.m.get("backup").includes("boom"));
ghFail = false; await _test.backup(env(), T("2026-11-14T01:00:00Z"));
check("recovery resets the count", JSON.parse(K.m.get("backup")).consecutive_failures === 0);

B = r2(); K = kv(); tarSize = 10;
r = await _test.backup(env(), T("2026-11-15T01:00:00Z"));
check("suspiciously small snapshot is refused, not stored", !r.ok && B.puts === 0 && r.error === "snapshot too small");
tarSize = 9_000_000;

r = await _test.backup({ FEED: kv(), GITHUB_TOKEN: TOKEN }, T("2026-11-16T01:00:00Z"));
check("no R2 binding: does nothing", r.skipped === "no binding");

// the public mirror is unchanged
const KH = kv(); await _test.backup({ BACKUPS: r2(), FEED: KH, GITHUB_TOKEN: TOKEN }, T("2026-11-17T01:00:00Z"));
const h = await worker.fetch(new Request("https://m/health"), { FEED: KH, BACKUPS: r2(), GITHUB_TOKEN: TOKEN });
const hb = await h.text();
check("/health shows backup status, never the token", JSON.parse(hb).backup.ok === true && !hb.includes(TOKEN));
// (a raw "../" is normalised away by URL parsing before it reaches the Worker, as in a
// browser, so test paths that stay hostile after normalisation)
for (const bad of ["/datasets/..%2fkeep.json", "/datasets/..%2f..%2f.git%2fconfig", "/.git/config", "/datasets/sub/x.csv", "/fetch.py"]) {
  const t = await worker.fetch(new Request("https://m" + bad), { FEED: KH });
  check("off-list path still 404: " + bad, t.status === 404, String(t.status));
}
const p = await worker.fetch(new Request("https://m/health", { method: "POST" }), { FEED: KH });
check("still read-only (POST -> 405)", p.status === 405);
console.log(`\n${res.filter(Boolean).length}/${res.length} passed`);
process.exit(res.every(Boolean) ? 0 : 1);
