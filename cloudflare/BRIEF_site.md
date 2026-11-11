# Member site on Cloudflare — setup brief

For Claude in Chrome. 11 November 2026, item 18. A fifth Worker, `ctzb-site`, alongside
`ctzb-feed`, `ctzb-scheduler`, `ctzb-dashboard` and `ctzb-trades`. It serves the ETHKROS
member site behind a login, for Jared and Joe only during the private test run. It
reads live data from `ctzb-feed` and `ctzb-trades`; nothing in it is typed by hand.

**Do not touch** the other four Workers, their bindings, secrets or Access applications.

---

## Rules

- Do not create accounts, enter payment or billing details, or accept terms. Stop and say so.
- Never type, print or echo a secret. Jared enters secrets himself.
- Describe the screen before changing anything; ask before every write.
- If a screen doesn't match this brief, stop and describe it. Don't improvise.

---

## Phase 1 — the Worker

**1.1** Workers & Pages → Create → Worker → name `ctzb-site` → deploy the placeholder.

**1.2 Code.** Replace it with the file at this commit-pinned URL, then Deploy:

```
https://raw.githubusercontent.com/jaredbausch-ai/ctzb-data/dc52155eb6b68094f4b7033b9d6ed2d35a5410ff/cloudflare/ctzb-site-worker.js
```

Exact-match check before deploying: 85,046 bytes; the second line reads
` * ctzb-site — the ETHKROS member site, served from Cloudflare (item 18).`; exactly one
`export default`. Most of its size is one long line (the page, as a string). If any of
that differs, stop.

**1.3 Bindings** (Settings → Bindings):

| Type | Name | Points to |
|---|---|---|
| Service binding | `MIRROR` | Worker `ctzb-feed` |
| Service binding | `TRADES` | Worker `ctzb-trades` |

**1.4 Variable** (Settings → Variables and Secrets), type **Text**:

| Name | Value |
|---|---|
| `GATE_MODE` | `access` |

`ACCESS_TEAM_DOMAIN` and `ACCESS_AUD` come in Phase 2.

**1.5 Preview URLs.** Settings → Domains & Routes → **Preview URLs → Disable**.

No cron trigger: this Worker only answers page loads.

**At this point the site correctly serves nothing.** Every request gets "Forbidden" until
Access is set up. That's the gate failing closed, and it's expected.

---

## Phase 2 — the login (same Zero Trust organisation as the dashboard)

**2.1 Turn Access on.** Worker `ctzb-site` → Settings → Domains & Routes → the
`workers.dev` row → enable **Cloudflare Access**. This creates an Access application for
`ctzb-site.<subdomain>.workers.dev`.

**2.2 Who may log in.** Zero Trust → Access → Applications → that new application → its
policy: **Allow**, **Include → Emails**: **the email addresses Jared gives you directly**
(Jared's and Joe's; they are deliberately not written in this file, which is in a public
repo). Login method: **One-time PIN**. Show Jared the list before saving.

**2.3 Tell the Worker which application it is.** From the application's overview, copy the
**Application Audience (AUD) Tag**. Add two more **Text** variables on `ctzb-site`:

| Name | Value |
|---|---|
| `ACCESS_TEAM_DOMAIN` | the same team domain the dashboard uses, e.g. `something.cloudflareaccess.com` (no `https://`) |
| `ACCESS_AUD` | this application's AUD tag (not the dashboard's) |

Deploy if Cloudflare asks.

---

## Phase 3 — verify

**3.1 Login works.** In a private window, open `https://ctzb-site.<subdomain>.workers.dev`.
Expect the Access login; enter Jared's email, then the emailed code. The site loads:
ETHKROS header, "Market filter: on", a row of setup buttons above the card, the card
with a big percentage, "Data through" today's date at the bottom right.

**3.2 Tabs.** Click Chart, Record and How to read a card. Record lists about 137 rows.
The Chart tab for a forming setup may say "Chart data unavailable" until the pipeline
run after 00:00 UTC (7 PM Eastern) on 11 Nov writes the candle files; the example
button above the card always has a chart.

**3.3 Login refuses others.** New private window, an address not on the list: no code is
sent, or access is denied.

**3.4 Report** the site's address and what 3.1 to 3.3 showed. Don't share the link.
