"""Write the CTZB live feed: one versioned JSON file per pipeline run.

This is the "one feed" in the live-feed plan sent to Joe (docs/joe/
2026-10-28_live_feed_proposal_SENT.md, settled 31 Oct). Every screen on Joe's
side (admin portal, member site, alerts, his Grok AI) is meant to read this
file instead of emailed copies. The Cloudflare backend that serves views per
audience will read it too, once the ETHKROS Cloudflare account exists.

Rules (docs/FEED_SPEC.md):
  - fields are only ever added, never renamed or removed; schema_version is 6
    (the additions alert_log and alert_log_carry, 13 Nov 2026, and alerts_held, 14 Nov, were made at 6 without a bump)
  - every record carries the computed-signal label
  - cards, live signals, the example and every figure from the run's datasets are withheld
    (cards_withheld true) whenever the stack check, the card cross-check or any gating step
    failed; a broken seal, a damaged alert log or a failed strict check publishes the
    fail-closed feed
  - it only repackages datasets/*.csv written earlier in the same run; it
    computes no figure of its own (it stamps the time, the schema version, the posting bar constant
    and the aliases, and words the labels)
  - (schema 4, 10 Nov 2026, item 17d) every card, print and open signal carries
    a signal_id = chart + confirmation date, which is the same at every stage of
    a signal's life. "alerts" lists the events in their delivery window
    (at least 24 hours; carried_alerts) -- forming, confirmed, vanished --
    each with a fixed alert_id; it is empty on held feeds. feed/alert_log.csv
    is an append-only record of every alert_id ever emitted, committed with the
    feed, so each event is emitted once however many runs happen. An emitted
    alert stays in "alerts" for its delivery window (carried_alerts, 14 Nov 2026),
    so senders must never send an alert_id twice.
  - (schema 5, 11 Nov 2026, item 18) the member card figures written by
    extras_live.py: if_it_misses, odds_fade, past_paths. Withheld (empty, with
    extras_withheld true) when that step failed this run, so a stale copy from an
    earlier run is never served. They never gate cards or alerts.
  - cards AND alerts are withheld when ANY scoring check in the run failed
    (refresh, grade, stack, cards, regression guard), not only the stack check.
    Withheld alerts are not logged, so they go out on the next clean run.

Usage: python feed_live.py [--datasets datasets] [--out feed/ctzb_feed.json]
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
import hashlib
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feedcheck  # noqa: E402
import seal  # noqa: E402

EXTRAS_FILES = seal.EXTRAS_FILES   # what extras_live.py writes


def now_utc():
    """Real time, or CTZB_NOW (ISO 8601) when a test replays a past run; same rule as clock.py,
    inlined because the tests run this file from a copy of its own."""
    v = os.environ.get("CTZB_NOW")
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc) if v else datetime.now(timezone.utc)

SCHEMA_VERSION = 6   # 6 (12 Nov 2026): every field added on 11-12 Nov (the +10% switch and audits #1-#14), batched
POSTING_BAR = 70     # WINMIN in refresh.py / EDGE_BAR in stack_live.py (tests/test_feed_extras.py checks they agree)
ALERT_LOG_FIELDS = ["alert_id", "event", "signal_id", "chart", "emitted_at"]
# The delivery window (14 Nov 2026 audit #28). The sender reads the feed from the mirror, which pulls every 15
# minutes; a feed replaced sooner (a red run's 1-minute retry) may never be seen, and its alerts were lost while the
# log marked them sent. So every clean feed carries, from the alert log itself, every alert emitted in the last
# ALERT_HOLD_HOURS; an older one stays while the previous feed carried it and that feed was held or had stood less
# than ALERT_STAND_MINUTES. Held and fail-closed feeds send nothing; they keep the alerts in `alerts_held` so the
# next clean feed carries them on. When the previous feed cannot be read (or its list is not a list of alerts), what
# was delivered is unknown, so every alert of the last ALERT_RECOVER_DAYS is carried (the sender sends each once).
ALERT_HOLD_HOURS = 24
ALERT_STAND_MINUTES = 60
ALERT_RECOVER_DAYS = 7
# Steps whose failure withholds cards and alerts. Passed in by daily.yml as
# CTZB_STEP_OUTCOMES="refresh=success,grade=success,...". Absent = run by hand.
GATING_STEPS = ("refresh", "grade", "stack", "cards", "regress")
LABEL = ("Computed signal, not a fill. No trade was taken. Entry quality only: "
         "the data has no exits, so this is not a strategy return or a track record.")


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def num(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
        if x == 0:
            x = 0.0   # never -0.0 in the feed (audit #17)
        return int(x) if x.is_integer() and "." not in str(v) else x
    except ValueError:
        return v


def sid(chart, date):
    """Stable signal id: chart + confirmation date. 'ETH 1D', '2026-11-12' -> 'ETH-1D-2026-11-12'."""
    return f"{chart.replace(' ', '-')}-{date}" if chart and date else None


def step_outcomes():
    out = {}
    for part in os.environ.get("CTZB_STEP_OUTCOMES", "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def read_log(path):
    return rows(path)


def log_bytes(all_rows):
    """The alert log's exact bytes for these rows (what write_log writes)."""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=ALERT_LOG_FIELDS, extrasaction="ignore")
    w.writeheader()
    w.writerows(all_rows)
    return buf.getvalue().encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def atomic_write(path, data):
    """Write the whole file or nothing: a crash part-way leaves the old file in place (13 Nov 2026 audit #22)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_log(path, all_rows):
    atomic_write(path, log_bytes(all_rows))


def log_state(path):
    """sha256 and row count of the alert log as it is on disk (None when there is no log)."""
    if not os.path.exists(path):
        return None
    b = open(path, "rb").read()
    return {"sha256": sha(b), "rows": max(0, b.count(b"\n") - 1)}


def check_log(log_path, prev_feed_path):
    """13 Nov 2026 audit #22: the alert log must be exactly the one the last published feed left behind.
    A log that was deleted, cut, emptied or replaced by an older copy would lose an alert or send one twice.
    Returns the log's rows. If the last run published its feed but died before writing the log, the log is
    rebuilt from that feed's own alerts (the feed went out, so they were sent). Anything else raises, which
    publishes the withheld feed."""
    prev = None
    try:
        with open(prev_feed_path) as f:
            prev = json.load(f)
    except (OSError, ValueError):
        prev = None
    want = (prev or {}).get("alert_log") if isinstance(prev, dict) else None
    have = log_state(log_path)
    cur = read_log(log_path) if have else []
    if not want:
        # no record to check against: the first run under this rule, or no previous feed
        if have is None:
            raise RuntimeError("the alert log is missing and no published feed records it; to start a new log on "
                               "purpose, run once with CTZB_SEED_ALERT_LOG=1")
        return cur
    if have and have["sha256"] == want["sha256"]:
        return cur
    # alerts a published feed carried that never reached the log: its own, plus any carried forward through
    # fail-closed feeds since (13 Nov 2026 audit #24: one crashed run in between used to lock every later run)
    # (since 14 Nov 2026 `alerts` also carries alerts already logged: only the ones the log lacks are appended)
    have_ids = {r.get("alert_id") for r in cur}
    unlogged = [x for x in (prev.get("alert_log_carry") or []) + (prev.get("alerts") or [])
                if isinstance(x, dict) and x.get("alert_id") not in have_ids]
    unlogged = [x for i, x in enumerate(unlogged) if x.get("alert_id") not in {y.get("alert_id") for y in unlogged[:i]}]
    rebuilt = cur + [{k: x.get(k) for k in ALERT_LOG_FIELDS} for x in unlogged]
    if sha(log_bytes(rebuilt)) == want["sha256"]:
        write_log(log_path, rebuilt)   # the last run died between publishing the feed and writing the log
        return rebuilt
    raise RuntimeError("the alert log is not the one the last published feed left "
                       f"({(have or {}).get('rows', 'no')} rows on disk, {want.get('rows')} expected)")


def _ts(v):
    try:
        return datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def prev_carry(prev):
    """The alerts the previous feed was carrying: its `alerts` when it was clean, its `alerts_held` when not. None
    when that feed cannot be read or the list is not a list of alerts: the chain is broken."""
    if not isinstance(prev, dict):
        return None
    src = prev.get("alerts_held") if prev.get("alerts_withheld") is True else prev.get("alerts")
    if not isinstance(src, list) or not all(isinstance(x, dict) and isinstance(x.get("alert_id"), str) for x in src):
        return None
    return src


def log_ok(log_rows):
    """Every row has exactly the log's columns (an alert log with a renamed or missing column cannot be read)."""
    return all(isinstance(r, dict) and list(r) == ALERT_LOG_FIELDS for r in log_rows)


def carried_alerts(prev, log_rows, now, keep_all=False):
    """Alerts an earlier run emitted that stay in this feed (the delivery window above), in log order. Only alerts
    the alert log records are carried, rebuilt from the log's own rows (a previous feed whose alert_log record
    matches the log plus its own alerts is trusted to have written them, as for a run that died before the log).
    keep_all (a held run): nothing leaves while nothing is being sent."""
    chain = prev_carry(prev)
    ids = {x["alert_id"] for x in chain} if chain is not None else set()
    stood = None
    if chain is not None and prev.get("alerts_withheld") is not True:
        g = _ts(prev.get("generated_at"))
        stood = (now - g).total_seconds() / 60 if g else None
    out, seen = [], set()
    for r in log_rows:
        aid = r.get("alert_id")
        if r.get("emitted_at") == "seeded" or not isinstance(aid, str) or aid in seen:
            continue
        e = _ts(r.get("emitted_at"))
        age_h = (now - e).total_seconds() / 3600 if e else None
        if chain is None:
            keep = age_h is not None and age_h < ALERT_RECOVER_DAYS * 24
        else:
            keep = (age_h is not None and age_h < ALERT_HOLD_HOURS) or \
                   (aid in ids and (keep_all or stood is None or stood < ALERT_STAND_MINUTES))
        if keep:
            seen.add(aid)
            out.append({"alert_id": aid, "event": r.get("event"), "signal_id": r.get("signal_id"),
                        "chart": r.get("chart"), "emitted_at": r.get("emitted_at"), "label": LABEL})
    return out


def pending_alerts(forming, confirmed, log_rows):
    """Events not yet in the log. forming/confirmed: {signal_id: chart}."""
    logged = {(r["signal_id"], r["event"]) for r in log_rows}
    out = []
    for s_, ch in sorted(forming.items()):
        if (s_, "forming") not in logged and (s_, "confirmed") not in logged:
            out.append(("forming", s_, ch))
    for s_, ch in sorted(confirmed.items()):
        if (s_, "confirmed") not in logged:
            out.append(("confirmed", s_, ch))
    alerted_forming = {r["signal_id"]: r["chart"] for r in log_rows if r["event"] == "forming"}
    finished = {r["signal_id"] for r in log_rows if r["event"] in ("confirmed", "vanished")}
    for s_, ch in sorted(alerted_forming.items()):
        if s_ in finished or s_ in forming or s_ in confirmed:
            continue
        out.append(("vanished", s_, ch))
    return out


def stack_check(path):
    lines = open(path).read().strip().splitlines() if os.path.exists(path) else []
    failed = [l for l in lines if "FAILED" in l]
    ok = bool(lines) and not failed
    return ok, lines


def card(r):
    return {
        "label": LABEL,
        "signal_id": sid(r["chart"], r["confirms"]),
        "chart": r["chart"],
        "asset": r["asset"],
        "timeframe": r["tf"],
        "low_date": r["trough"],
        "low_day": r.get("lowDay") or r["trough"],  # the day the low printed (12 Nov 2026); low_date is its bar's open date
        "confirms_on": r["confirms"],
        "bars_to_confirm": num(r["barsNeeded"]),
        "must_close_above": num(r["killClose"]),
        "price_now": num(r["priceNow"]),     # forming: today's price (stand-in for the entry); live: today's price; example: none
        "entry_close": num(r.get("entryClose", "")),   # live and example: the actual entry close; forming: not yet known
        "grade": r["grade"],
        "confirmations": r["lenses"],
        "sample": r["basis"],
        "past_trades": num(r["n"]),
        "rose10_never_fell25_within60d_pct": num(r["surv10"]),
        "beat_normal_move_pct": num(r["scaled20"]),
        "rose20_within60d_pct": num(r["reach20"]),
        "rose10_within60d_pct": num(r["reach10"]),
        "typical_biggest_rise_pct": num(r["bestMove"]),
        "typical_dip_before_rise_pct": num(r["dipBeforeHigh"]),
        "typical_deepest_dip_pct": num(r["maxDip60"]),
        # unrounded, for prices built from them (12 Nov 2026 audit); display the rounded ones
        "typical_biggest_rise_exact_pct": num(r.get("bestMoveExact", "")),
        "typical_dip_before_rise_exact_pct": num(r.get("dipBeforeHighExact", "")),
        "typical_deepest_dip_exact_pct": num(r.get("maxDip60Exact", "")),
        "fell30_within60d_pct": num(r["touched30"]),
        "before_2022": {"past_trades": num(r["nOld"]), "rose10_never_fell25_within60d_pct": num(r["surv10Old"])},
        "since_2022": {"past_trades": num(r["nNew"]), "rose10_never_fell25_within60d_pct": num(r["surv10New"])},
        "typical_day_first_rose10": num(r.get("daysTo10", "")),
        "typical_day_first_rose20": num(r.get("daysTo20", "")),
        "typical_day_of_60d_high": num(r.get("daysToHigh", "")),
        "typical_day_of_deepest_dip": num(r.get("daysToLow", "")),
        "active_confluences": [
            {"after": f"{x['after']} {x['afterTag']}", "after_confirmed": x["confirmed"], "window_closes": x["closes"],
             "applies_to": x["tag"], "past_trades": x["n"], "rose20_within60d_pct": num(x["reach20"]),
             "rose10_within60d_pct": num(x["reach10"]), "fell30_within60d_pct": num(x["touched30"]),
             "note": "Its own sample, separate from the card number; rows overlap and are not added."}
            for x in json.loads(r.get("confluences") or "[]")
        ],
        # the ladder's first row (12 Nov 2026 audit #5): from entry, rose 10% before ever falling 25.3%
        "from_entry": {"past_trades": num(r["n"]), "still_rose10_pct": num(r.get("l0ok", "")), "went_on_to_fall25_pct": num(r.get("l0liq", "")),
                       "still_rose10_exact_pct": num(r.get("l0okExact", ""))},
        "if_it_falls_first": [
            {"fell_pct": k, "past_trades": num(r[f"l{k}n"]),
             "still_rose10_pct": num(r[f"l{k}ok"]), "went_on_to_fall25_pct": num(r[f"l{k}liq"]),
             "still_rose10_exact_pct": num(r.get(f"l{k}okExact", ""))}
            for k in (5, 10, 15, 20)
        ],
    }


def signal_aliases(o):
    """Audit #7 (12 Nov 2026): no signal was traded, so every `past_trades` gains a `past_signals` twin and
    `trades_a_year` a `signals_a_year` twin, same values, placed right after. The old names stay (fields are
    never renamed)."""
    if isinstance(o, list):
        return [signal_aliases(x) for x in o]
    if not isinstance(o, dict):
        return o
    out = {}
    for k, v in o.items():
        out[k] = signal_aliases(v)
        if k == "past_trades":
            out["past_signals"] = out[k]
        elif k == "trades_a_year":
            out["signals_a_year"] = out[k]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", default="datasets")
    ap.add_argument("--out", default="feed/ctzb_feed.json")
    ap.add_argument("--alert-log", default="feed/alert_log.csv")
    a = ap.parse_args()
    d = lambda name: os.path.join(a.datasets, name)

    status = {r["item"]: r["value"] for r in rows(d("status.csv"))}
    ok, check_lines = stack_check(d("stack_status.txt"))
    steps = step_outcomes()
    # A real run names every gating step. Anything but "success" (failure, skipped, cancelled, missing, a typo)
    # withholds; only a hand run with no CTZB_STEP_OUTCOMES at all is taken on the checks below alone.
    failed_steps = [k for k in GATING_STEPS if steps.get(k) != "success"] if os.environ.get("CTZB_STEP_OUTCOMES", "").strip() else []
    all_ok = ok and not failed_steps
    # 13 Nov 2026 audit #21: a clean run always writes these (stack_live.py). If one is gone after the checks
    # passed, the feed must not read as a quiet market: crash here, which publishes the withheld feed.
    if all_ok:
        # the candle check's own verdict (13 Nov 2026 audit #22): a run whose candles failed the structural check
        # must not publish, whatever the later steps did
        try:
            with open(d("candle_check.json")) as f:
                cc0 = json.load(f)
        except (OSError, ValueError):
            cc0 = None
        if os.environ.get("CTZB_STEP_OUTCOMES", "").strip() and not (isinstance(cc0, dict) and cc0.get("structural_ok") is True):
            raise RuntimeError("candle_check.json does not say the candles passed the structural check")
        gone = [f for f in ("cards.csv", "open.csv", "cards_open.csv", "cards_example.csv", "prints.csv") if not os.path.exists(d(f))]
        if gone:
            raise RuntimeError("missing after a clean run: " + ", ".join(gone))
        # the run seal (seal.py): every scoring step finished, in order, and no file in datasets/ has changed
        # since the step that wrote it. The member-card extras are not a gating step: when that step failed its
        # files are withheld below, so their state is not held against the cards.
        extras_failed = steps.get("extras") == "failure"
        broken = seal.problems(a.datasets, need=("refresh", "grade", "stack", "cards") + (() if extras_failed else ("extras",)),
                               ignore=EXTRAS_FILES if extras_failed else ())
        old = seal.age_problem(a.datasets)   # a hand run of this step alone, later, is not this run (audit #25)
        if old:
            broken = broken + [old]
        if broken:
            raise RuntimeError("the run seal is broken: " + "; ".join(broken[:5]))
    # status.csv is refresh.py's. If refresh failed this run, the file is the last good run's, and its market
    # filter reading and dates are not today's (audit #21: a held feed repeated "on" after the filter turned off).
    if not all_ok:
        status = {}   # 13 Nov 2026 audit #22: also when refresh was reported as anything but "success"
    cards = [card(r) for r in rows(d("cards.csv"))] if all_ok else []
    # the member site's worked example, as a real card from what was known at its alert (12 Nov 2026)
    ex_rows = rows(d("cards_example.csv")) if os.path.exists(d("cards_example.csv")) else []
    example_card = dict(card(ex_rows[0]), example=True) if all_ok and ex_rows else None
    open_cards = {(r["chart"], r["confirms"]): card(r) for r in (rows(d("cards_open.csv")) if os.path.exists(d("cards_open.csv")) else [])} if all_ok else {}
    now = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- alerts: once per event, ever (item 17d) ----
    forming = {sid(r["chart"], r["confirms"]): r["chart"] for r in rows(d("cards.csv")) if r.get("confirms")}
    confirmed = {sid(r["chart"], r["confirms"]): r["chart"] for r in rows(d("prints.csv")) if r["state"] == "confirmed"}
    confirmed.update({sid(r["chart"], r["entry"]): r["chart"] for r in rows(d("forward.csv"))})
    seed = os.environ.get("CTZB_SEED_ALERT_LOG") == "1"
    log_rows = read_log(a.alert_log) if seed and os.path.exists(a.alert_log) else ([] if seed else check_log(a.alert_log, a.out))
    alerts, seeded = [], False
    log_dirty = False   # the alert log is written only once the feed has passed its strict check (13 Nov 2026)
    try:
        with open(a.out) as f:
            prev_feed = json.load(f)
    except (OSError, ValueError):
        prev_feed = None
    held = []
    if not all_ok:
        # withheld: nothing emitted, nothing logged -- the next clean run sends it; alerts already emitted are kept
        held = [] if seed else carried_alerts(prev_feed, log_rows, now_utc(), keep_all=True)
    elif seed:
        # A new log, on purpose only (CTZB_SEED_ALERT_LOG=1): record what is already live without alerting on
        # it, or day one would announce every signal currently on the books. A log that is simply missing is
        # not a reason to start over (13 Nov 2026 audit #22): check_log fails the run instead.
        seeded = True
        log_rows = [{"alert_id": f"{s_}:forming", "event": "forming", "signal_id": s_, "chart": ch, "emitted_at": "seeded"}
                    for s_, ch in sorted(forming.items())] + \
                   [{"alert_id": f"{s_}:confirmed", "event": "confirmed", "signal_id": s_, "chart": ch, "emitted_at": "seeded"}
                    for s_, ch in sorted(confirmed.items())]
        log_dirty = True
    else:
        alerts = carried_alerts(prev_feed, log_rows, now_utc())
        new_events = pending_alerts(forming, confirmed, log_rows)
        for ev, s_, ch in new_events:
            aid = f"{s_}:{ev}"
            alerts.append({"alert_id": aid, "event": ev, "signal_id": s_, "chart": ch,
                           "emitted_at": now, "label": LABEL})
            log_rows.append({"alert_id": aid, "event": ev, "signal_id": s_, "chart": ch, "emitted_at": now})
        if new_events:
            log_dirty = True

    feed = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now,
        # the 70% bar below which a setup's edge is gone; top level so a card's ladder can be read against it
        # even when odds_fade is withheld (12 Nov 2026 audit #14)
        "posting_bar_pct": POSTING_BAR,
        "scored_as_of": status.get("Scored as of"),
        "label": LABEL,
        "checks": {"passed": ok, "lines": check_lines,
                   "all_passed": all_ok, "steps": steps, "failed_steps": failed_steps},
        "cards_withheld": not all_ok,
        "alerts_withheld": not all_ok,
        "alerts_seeded": seeded,
        "alerts": alerts,
        "alerts_held": held,
        "market_regime": status.get("Market regime"),
        "next_buy_date": status.get("Next buy date"),
        "trades_a_year": status.get("Trades a year"),
        "cards": cards,
        "example_card": example_card,
        "prints": [
            {"label": LABEL, "signal_id": sid(r["chart"], r["confirms"]), "chart": r["chart"], "state": r["state"],
             "provisional": r["state"] != "confirmed",
             "low_date": r["trough"], "confirms_on": r["confirms"],
             "entry_close": num(r["entry"]), "tags": r["tags"], "note": r["note"]}
            for r in rows(d("prints.csv"))
        ] if all_ok else [],
        # every signal inside its 60 days, ETH and BTC, from stack_live's open.csv (12 Nov 2026 audit);
        # each carries its own card (sample, ladder, edge). Dated by the confirmation close.
        "open_signals": [
            {"label": LABEL, "signal_id": sid(r["chart"], r["entry"]), "chart": r["chart"], "entry_date": r["entry"],
             "entry_close": num(r["entryClose"]), "tags": r["tag"], "grade": r["grade"],
             "confirmations": r["lenses"], "days_elapsed": num(r["elapsed"]),
             "day10_pct": num(r["d10"]), "day30_pct": num(r["d30"]), "day60_pct": num(r["d60"]),
             "best_so_far_pct": num(r["best"]), "worst_so_far_pct": num(r["worst"]),
             # 12 Nov 2026 audit #9: the setup's own edge level (its card's ladder, exact shares) and whether it
             # was lost: whichever came first on closed daily bars, the edge level or +10%
             "edge_level_pct": num(r.get("edgeLevel", "")), "edge_status": r.get("edgeStatus") or None,
             "card": open_cards.get((r["chart"], r["entry"]))}
            for r in (rows(d("open.csv")) if os.path.exists(d("open.csv")) else [])
        ] if all_ok else [],
        "confluence_windows": [
            {"opened_by": r["openedBy"], "confirmed": r["confirmed"],
             "closes": r["closes"], "applies_to": r["appliesTo"]}
            for r in rows(d("windows.csv"))
        ] if all_ok else [],
        "grade_odds": [
            {"label": LABEL, "asset": r["asset"], "grade": r["grade"], "past_trades": num(r["n"]),
             "rose10_within60d_pct": num(r["reach10"]),
             "rose10_never_fell25_within60d_pct": num(r["surv10"]),
             "rose20_within60d_pct": num(r["reach20"]),
             "median_deepest_dip_pct": num(r["medDip"]), "sample": r["sample"],
             "note": "Pooled across every chart and mix for this asset. Context only: the card is the number for a live setup."}
            for r in rows(d("grades.csv"))
        ] if all_ok else [],   # a held run publishes no figures from its datasets (13 Nov 2026 audit #22)
    }
    # ---- the second-exchange check (11 Nov 2026): lets the health monitor see Kraken
    # being skipped run after run, which on its own never fails anything ----
    cc = {}
    try:
        with open(d("candle_check.json")) as f:
            cc = json.load(f)
    except (OSError, ValueError):
        pass
    feed["candle_check"] = {
        "checked_at": cc.get("checked_at"), "cross_mode": cc.get("cross_mode"),
        "structural_ok": cc.get("structural_ok"),
        "kraken": {a: (v or {}).get("status") for a, v in (cc.get("cross") or {}).items()},
    } if cc else None
    # ---- schema 5: member card figures (extras_live.py) ----
    extras_ok = all_ok and steps.get("extras", "success") == "success" and all(
        os.path.exists(d(f)) for f in ("missstats.csv", "pastpaths.csv", "oddsfade.csv"))
    feed["extras_withheld"] = not extras_ok
    feed["if_it_misses"] = [
        {"label": LABEL, "asset": r["asset"], "grade": r["grade"], "signals": num(r["aplus_signals"]),
         "misses": num(r["misses"]), "up_first": num(r["up_first"]),
         "median_peak_pct": num(r["median_peak_pct"]), "mean_peak_pct": num(r["mean_peak_pct"]),
         "peaked_5_or_more": num(r["peaked_5_or_more"]), "peaked_10_or_more": num(r["peaked_10_or_more"]),
         "median_worst_drop_pct": num(r["median_worst_drop_pct"]), "median_day60_pct": num(r["median_day60_pct"]),
         "miss_rule": "did not rise 10% within 60 days",
         "note": "Signals of this asset and grade that did not rise 10% within 60 days (the card's headline). Show the median peak."}
        for r in rows(d("missstats.csv"))] if extras_ok else []
    fade = rows(d("oddsfade.csv")) if extras_ok else []
    _tf = status.get("Tier fixed on")
    tier_day = f"{int(_tf[8:10])} {datetime.strptime(_tf, '%Y-%m-%d'):%b %Y}" if _tf else "1 January of the current year"
    feed["odds_fade"] = {
        "label": LABEL,
        "posting_bar_pct": num(fade[0]["posting_bar_pct"]) if fade else POSTING_BAR,
        "tier_fixed_on": status.get("Tier fixed on"),   # refresh.py's own anchor, from status.csv
        "sample": f"ETH signals on the chart/tag pairs in the walk-forward tier as fixed on {tier_day}, applied to every signal from 2016 (refresh.py earlydip/holdcheck). In-sample: the tier was chosen on the outcomes of almost all of these signals. Measured on daily candles from the entry close. Each row is grouped by what was known at the day-10 close (the deepest dip in days 1-10, or the day-10 close vs entry) and its +10%/+20% shares count highs AFTER day 10 (days 11 to 60). General explainer only: a card uses its own ladder. Below the posting bar the edge is gone.",
        "edge_measured_on": "rose 10% after day 10 (days 11 to 60)",
        # rose10/20_after_day10_pct name the real window (days 11-60). The *_within60d_pct names are
        # kept, same values, because feed fields are never renamed or removed (FEED_SPEC); don't use them.
        "early_dip": [{"band": r["band"], "past_trades": num(r["n"]),
                       "rose10_after_day10_pct": num(r["reached10_pct"]), "rose20_after_day10_pct": num(r["reached20_pct"]),
                       "rose10_within60d_pct": num(r["reached10_pct"]), "rose20_within60d_pct": num(r["reached20_pct"]),
                       "edge": r["edge"]} for r in fade if r["kind"] == "early_dip"],
        "day10": [{"check": r["band"], "past_trades": num(r["n"]),
                   "rose10_after_day10_pct": num(r["reached10_pct"]), "rose20_after_day10_pct": num(r["reached20_pct"]),
                   "rose10_within60d_pct": num(r["reached10_pct"]), "rose20_within60d_pct": num(r["reached20_pct"]),
                   "edge": r["edge"]} for r in fade if r["kind"] == "day10"],
    }
    paths = rows(d("pastpaths.csv")) if extras_ok else []
    feed["past_paths"] = [
        {"label": LABEL, "asset": asset, "grade": "A+",
         "signals": num(next(r["n"] for r in paths if r["asset"] == asset)),
         "note": "Every past signal of this grade, daily closes, lined up at entry: percent from entry by day.",
         "days": [{"day": num(r["day"]), "q25_pct": num(r["q25_pct"]), "median_pct": num(r["median_pct"]),
                   "q75_pct": num(r["q75_pct"])} for r in paths if r["asset"] == asset]}
        for asset in dict.fromkeys(r["asset"] for r in paths)]

    me = rows(d("missstats_example.csv")) if extras_ok and os.path.exists(d("missstats_example.csv")) else []
    feed["example_if_it_misses"] = {
        "label": LABEL, "asset": "ETH", "grade": "A+", "signals": num(me[0]["aplus_signals"]), "misses": num(me[0]["misses"]),
        "up_first": num(me[0]["up_first"]), "median_peak_pct": num(me[0]["median_peak_pct"]),
        "median_worst_drop_pct": num(me[0]["median_worst_drop_pct"]), "median_day60_pct": num(me[0]["median_day60_pct"]),
        "miss_rule": "did not rise 10% within 60 days",
        "note": "The worked example's misses: only ETH top-grade signals whose 60th day had closed by 2024-09-22."} if me else None

    pe = rows(d("pastpaths_example.csv")) if extras_ok and os.path.exists(d("pastpaths_example.csv")) else []
    feed["example_past_paths"] = {
        "label": LABEL, "asset": "ETH", "grade": "A+", "signals": num(pe[0]["n"]),
        "note": "The worked example's cloud: only ETH top-grade signals whose 60th day had closed by 2024-09-22.",
        "days": [{"day": num(r["day"]), "q25_pct": num(r["q25_pct"]), "median_pct": num(r["median_pct"]),
                  "q75_pct": num(r["q75_pct"])} for r in pe]} if pe else None

    feed = signal_aliases(feed)
    # 13 Nov 2026: the member page uses a feed only if it passes its strict check (the schema inside the page;
    # feedcheck.py reads the same block). Never publish one it would reject: crash, which publishes the
    # withheld feed and turns the run red.
    bad = feedcheck.problems(json.loads(json.dumps(feed)))
    if bad:
        raise RuntimeError("feed fails the strict check: " + "; ".join(bad[:5]))
    # what the alert log must be when the next run starts (check_log). The feed is written first, whole or not
    # at all, then the log; if the run dies in between, the next run rebuilds the log from this feed's alerts.
    final_log = log_bytes(log_rows) if log_dirty else (open(a.alert_log, "rb").read() if os.path.exists(a.alert_log) else None)
    feed["alert_log"] = {"sha256": sha(final_log), "rows": max(0, final_log.count(b"\n") - 1)} if final_log is not None else None
    atomic_write(a.out, (json.dumps(feed, indent=1) + "\n").encode())
    if log_dirty:
        try:
            write_log(a.alert_log, log_rows)
        except OSError as e:
            # the feed is out and its alerts with it; leave it published (no fail-closed overwrite) so the next
            # run can rebuild the log from it (check_log), and turn this run red
            raise SystemExit(f"feed published, but the alert log could not be written ({e}); the next run rebuilds it from the feed")
    print(f"alerts: {len(alerts)} new" + (" (WITHHELD: " + ", ".join(failed_steps or ["stack"]) + " failed)" if not all_ok else "")
          + (" (log SEEDED with what is already live; nothing sent)" if seeded else ""))
    print(f"feed: {len(cards)} cards{' (WITHHELD: checks failed)' if not all_ok else ''}, "
          f"{len(feed['prints'])} prints, {len(feed['open_signals'])} open signals, "
          f"{len(feed['confluence_windows'])} windows -> {a.out}")


def prev_log_record(feed_path):
    try:
        with open(feed_path) as f:
            r = json.load(f).get("alert_log")
        return r if isinstance(r, dict) and r.get("sha256") else None
    except (OSError, ValueError, AttributeError):
        return None


def unlogged_alerts(feed_path, log_path):
    try:
        with open(feed_path) as f:
            prev = json.load(f)
        rec = prev.get("alert_log")
    except (OSError, ValueError, AttributeError):
        return []
    if not (isinstance(rec, dict) and rec.get("sha256")):
        return []
    have = log_state(log_path) if log_path else None
    if have and have["sha256"] == rec["sha256"]:
        return []
    try:
        have_ids = {r.get("alert_id") for r in read_log(log_path)} if have else set()
    except Exception:  # noqa: BLE001 -- a damaged log is the next run's to judge (check_log)
        have_ids = set()
    return [x for x in (prev.get("alert_log_carry") or []) + (prev.get("alerts") or [])
            if isinstance(x, dict) and x.get("alert_id") not in have_ids]


def held_alerts(feed_path, log_path):
    """For the fail-closed feed: the alerts the last feed was carrying, kept for the next clean feed."""
    try:
        with open(feed_path) as f:
            prev = json.load(f)
    except Exception:  # noqa: BLE001
        prev = None
    try:
        rows_ = read_log(log_path) if log_path and os.path.exists(log_path) else []
        if not log_ok(rows_):
            raise ValueError("alert log unreadable")
        rows_ += [{k: x.get(k) for k in ALERT_LOG_FIELDS} for x in unlogged_alerts(feed_path, log_path)]
        return carried_alerts(prev, rows_, now_utc(), keep_all=True)
    except Exception:  # noqa: BLE001 -- the fail-closed feed must always be written
        # the log cannot be read: keep the last feed's own list as it was; the next clean run carries only what
        # the (repaired) log records
        try:
            return [dict({k: x.get(k) for k in ALERT_LOG_FIELDS}, label=LABEL) for x in (prev_carry(prev) or [])]
        except Exception:  # noqa: BLE001
            return []


def fail_closed(out_path, err, log_path=None):
    """Fire drills, 11 Nov 2026: when this script itself crashes (a missing column after an
    upstream step failed, say), the PREVIOUS feed used to stay published, cards and all, as
    if the run were clean. Overwrite it with an empty, withheld feed instead, so every reader
    sees that this run's checks failed. Exit 1 still turns the run red and retries it."""
    now = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
    feed = {"schema_version": SCHEMA_VERSION, "generated_at": now, "posting_bar_pct": POSTING_BAR, "scored_as_of": None, "label": LABEL,
            "checks": {"passed": False, "all_passed": False, "lines": [], "steps": step_outcomes(),
                       "failed_steps": ["feed"]},
            "feed_error": type(err).__name__,
            "cards_withheld": True, "alerts_withheld": True, "extras_withheld": True,
            "alerts": [], "cards": [], "prints": [], "open_signals": [], "confluence_windows": [],
            "grade_odds": [], "if_it_misses": [], "past_paths": [], "candle_check": None, "example_card": None, "example_past_paths": None, "example_if_it_misses": None,
            "odds_fade": {"label": LABEL, "posting_bar_pct": POSTING_BAR, "sample": None, "early_dip": [], "day10": []},
            "market_regime": None, "next_buy_date": None, "trades_a_year": None,
            # a failed run never writes the log, so what the log must be is unchanged: carry the last published
            # feed's record forward (a log damaged before this run must still be caught by the next one)
            "alert_log": prev_log_record(out_path) or (log_state(log_path) if log_path else None),
            # alerts the last published feed sent that the log does not hold yet (it died before writing the log):
            # carried so the next run can still rebuild the log, and never sent again
            "alert_log_carry": unlogged_alerts(out_path, log_path),
            # alerts the last feed was carrying in their delivery window; the next clean feed carries them on
            "alerts_held": held_alerts(out_path, log_path)}
    atomic_write(out_path, (json.dumps(feed, indent=1) + "\n").encode())
    return


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 -- any crash must leave a withheld feed behind
        out = "feed/ctzb_feed.json"
        if "--out" in sys.argv[1:-1]:
            out = sys.argv[sys.argv.index("--out") + 1]
        log = "feed/alert_log.csv"
        if "--alert-log" in sys.argv[1:-1]:
            log = sys.argv[sys.argv.index("--alert-log") + 1]
        fail_closed(out, e, log)
        print(f"FEED BUILD FAILED ({type(e).__name__}: {e}); wrote a withheld feed to {out}", file=sys.stderr)
        sys.exit(1)
