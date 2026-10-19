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
    """Page backwards 300 candles at a time. Returns {date: (o,h,l,c)}."""
    bars, end = {}, dt.date.today()
    while end > START:
        start = max(START, end - dt.timedelta(days=299))
        url = f"{API.format(p=product)}?granularity=86400&start={start}&end={end}"
        rows = get(url)
        if not rows:
            break
        for t, lo, hi, op, cl, _vol in rows:
            d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
            if d >= START:
                bars[d] = (op, hi, lo, cl)       # note the API order is l,h,o,c
        end = start - dt.timedelta(days=1)
        time.sleep(0.25)                          # stay under the rate limit
    return bars


def hourly(product, since):
    """Page FORWARD from `since` at 1H. Returns {unix_ts: (o,h,l,c)}.

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
                  min(bars[x][2] for x in ts), bars[ts[-1]][3])
    return out


def read_ts(path):
    """Existing bars keyed by unix timestamp, or {} if the file isn't there."""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            out[int(r["time"])] = (float(r["open"]), float(r["high"]),
                                   float(r["low"]), float(r["close"]))
    return out


def write_ts(path, bars):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["time", "open", "high", "low", "close"])
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
        out[days[0]] = (o, h, l, c)
    return out


def write(path, bars):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close"])
        for d in sorted(bars):
            ts = int(dt.datetime.combine(d, dt.time(), dt.timezone.utc).timestamp())
            w.writerow([ts, *bars[d]])
    print(f"  {os.path.basename(path):24s} {len(bars):5d} bars  through {max(bars)}")


def main():
    for product in PRODUCTS:
        sym = product.split("-")[0]
        print(f"{product}:")
        bars = daily(product)
        if not bars:
            raise SystemExit(f"no candles returned for {product}")
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
