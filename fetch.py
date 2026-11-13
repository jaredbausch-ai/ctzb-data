#!/usr/bin/env python3
"""Pull Coinbase daily candles and rebuild the multi-day bars CTZB runs on.

Coinbase serves only 1D natively. TradingView builds 2D/3D/5D/8D by bucketing
days within each calendar year, restarting the count on 1 January. That rule
was verified against TradingView exports: 100% bar match and 297 of 297
signals identical across ETH 2D, 3D, 5D and 8D.
"""
import csv
import math, datetime as dt, json, os, time, urllib.request

API = "https://api.exchange.coinbase.com/products/{p}/candles"
PRODUCTS = ["ETH-USD", "BTC-USD"]
TIMEFRAMES = [2, 3, 5, 8]          # days; 1D is written as-is
INTRADAY = [4, 12]                 # hours; rebuilt from 1H
START = dt.date(2016, 1, 1)
OUT = os.path.join(os.path.dirname(__file__), "data")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ctzb-pipeline"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def daily(product):
    """Page backwards 300 candles at a time. Returns {date: (o,h,l,c,v)}."""
    bars, end = {}, dt.date.today()
    while end > START:
        start = max(START, end - dt.timedelta(days=299))
        url = f"{API.format(p=product)}?granularity=86400&start={start}&end={end}"
        rows = get(url)
        if not rows:
            break
        for t, lo, hi, op, cl, vol in rows:
            d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
            if d >= START:
                bars[d] = (op, hi, lo, cl, vol)  # note the API order is l,h,o,c
        end = start - dt.timedelta(days=1)
        time.sleep(0.25)                          # stay under the rate limit
    return bars


def hourly(product, since):
    """Page FORWARD from `since` at 1H. Returns {unix_ts: (o,h,l,c,v)}.

    Forward, not backward like daily(), because this is incremental: only the
    first run pages the whole history. Later runs ask for the one bucket that
    was still open plus whatever is new, which is a single request.
    """
    bars, cur = {}, since
    now = dt.datetime.now(dt.timezone.utc)
    while cur < now:
        end = min(now, cur + dt.timedelta(hours=299))
        iso = "%Y-%m-%dT%H:%M:%SZ"      # the canonical form; isoformat()'s
        url = (f"{API.format(p=product)}?granularity=3600"   # +00:00 is riskier
               f"&start={cur.strftime(iso)}&end={end.strftime(iso)}")
        rows = get(url)
        for t, lo, hi, op, cl, _vol in rows or []:
            bars[t] = (op, hi, lo, cl)
        cur = end + dt.timedelta(hours=1)
        time.sleep(0.25)
    return bars


def resample_intraday(bars, hours):
    """Bucket from the UTC epoch: every bucket starts at a multiple of `hours`.

    Verified against TradingView by rebuilding their ETH 12H bars from their
    own 4H export: 821 of 823 identical, the two misses differing only in the
    open by 0.007% where the 4H export had a gap.
    """
    sec = hours * 3600
    groups = {}
    for t in sorted(bars):
        groups.setdefault(t - (t % sec), []).append(t)
    out = {}
    for k in sorted(groups):
        ts = groups[k]
        out[k] = (bars[ts[0]][0], max(bars[x][1] for x in ts),
                  min(bars[x][2] for x in ts), bars[ts[-1]][3],
                  sum(bars[x][4] for x in ts if len(bars[x]) > 4))
    return out


def read_ts(path):
    """Existing bars keyed by unix timestamp, or {} if the file isn't there."""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            out[int(r["time"])] = (float(r["open"]), float(r["high"]),
                                   float(r["low"]), float(r["close"]),
                                   float(r.get("volume") or 0.0))
    return out


def write_ts(path, bars):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        for t in sorted(bars):
            w.writerow([t, *bars[t]])
    last = dt.datetime.fromtimestamp(max(bars), dt.timezone.utc)
    print(f"  {os.path.basename(path):24s} {len(bars):6d} bars  through {last:%Y-%m-%d %H:%M}")


def resample(bars, tf):
    """Bucket days inside each calendar year, restarting on 1 January."""
    groups = {}
    for d in sorted(bars):
        key = (d.year, (d - dt.date(d.year, 1, 1)).days // tf)
        groups.setdefault(key, []).append(d)
    out = {}
    for key in sorted(groups):
        days = groups[key]
        o = bars[days[0]][0]
        h = max(bars[x][1] for x in days)
        l = min(bars[x][2] for x in days)
        c = bars[days[-1]][3]
        v = sum(bars[x][4] for x in days if len(bars[x]) > 4)
        out[days[0]] = (o, h, l, c, v)
    return out


# The exchange's history starts here; a daily file that starts later has lost history (daily() stops paging
# on an empty response, so a hiccup mid-fetch would otherwise pass as a short but "fresh" file).
FIRST_DAY = {"ETH": dt.date(2016, 5, 18), "BTC": dt.date(2016, 1, 1)}
# Days the exchange itself has no candle for. Any other missing day inside a daily file is a fault.
KNOWN_MISSING = {"ETH": {dt.date(2016, 5, 21), dt.date(2016, 5, 22)}, "BTC": set()}


def _row_problems(name, rows, step):
    """Every row of one candle file: a readable time on the bar grid, strictly ascending; open, high, low and
    close finite and above zero, the high and low bracketing the open and close; volume finite and not negative."""
    bad, prev = [], None
    for i, r in enumerate(rows, 2):
        try:
            t = float(r["time"]); o, h, l, c = (float(r[k]) for k in ("open", "high", "low", "close"))
            v = float(r["volume"]) if r.get("volume") not in (None, "") else 0.0
        except (KeyError, TypeError, ValueError):
            return [f"{name}: row {i} has a missing or unreadable cell"]
        if not all(math.isfinite(x) for x in (t, o, h, l, c, v)):
            return [f"{name}: row {i} holds a non-finite number"]
        if min(o, h, l, c) <= 0 or v < 0:
            return [f"{name}: row {i} has a price at or below zero, or a negative volume"]
        if h < max(o, c) or l > min(o, c):
            return [f"{name}: row {i} has a high below, or a low above, its open or close"]
        if step and t % step:
            return [f"{name}: row {i} is not on the {step // 3600}-hour grid"]
        if prev is not None and not t > prev:
            bad.append(f"{name}: row(s) repeated or out of order (first at row {i})"); break
        prev = t
    if not rows:
        bad.append(f"{name} is empty")
    return bad


def history_problems(data_dir, assets=("ETH", "BTC"), today=None):
    """Whole-history checks (13 Nov 2026, audits #20 to #22). Returns a list of problems, empty when whole.
    - Every candle file (1D to 8D, 4H, 12H), every row: see _row_problems (structure, not price levels).
    - Each daily file starts on the exchange's first day and has no missing day after it (bar the two the
      exchange never had); every 2D-8D file is exactly the daily candles bucketed by resample().
    - ETH is ETH and BTC is BTC: on every day both have, ETH's close is between 0.1% and 50% of BTC's (it has
      been 0.8% to 15%). A file of one asset saved under the other's name fails here.
    - The funding series the grade reads (data/derivs/<asset>_funding_daily.csv, column funding_mean): days
      strictly ascending from its first day with none missing, every value a finite number between -1 and 1
      (the series has stayed within -0.5 and 0.3), and the last day no more than 3 days before `today`
      (default: the clock's UTC date). The derivatives fetch runs after the feed, so the series ends a day
      behind the candles in a normal run.
    4H and 12H files can have exchange gaps, so they are checked for structure and grid only."""
    from clock import now_utc
    today = today or now_utc().date()
    bad, closes, intraday = [], {}, {}
    for a in assets:
        for name, step in [(f"{a}_{tf}D", 0) for tf in (1,) + tuple(TIMEFRAMES)] + [(f"{a}_4H", 4 * 3600), (f"{a}_12H", 12 * 3600)]:
            pth = os.path.join(data_dir, name + ".csv")
            if not os.path.exists(pth):
                bad.append(f"{name} is missing"); continue
            with open(pth, newline="") as f:
                frows = list(csv.DictReader(f))
            rp = _row_problems(name, frows, step)
            bad += rp
            if step and len(frows) > 1 and not rp:
                # the right timeframe: nearly every bar follows the last by exactly one step (the exchange has a few
                # gaps; a 12H file saved as 4H has none on the 4-hour step)
                ts = [float(r["time"]) for r in frows]
                on = sum(1 for i in range(1, len(ts)) if ts[i] - ts[i - 1] == step)
                if on < 0.99 * (len(ts) - 1):
                    bad.append(f"{name}: only {on} of {len(ts) - 1} bars are one {step // 3600}-hour step apart: not a {name.split('_')[1]} file")
                intraday[name] = (ts[-1], float(frows[-1]["close"]))
        pf = os.path.join(data_dir, "derivs", f"{a}_funding_daily.csv")
        if os.path.exists(pf):
            with open(pf, newline="") as f:
                fr = list(csv.DictReader(f))
            try:
                days = [dt.date.fromisoformat(r["date"]) for r in fr]
                vals = [float(r["funding_mean"]) for r in fr]
            except (KeyError, TypeError, ValueError):
                bad.append(f"{a}_funding_daily: a row has no readable date or funding_mean"); days = vals = []
            if fr and days:
                if any((days[i] - days[i - 1]).days != 1 for i in range(1, len(days))):
                    bad.append(f"{a}_funding_daily: a day is missing, repeated or out of order")
                if not all(math.isfinite(v) and -1 < v < 1 for v in vals):
                    bad.append(f"{a}_funding_daily: a funding value is not a number between -1 and 1")
                if days[-1] < today - dt.timedelta(days=3):
                    bad.append(f"{a}_funding_daily ends {days[-1]}: more than 3 days before {today}")
            elif not fr:
                bad.append(f"{a}_funding_daily is empty")
        else:
            bad.append(f"{a}_funding_daily is missing")
        p1 = os.path.join(data_dir, f"{a}_1D.csv")
        if not os.path.exists(p1):
            continue
        with open(p1) as f:
            rows = list(csv.DictReader(f))
        try:
            daily = {dt.datetime.fromtimestamp(float(r["time"]), dt.timezone.utc).date():
                     tuple(float(r[k]) for k in ("open", "high", "low", "close")) for r in rows}
        except (KeyError, TypeError, ValueError):
            continue   # already reported above
        if not daily:
            continue
        closes[a] = {d: v[3] for d, v in daily.items()}
        if min(daily) > FIRST_DAY[a]:
            bad.append(f"{a}_1D starts {min(daily)}, expected {FIRST_DAY[a]}: history is missing")
        d, holes = min(daily), []
        while d < max(daily):
            if d not in daily and d not in KNOWN_MISSING[a]:
                holes.append(d)
            d += dt.timedelta(days=1)
        if holes:
            bad.append(f"{a}_1D has {len(holes)} missing day(s) (first {holes[0]})")
        for tf in TIMEFRAMES:
            p = os.path.join(data_dir, f"{a}_{tf}D.csv")
            if not os.path.exists(p):
                continue   # already reported above
            try:
                with open(p) as f:
                    got = {dt.datetime.fromtimestamp(float(r["time"]), dt.timezone.utc).date():
                           tuple(float(r[k]) for k in ("open", "high", "low", "close")) for r in csv.DictReader(f)}
            except (KeyError, TypeError, ValueError):
                continue   # already reported above
            want = {d: v[:4] for d, v in resample({d: v + (0.0,) for d, v in daily.items()}, tf).items()}
            if set(got) != set(want):
                miss = sorted(set(want) - set(got)); extra = sorted(set(got) - set(want))
                bad.append(f"{a}_{tf}D bars differ from the daily candles: {len(miss)} missing"
                           + (f" (first {miss[0]})" if miss else "") + f", {len(extra)} extra")
            else:
                diff = [d for d in want if any(abs(x - y) > 1e-9 for x, y in zip(got[d], want[d]))]
                if diff:
                    bad.append(f"{a}_{tf}D: {len(diff)} bar(s) are not their daily candles bucketed (first {min(diff)})")
    # the 4H and 12H files are the same asset as its daily file: their last close is within 25% of the daily close
    # of the day that bar falls on
    for name, (t, c) in intraday.items():
        a = name.split("_")[0]
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
        if a in closes and d in closes[a] and not 0.75 <= c / closes[a][d] <= 1.25:
            bad.append(f"{name}: its last close is not {a}'s price that day: a file of another asset?")
    if "ETH" in closes and "BTC" in closes:
        odd = [d for d in closes["ETH"] if d in closes["BTC"] and not 0.001 <= closes["ETH"][d] / closes["BTC"][d] <= 0.5]
        if odd:
            bad.append(f"ETH and BTC daily closes are not ETH and BTC on {len(odd)} day(s) (first {min(odd)}): a file of one asset under the other's name?")
    return bad


def write(path, bars):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        for d in sorted(bars):
            ts = int(dt.datetime.combine(d, dt.time(), dt.timezone.utc).timestamp())
            w.writerow([ts, *bars[d]])
    print(f"  {os.path.basename(path):24s} {len(bars):5d} bars  through {max(bars)}")


def today_from_hourly(product, today):
    """Today's (UTC) daily bar built from today's hourly candles: (o, h, l, c, v), or None if there are none.

    12 Nov 2026 audit #17. Every later step treats the last daily bar as today's open bar. In the first minutes
    after 00:00 UTC the daily endpoint may not have opened the new bar yet; until this date the pipeline then ran
    on yesterday's bar as if it were still open. The hourly endpoint has the day's trades as soon as there are
    any, so the bar is built from it. Real candles, replaced by the exchange's own daily bar on the next run.
    """
    iso = "%Y-%m-%dT%H:%M:%SZ"
    start = dt.datetime.combine(today, dt.time(), dt.timezone.utc)
    now = dt.datetime.now(dt.timezone.utc)
    rows = get(f"{API.format(p=product)}?granularity=3600&start={start.strftime(iso)}&end={now.strftime(iso)}") or []
    rows = sorted(r for r in rows if dt.datetime.fromtimestamp(r[0], dt.timezone.utc).date() == today)
    if not rows:
        return None
    return (rows[0][3], max(r[2] for r in rows), min(r[1] for r in rows), rows[-1][4], sum(r[5] for r in rows))  # API order t,l,h,o,c,v


def main():
    for product in PRODUCTS:
        sym = product.split("-")[0]
        print(f"{product}:")
        bars = daily(product)
        if not bars:
            raise SystemExit(f"no candles returned for {product}")
        today = dt.datetime.now(dt.timezone.utc).date()
        if today not in bars:
            tb = today_from_hourly(product, today)
            if tb:
                bars[today] = tb
                print(f"  the daily endpoint has not opened {today} yet: today's bar built from the hourly candles")
        write(os.path.join(OUT, f"{sym}_1D.csv"), bars)
        for tf in TIMEFRAMES:
            write(os.path.join(OUT, f"{sym}_{tf}D.csv"), resample(bars, tf))

        # --- intraday -------------------------------------------------------
        # Resume from the start of the last bucket already stored, so a bucket
        # that was still forming when we last ran is rebuilt rather than frozen
        # half-finished. With nothing stored this backfills from START.
        widest = max(INTRADAY)
        have = read_ts(os.path.join(OUT, f"{sym}_{widest}H.csv"))
        if have:
            since = dt.datetime.fromtimestamp(max(have), dt.timezone.utc)
        else:
            since = dt.datetime.combine(START, dt.time(), dt.timezone.utc)
            print(f"  no {widest}H file yet - backfilling hourly from {START}, "
                  f"this takes a few minutes")
        fresh = hourly(product, since)
        if not fresh:
            print(f"  no new hourly candles for {product}")
            continue
        for hrs in INTRADAY:
            path = os.path.join(OUT, f"{sym}_{hrs}H.csv")
            merged = read_ts(path)
            merged.update(resample_intraday(fresh, hrs))
            write_ts(path, merged)


if __name__ == "__main__":
    main()
