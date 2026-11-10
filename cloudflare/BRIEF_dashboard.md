# CTZB dashboard on Cloudflare — build brief

For Claude in Chrome. 10 November 2026. A third Worker, `ctzb-dashboard`, alongside
`ctzb-feed` (the mirror) and `ctzb-scheduler`, which are both live. It serves the
ETH Setup Standard dashboard behind a login, and sends Jared's phone alerts through a
private Telegram bot.

**Do not touch** the claude.ai dashboard (`claude.ai/artifact/6tH6hXMh3EYLvUUEM9XgSJ`)
or the "CTZB dashboard refresh" scheduled task. The old and new run side by side until
the new one is checked; retiring the old one is a separate step.

---

## Rules — unchanged

- Do not create accounts, enter payment or billing details, or accept terms. Stop and say so.
- Never type, print or echo a secret value. Jared enters secrets himself.
- Describe the screen before changing anything; ask before every write.
- If a screen doesn't match this brief, stop and describe it. Don't improvise.

---

## Phase 0 — Jared, on his phone (about 3 minutes)

**0.1 Create the bot.** In Telegram, message **@BotFather** → `/newbot` → name it
`CTZB alerts` → give it a username ending in `bot`. BotFather replies with a **token**.
Keep it; it goes into Cloudflare in Phase 4. Don't paste it into any chat.

**0.2 Start it.** Open the new bot and tap **Start**. A bot cannot message anyone who
hasn't done this.

**0.3 Get your chat id.** Message **@userinfobot**. It replies with your numeric **Id**.
That number is `TELEGRAM_CHAT_ID`. It isn't a secret, but don't post it publicly.

---

## Phase 1 — Zero Trust, check before building

The login gate is **Cloudflare Access**, part of Cloudflare Zero Trust. Its free plan
covers up to 50 users.

**1.1** Open **Zero Trust** from the account dashboard. If a Zero Trust organisation
already exists, report its **team domain** (`<name>.cloudflareaccess.com`) and go on.

**1.2** If it asks to create one: proceed only as far as choosing the **Free** plan.
**If it asks for a payment method, STOP.** Report it. Jared decides; there is a
fallback (see the end).

---

## Phase 2 — the Worker

**2.1 KV namespace.** Storage & Databases → KV → Create: `CTZB_NOTIFY`.

**2.2 Worker.** Workers & Pages → Create → Worker → name `ctzb-dashboard` → deploy the
placeholder.

**2.3 Code.** Replace it with the file at this commit-pinned URL, exact-match check as
before, then Deploy:

```
https://raw.githubusercontent.com/jaredbausch-ai/ctzb-data/e43c0f87633243a40bbd491c6251a8e3984f1246/cloudflare/ctzb-dashboard-worker.js
```

About 63 KB. The first comment line reads "ctzb-dashboard — the ETH Setup Standard
dashboard, served from Cloudflare." Most of its size is one long line: the page itself,
as a string. It has exactly one `export default`.

**2.4 Bindings** (Settings → Bindings):

| Type | Name | Points to |
|---|---|---|
| Service binding | `MIRROR` | Worker `ctzb-feed` |
| KV namespace | `NOTIFY` | `CTZB_NOTIFY` |

**2.5 Variables** (Settings → Variables and Secrets), type **Text**, not Secret:

| Name | Value |
|---|---|
| `GATE_MODE` | `access` |
| `TELEGRAM_CHAT_ID` | Jared's number from 0.3 |

`ACCESS_TEAM_DOMAIN` and `ACCESS_AUD` come in Phase 3.

**2.6 Cron trigger.** One trigger: `5,20,35,50 * * * *`.

**At this point the dashboard correctly serves nothing.** Until Access is configured,
every request gets "Forbidden". That's the gate failing closed, and it's expected.

---

## Phase 3 — the login

**3.1 Turn Access on for the Worker.** Worker → Settings → Domains & Routes → the
`workers.dev` row → enable **Cloudflare Access**. This creates an Access application
for `ctzb-dashboard.<subdomain>.workers.dev`.

**3.2 Who may log in.** Open that Access application's policy (Zero Trust → Access →
Applications). Set it to **Allow**, with **Include → Emails**:

**the email addresses Jared gives you directly** (they are deliberately not written in
this file, which sits in a public repo).

Login method: **One-time PIN** (a code is emailed; no other identity provider is needed).
Show Jared the email list before saving.

**3.3 Tell the Worker which application it is.** From the Access application's overview,
copy the **Application Audience (AUD) Tag**. Add two more **Text** variables on
`ctzb-dashboard`:

| Name | Value |
|---|---|
| `ACCESS_TEAM_DOMAIN` | the team domain, e.g. `something.cloudflareaccess.com` (no `https://`) |
| `ACCESS_AUD` | the AUD tag |

The Worker checks every login token against these itself, so a token for any other
application, or no token at all, gets nothing.

**3.4 Preview URLs.** Worker → Settings → Domains & Routes → **Preview URLs → Disable**.
The Worker would refuse them anyway; this just removes the extra door.

---

## Phase 4 — Jared: the bot token

Worker `ctzb-dashboard` → Settings → Variables and Secrets → Add → type **Secret**:
`TELEGRAM_BOT_TOKEN` = the token from 0.1. The agent may confirm the name appears;
never the value.

---

## Phase 5 — verify

**5.1 Login works.** In a private window, open the Worker's workers.dev URL. Expect the
Cloudflare Access login, enter Jared's email, then the emailed code. The
dashboard loads with data: DATA THROUGH shows today's date, and the prints table has
rows.

**5.2 Login refuses others.** In a new private window, enter an address that isn't on
the list. Expect no code to be sent, or access denied.

**5.3 Health.** While logged in, open `/health`. Expect `"mirror": "ok"`,
`"gate": "access"`, `"alerts": {"configured": true, ...}`.

**5.4 Telegram.** While logged in on the dashboard page, run once in its console:

```js
fetch('/alerts/test', {method: 'POST'}).then(r => r.json()).then(console.log)
```

Expect `{sent: true, telegram_status: 200}`, and Jared's phone gets "CTZB alerts are
connected." A `telegram_status` of 400 or 403 almost always means the bot wasn't
started (0.2) or the chat id is wrong (0.3). The endpoint allows one test every 10
minutes.

Report the workers.dev URL and the result of each check.

---

## Fallback, only if Phase 1 hits a payment wall

Skip Phase 3. Set `GATE_MODE` to `password`. Jared adds a Secret `DASHBOARD_PASSWORD`.
The browser then shows a username/password prompt (any username, that password). It's
one shared password instead of per-person logins, so Jared gives it to Joe directly,
not by email. Everything else is the same.
