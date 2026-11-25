# Status panel for Joe — setup brief

For Claude in Chrome. 25 November 2026. One NEW Worker, `ctzb-status`: Joe's read-only status panel
(`/`, for an iframe on his dashboard) and the same figures as JSON (`/status.json`). It shows the pipeline state,
when the data last updated, setups forming and live, the relay up or down, and the day of the dry run. No trades,
prices, balances, keys or error texts. It holds no secret.

**Do not touch** any other Worker (`ctzb-feed`, `ctzb-trades`, `ctzb-site`, `ctzb-dashboard`, `ctzb-scheduler`),
any Access application, or any existing binding, variable or secret.

**No Access login on this Worker.** It must load inside Joe's dashboard, and everything on it is already public in
the feed (counts and times only).

## Rules

- Describe the screen before changing anything; ask before every write.
- If a screen doesn't match this brief, stop and describe it. Don't improvise.

---

**1. Create.** Workers & Pages → Create → Worker → start from "Hello World". Name it exactly `ctzb-status`. Deploy
the template as it is.

**2. Code.** `ctzb-status` → Edit code. Replace all of it with:

```
https://raw.githubusercontent.com/jaredbausch-ai/ctzb-data/ca8abefbb881f257c04b28574d593b2ef96ae8b3/cloudflare/ctzb-status-worker.js
```

Check before deploying: exactly **10,172 bytes**; the second line reads
` * ctzb-status — Joe's read-only status panel (25 Nov 2026).`; exactly one `export default`. If any of that
differs, stop. Deploy.

**3. Bindings** (`ctzb-status` → Settings → Bindings → Add):

| Type | Name | Points to |
|---|---|---|
| Service binding | `MIRROR` | Worker `ctzb-feed` |
| Service binding | `TRADES` | Worker `ctzb-trades` |

Nothing else: no variables, no secrets, no KV, no cron trigger.

**4. Check.** Open `https://ctzb-status.bigpapi.workers.dev/` and report what each row says (Pipeline, Data last
updated, Setups, Lead-trader relay, Private dry run). Then open `/status.json` and report `pipeline.state`,
`setups` and `relay.state`. Report the deployed version id.
