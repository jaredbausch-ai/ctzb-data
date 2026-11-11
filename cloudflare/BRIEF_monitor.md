# Health monitor — setup brief

For Claude in Chrome. 11 November 2026. Two existing Workers get new code:
`ctzb-dashboard` (leaves a heartbeat so a stopped alert sender is noticed) and
`ctzb-scheduler` (now also the health monitor: it messages Jared on Telegram when anything
goes down, and again when it recovers).

**Do not touch** `ctzb-feed`, `ctzb-trades` or `ctzb-site`, any Access application, or any
existing binding, variable or secret except the ones this brief adds.

## Rules

- Never type, print, copy or echo a secret. Jared enters the bot token himself.
- Describe the screen before changing anything; ask before every write.
- If a screen doesn't match this brief, stop and describe it. Don't improvise.

---

## Phase 1 — ctzb-dashboard: new code only

**1.1** Workers & Pages → `ctzb-dashboard` → Edit code. Replace all of it with:

```
https://raw.githubusercontent.com/jaredbausch-ai/ctzb-data/0cdf3df83d83823293fce9c9a574e55e34a67070/cloudflare/ctzb-dashboard-worker.js
```

Check before deploying: exactly **65,188 bytes**; exactly one `export default`; it contains
`async function tick(`. If any of that differs, stop. Deploy. Change nothing else.

---

## Phase 2 — ctzb-scheduler: new code, bindings, Telegram

**2.1 Code.** Workers & Pages → `ctzb-scheduler` → Edit code. Replace all of it with:

```
https://raw.githubusercontent.com/jaredbausch-ai/ctzb-data/0cdf3df83d83823293fce9c9a574e55e34a67070/cloudflare/ctzb-scheduler-worker.js
```

Check: exactly **16,881 bytes**; the second line reads
` * CTZB external scheduler and health monitor — v3, 11 Nov 2026 (v2: 10 Nov).`; exactly one
`export default`. Deploy. Keep the existing `SCHED` KV binding, the `GITHUB_DISPATCH_TOKEN`
secret and the cron trigger `13,25,35,43 * * * *` exactly as they are.

**2.2 Find the alert namespace.** Open `ctzb-dashboard` → Settings → Bindings and note which
KV namespace its `NOTIFY` binding points to (the namespace's name, not its contents).

**2.3 Bindings on ctzb-scheduler** (Settings → Bindings → Add):

| Type | Name | Points to |
|---|---|---|
| Service binding | `MIRROR` | Worker `ctzb-feed` |
| Service binding | `TRADES` | Worker `ctzb-trades` |
| KV namespace | `NOTIFY` | the SAME namespace as ctzb-dashboard's `NOTIFY` (from 2.2) |

**2.4 Variable** (Settings → Variables and Secrets), type **Text**:

| Name | Value |
|---|---|
| `TELEGRAM_CHAT_ID` | the same value as the `TELEGRAM_CHAT_ID` variable on ctzb-dashboard |

**2.5 Secret** — Jared does this himself. Settings → Variables and Secrets → Add → type
**Secret**, name `TELEGRAM_BOT_TOKEN`. Hand over to Jared to paste the value: the same bot
token ctzb-dashboard uses (in Telegram: @BotFather → /mybots → the CTZB bot → API Token).
Do not look at, read back or screenshot the value. Save, and Deploy if Cloudflare asks.

---

## Phase 3 — verify

**3.1** Wait for the next tick (13, 25, 35 or 43 minutes past the hour). Jared should get one
Telegram message: "CTZB health monitor connected…". If 20 minutes pass with nothing, say so.

**3.2** Open `https://ctzb-scheduler.bigpapi.workers.dev/health`. Expect `"version": 3` and a
`monitor` block with `"telegram_configured": true` and `watching` showing `mirror`,
`trades` and `notifier` all `true`. Report the `problems` list exactly as shown (an empty
list is the good result).

**3.3** Report what 3.1 and 3.2 showed. Nothing in /health is secret.
