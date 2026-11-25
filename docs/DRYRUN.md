# Private dry run — log

**Started 24 Nov 2026**, the day the round 48 audited site went live (ctzb-site ec13c062, ctzb-dashboard 18e5e173,
ctzb-trades 4a8f6b79, still dry run). Jared and Joe only: no outside members, nothing sold.

**Length:** one to two months before anything is sold (CONTEXT, launch plan). Earliest end **24 Dec 2026**; latest
planned end **24 Jan 2027**. Jared decides when it ends.

**What it has to show** (from the launch plan): the system runs on its own, every failover works when it is needed,
and every figure a member sees stays right.

**What is recorded here**, one row per event, newest first. Routine clean days are not logged; the morning health
check reports them to Jared's phone.
- an outage or a stale feed, and whether the system caught it and alerted
- a held or fail-closed run, and why
- a wrong or stale figure anyone finds on the site
- a missed, late or duplicate alert
- the relay: the first reduce, close, short and other-asset trade, checked against Coinbase (no test trades)
- any fix made during the run, with its commit

Everything on the site is computed signals measuring entry quality only: not trades, fills, a track record or a
return. The relay's dry-run page holds Jared's real trades privately; nothing from it is published until he switches
it live after Noah's sign-off.

| Date | Event | What happened | Caught and alerted? | Fix |
|---|---|---|---|---|
| 24 Nov 2026 | Start | Audited site, dashboard and relay deployed; relay health window fixed (5f4709e) | n/a | n/a |
| 24 Nov 2026 | Relay, first case | An open filled by two limit orders recorded as an open and an add; nothing posted | n/a | n/a |
