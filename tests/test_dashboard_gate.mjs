// Tests for the ctzb-dashboard Worker's gate and routes (item 17f).
// Real RS256 signatures from a generated key; the Access certs endpoint is mocked.
// Run: node tests/test_dashboard_gate.mjs   -- exits 1 if any case fails.
import { webcrypto } from "node:crypto";
import { fileURLToPath } from "node:url";
import path from "node:path";
import fs from "node:fs";
const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const worker = (await import(path.join(ROOT, "cloudflare/ctzb-dashboard-worker.js"))).default;

const TEAM = "ethkros.cloudflareaccess.com", AUD = "aud-tag-123", KID = "k1";
const enc = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
const kp = await webcrypto.subtle.generateKey({ name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"]);
const other = await webcrypto.subtle.generateKey({ name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["sign", "verify"]);
const pubJwk = { ...(await webcrypto.subtle.exportKey("jwk", kp.publicKey)), kid: KID };
let certCalls = 0;
globalThis.fetch = async (u) => {
  if (String(u) === `https://${TEAM}/cdn-cgi/access/certs`) { certCalls++; return new Response(JSON.stringify({ keys: [pubJwk] })); }
  throw new Error("unexpected fetch " + u);
};
async function jwt(payload, { key = kp.privateKey, header = { alg: "RS256", kid: KID } } = {}) {
  const h = enc(header), p = enc(payload);
  const sig = await webcrypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(h + "." + p));
  return h + "." + p + "." + Buffer.from(sig).toString("base64url");
}
const now = Math.floor(Date.now() / 1000);
const good = { aud: [AUD], iss: `https://${TEAM}`, exp: now + 3600, iat: now, email: "j@example.com" };
const mirror = { fetch: async (req) => {
  const p = new URL(req.url).pathname;
  const f = path.join(ROOT, p.replace(/^\//, ""));
  if (p === "/health") return new Response("{}");
  return fs.existsSync(f) ? new Response(fs.readFileSync(f), { headers: { "x-ctzb-stale": "false" } }) : new Response("nf", { status: 404 });
} };
const ACC = { GATE_MODE: "access", ACCESS_TEAM_DOMAIN: TEAM, ACCESS_AUD: AUD, MIRROR: mirror };
const PW = { GATE_MODE: "password", DASHBOARD_PASSWORD: "correct horse", MIRROR: mirror };
const req = (p, h = {}, method = "GET") => new Request("https://ctzb-dashboard.example.workers.dev" + p, { method, headers: h });
const res = [];
async function expect(name, r, status, check) {
  const resp = await r; const body = resp.status === 200 ? await resp.text() : "";
  const ok = resp.status === status && (!check || check(resp, body));
  res.push(ok); console.log(`  ${ok ? "PASS" : "*** FAIL ***"}  ${name}  -> ${resp.status}`);
}
console.log("--- access mode ---");
await expect("valid Access token gets the page", worker.fetch(req("/", { "cf-access-jwt-assertion": await jwt(good) }), ACC), 200,
  (r, b) => b.includes("<title>ETH Setup Standard</title>") && r.headers.get("content-security-policy").includes("connect-src 'self'"));
await expect("no token -> 403", worker.fetch(req("/"), ACC), 403);
await expect("token from the wrong application (aud) -> 403", worker.fetch(req("/", { "cf-access-jwt-assertion": await jwt({ ...good, aud: ["someone-else"] }) }), ACC), 403);
await expect("expired token -> 403", worker.fetch(req("/", { "cf-access-jwt-assertion": await jwt({ ...good, exp: now - 5 }) }), ACC), 403);
await expect("wrong issuer -> 403", worker.fetch(req("/", { "cf-access-jwt-assertion": await jwt({ ...good, iss: "https://evil.cloudflareaccess.com" }) }), ACC), 403);
await expect("signed by a different key -> 403", worker.fetch(req("/", { "cf-access-jwt-assertion": await jwt(good, { key: other.privateKey }) }), ACC), 403);
await expect("unknown kid -> 403", worker.fetch(req("/", { "cf-access-jwt-assertion": await jwt(good, { header: { alg: "RS256", kid: "nope" } }) }), ACC), 403);
const forged = enc({ alg: "none", kid: KID }) + "." + enc(good) + ".";
await expect("alg:none forgery -> 403", worker.fetch(req("/", { "cf-access-jwt-assertion": forged }), ACC), 403);
const t = await jwt(good); const tampered = t.split(".")[0] + "." + enc({ ...good, email: "attacker@x" }) + "." + t.split(".")[2];
await expect("payload tampered after signing -> 403", worker.fetch(req("/", { "cf-access-jwt-assertion": tampered }), ACC), 403);
await expect("access mode missing AUD config -> 403 (fails closed)", worker.fetch(req("/", { "cf-access-jwt-assertion": await jwt(good) }), { ...ACC, ACCESS_AUD: "" }), 403);
await expect("/health is gated too", worker.fetch(req("/health"), ACC), 403);
console.log("--- password mode ---");
const basic = (pw) => ({ authorization: "Basic " + Buffer.from("jared:" + pw).toString("base64") });
await expect("right password gets the page", worker.fetch(req("/", basic("correct horse")), PW), 200);
await expect("wrong password -> 401 with a login prompt", worker.fetch(req("/", basic("wrong")), PW), 401, (r) => (r.headers.get("www-authenticate") || "").startsWith("Basic"));
await expect("no password -> 401", worker.fetch(req("/"), PW), 401);
await expect("password mode with no secret set -> 401 (fails closed)", worker.fetch(req("/", basic("")), { ...PW, DASHBOARD_PASSWORD: "" }), 401);
console.log("--- no gate configured ---");
await expect("GATE_MODE unset -> 503, nothing served", worker.fetch(req("/", basic("correct horse")), { MIRROR: mirror }), 503);
await expect("GATE_MODE misspelled -> 503", worker.fetch(req("/"), { GATE_MODE: "Access", MIRROR: mirror }), 503);
console.log("--- routes (authenticated) ---");
const A = basic("correct horse");
await expect("dataset served as CSV", worker.fetch(req("/data/datasets/status.csv", A), PW), 200,
  (r, b) => r.headers.get("content-type").startsWith("text/csv") && b.startsWith("item,value"));
for (const p of ["/data/datasets/../../.git/config", "/data/datasets/..%2fkeep.json", "/data/keep.json", "/data/datasets/X.csv", "/data/datasets/a/b.csv", "/datasets/status.csv"])
  await expect("traversal/off-list " + p + " -> 404", worker.fetch(req(p, A), PW), 404);
await expect("POST -> 405", worker.fetch(req("/", A, "POST"), PW), 405);
await expect("/health reports mirror", worker.fetch(req("/health", A), PW), 200, (r, b) => JSON.parse(b).mirror === "ok");
console.log(`\ncerts fetched ${certCalls}x across ${res.length} requests (cached)`);
console.log(`${res.filter(Boolean).length}/${res.length} passed`);
process.exit(res.every(Boolean) ? 0 : 1);
