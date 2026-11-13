#!/usr/bin/env python3
"""Pull Coinbase daily candles and rebuild the multi-day bars CTZB runs on.

Coinbase serves only 1D natively. TradingView builds 2D/3D/5D/8D by bucketing
days within each calendar year, restarting the count on 1 January. That rule
was verified against TradingView exports: 100% bar match and 297 of 297
signals identical across ETH 2D, 3D, 5D and 8D.
"""
import csv, datetime as dt, json, os, time, urllib.request

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


def history_problems(data_dir, assets=("ETH", "BTC"), upto=None):
    """Whole-history checks on the candle files (13 Nov 2026 audit #20): each daily file starts on the
    exchange's first day and has no missing day after it (bar the two the exchange never had), every
    2D-8D file is exactly the daily candles bucketed by resample(), and every file's rows run in strictly
    ascending time (no row twice, none out of order). Returns a
    list of problems, empty when the files are whole. `upto` (a date) ignores the first-day rule for replays
    that are cut on purpose; the bucket rule always applies."""
    bad = []
    for a in assets:
        # every candle file, read as the list of rows the engine reads: times strictly ascending, so no row
        # twice and none out of order (13 Nov 2026 audit #21: a duplicated or reversed file passed, because the
        # checks below key rows by date)
        for name in [f"{a}_{tf}D" for tf in (1,) + tuple(TIMEFRAMES)] + [f"{a}_4H", f"{a}_12H"]:
            pth = os.path.join(data_dir, name + ".csv")
            if not os.path.exists(pth):
                continue
            with open(pth) as f:
                try:
                    ts = [float(r["time"]) for r in csv.DictReader(f)]
                except (KeyError, TypeError, ValueError):
                    bad.append(f"{name}: a row has no readable time"); continue
            wrong = [i for i in range(1, len(ts)) if not ts[i] > ts[i - 1]]
            if wrong:
                bad.append(f"{name}: {len(wrong)} row(s) repeated or out of order (first at row {wrong[0] + 1})")
        pf = os.path.join(data_dir, "derivs", f"{a}_funding_daily.csv")   # the funding series the grade reads
        if os.path.exists(pf):
            with open(pf) as f:
                days = [r[0] for r in list(csv.reader(f))[1:] if r]
            if any(not days[i] > days[i - 1] for i in range(1, len(days))):
                bad.append(f"{a}_funding_daily: a day is repeated or out of order")
        p1 = os.path.join(data_dir, f"{a}_1D.csv")
        with open(p1) as f:
            rows = list(csv.DictReader(f))
        daily = {dt.datetime.fromtimestamp(float(r["time"]), dt.timezone.utc).date():
                 tuple(float(r[k]) for k in ("open", "high", "low", "close")) for r in rows}
        if not daily:
            bad.append(f"{a}_1D is empty"); continue
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
                bad.append(f"{a}_{tf}D is missing"); continue
            with open(p) as f:
                got = {dt.datetime.fromtimestamp(float(r["time"]), dt.timezone.utc).date():
                       tuple(float(r[k]) for k in ("open", "high", "low", "close")) for r in csv.DictReader(f)}
            want = {d: v[:4] for d, v in resample({d: v + (0.0,) for d, v in daily.items()}, tf).items()}
            if set(got) != set(want):
                miss = sorted(set(want) - set(got)); extra = sorted(set(got) - set(want))
                bad.append(f"{a}_{tf}D bars differ from the daily candles: {len(miss)} missing"
                           + (f" (first {miss[0]})" if miss else "") + f", {len(extra)} extra")
            else:
                diff = [d for d in want if any(abs(x - y) > 1e-9 for x, y in zip(got[d], want[d]))]
                if diff:
                    bad.append(f"{a}_{tf}D: {len(diff)} bar(s) are not their daily candles bucketed (first {min(diff)})")
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
