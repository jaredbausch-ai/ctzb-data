# Lead trader's real trades on Cloudflare — setup brief

For Claude in Chrome (or any agent driving Jared's browser). 11 November 2026, item 13a.
A fourth Worker, `ctzb-trades`, alongside `ctzb-feed`, `ctzb-scheduler` and
`ctzb-dashboard`. It reads Jared's Coinbase futures trades with a **view-only** key and
records them as "the lead trader's real trades". It starts in **dry run**: nothing is
public until Jared switches it live, after counsel (Noah) signs off.

**Do not touch** the other three Workers, their bindings or their secrets.

---

## Rules

- Do not create accounts, enter payment or billing details, or accept terms. Stop and say so.
- **Never read out, copy, type, print or echo a secret.** That includes the Coinbase
  private key and key name. Jared enters every secret himself. You may confirm a secret's
  *name* appears in a list; never its value.
- Never give the Coinbase key any permission except **View**.
- Describe the screen before changing anything; ask before every write.
- If a screen doesn't match this brief, stop and describe it. Don't improvise.

---

## Phase 1 — the Coinbase view-only key (Jared, with the agent guiding)

The key from 24 Oct is locked to Joe's IP address, so it can't be used from Cloudflare.
This is a new key, for this Worker only.

**1.1** Open `https://portal.cdp.coinbase.com/api-keys/secret` and sign in with the
Coinbase account that holds the perps. If it asks to create a developer project, choose
the free default and report it. Stop at any payment screen.

**1.2** Click **Create API key**. Nickname: `ctzb-trades read-only`.

**1.3** Open **API restrictions**:

| Setting | Value |
|---|---|
| Portfolio | the portfolio the perps trade in (usually **Default**). Ask Jared if there's more than one |
| Permissions | **View** only. **Trade** and **Transfer** must be unchecked |
| IP allowlist | **leave empty** (see below) |

Why no IP allowlist: Cloudflare Workers don't call out from fixed addresses, so an
allowlist would block every request. The protection is that the key can only read.

**1.4** Open **Advanced settings** → signature algorithm **ECDSA**. Not Ed25519;
Coinbase's trading APIs don't accept it, and the Worker refuses it.

**1.5** Show Jared the settings, then click **Create API key**.

**1.6 STOP. Jared only from here.** The screen now shows the **API key name** (it starts
`organizations/…/apiKeys/…`) and the **private key** (a block starting
`-----BEGIN EC PRIVATE KEY-----`). The agent looks away from this screen: no reading,
no copying, no screenshots. Jared either keeps this window open for Phase 3 or clicks
**Download API key** and saves the file somewhere private on his computer. It goes
nowhere else: not a chat, not an email, not the repo.

**1.7** Back on the key list, confirm the new key shows **View** as its only permission.

---

## Phase 2 — the Worker (agent)

**2.1 KV namespace.** Storage & Databases → KV → Create: `CTZB_TRADES`.

**2.2 Worker.** Workers & Pages → Create → Worker → name `ctzb-trades` → deploy the
placeholder.

**2.3 Code.** Replace it with the file at this commit-pinned URL, then Deploy:

```
https://raw.githubusercontent.com/jaredbausch-ai/ctzb-data/19e7c37f1d1586f95a624e9f55e7fdfd5c58fa47/cloudflare/ctzb-trades-worker.js
```

Exact-match check before deploying: about 21.8 KB (21,762 bytes); the first line reads
`// ctzb-trades — the lead trader's real trades, relayed from Coinbase (item 13a).`;
exactly one `export default`. If any of that differs, stop.

**2.4 Binding** (Settings → Bindings):

| Type | Name | Points to |
|---|---|---|
| KV namespace | `TRADES` | `CTZB_TRADES` |

**2.5 Variable** (Settings → Variables and Secrets), type **Text**, not Secret:

| Name | Value |
|---|---|
| `MODE` | `dry` |

**2.6 Cron trigger.** One trigger: `* * * * *` (every minute).

**2.7 Preview URLs.** Settings → Domains & Routes → **Preview URLs → Disable**.

---

## Phase 3 — Jared: the three secrets

Worker `ctzb-trades` → Settings → Variables and Secrets → Add → type **Secret**, three times:

| Name | Value |
|---|---|
| `COINBASE_KEY_NAME` | the API key name from 1.6, the whole `organizations/…/apiKeys/…` string |
| `COINBASE_PRIVATE_KEY` | the whole private key from 1.6, **including** the `-----BEGIN…` and `-----END…` lines |
| `DRY_VIEW_PASSWORD` | a password Jared picks, to open the dry-run page |

The agent may confirm the three names appear; never the values.

---

## Phase 4 — verify (agent)

Wait three minutes after the secrets are in. Use the Worker's `workers.dev` address.

**4.1** Open `/health`. Expect `"mode": "dry"`, a `baseline_at` time, `"consecutive_failures": 0`
and `"ok": true`.

If `last_error` says **HTTP 401**: the key name and private key don't match, or the key
isn't permitted on that portfolio. Stop and report; Jared re-enters the two secrets.
If it says **not set** or **could not be read**: a secret is missing or was pasted
without its BEGIN/END lines. Stop and report.

**4.2** In a private window, open `/dry`. The browser asks for a login: any username,
and the `DRY_VIEW_PASSWORD`. Expect JSON with `"trades": []` and `open_positions`
matching what Jared holds on Coinbase right now (direction and average entry). Positions
open before today are marked `from_baseline` and are never posted.

**4.3** Open `/trades.json`. Expect **404, "Not live yet: dry run."** That's correct.

---

## Phase 5 — the dry run (Jared)

Trade as normal. After each trade, open `/dry` and check the new entry against Coinbase:
direction, open / add / reduce / close, price, leverage, size %, and on exits the move %
and account %. Anything odd shows up under `review_notes`.

**Going live is Jared's switch, after Noah signs off:** change `MODE` from `dry` to
`live`. Only trades made from then on are published; the dry-run history never is.
The agent does not make this change.

---

## What the Worker does, briefly

Every minute it reads new futures fills, positions and the futures balance, using a
fresh signed token per request. The fills of one order become one trade at their
average price. BTC and ETH only; anything else is ignored. A record shows time, asset,
long or short, open / add / reduce / close, price, leverage and size as a percentage of
the account, never dollar amounts, contract counts or balances. If its own count of a
position ever disagrees with Coinbase, Coinbase wins and the correction is logged for
review, never posted. It writes to storage only when something changes, plus a check-in
every 15 minutes, which keeps it well inside Cloudflare's free limits.
