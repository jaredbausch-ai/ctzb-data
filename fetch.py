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


if __name__ == "__main__":
    main()
