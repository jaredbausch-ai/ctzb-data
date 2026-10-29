#!/usr/bin/env python3
"""Fetch Binance ETHUSDT spot and USDT-perp hourly closes, write the daily perp-vs-spot
gap (basis) for analysis/basistest.py (29 Oct 2026).

Why: TradingView cannot read the 12-exchange funding the ETH grade uses, but it can
read BINANCE:ETHUSDT.P and BINANCE:ETHUSDT. Funding is set from that gap, so the test
asks whether a basis-built FUND/FCOOL agrees with the real ones.

Source: data.binance.vision, Binance's public bulk archive (no key). Monthly zips for
finished months, daily zips for the current month. Runs in GitHub Actions
(.github/workflows/basis.yml); the container cannot reach Binance.

Writes data/ext/ETH_basis_daily.csv:
  date, basis_mean (mean of the 24 hourly (perp/spot - 1) on that UTC day, in %),
  basis_close (at the day's last hourly close, in %), hours
"""
import csv, io, os, sys, zipfile, datetime as dt, urllib.request, time

BASE = 'https://data.binance.vision/data'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'ext', 'ETH_basis_daily.csv')
START = dt.date(2019, 12, 1)


def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ctzb-pipeline'}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 ** i)
        except Exception:
            time.sleep(2 ** i)
    return None


def closes(market):
    """{hour_open_ms: close} for 'spot' or 'futures/um'"""
    out = {}; today = dt.date.today()
    m = START
    while m < today.replace(day=1):
        url = f'{BASE}/{market}/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-{m:%Y-%m}.zip'
        b = get(url)
        if b: out.update(parse(b))
        else: print('missing', url, file=sys.stderr)
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    d = today.replace(day=1)
    while d < today:
        b = get(f'{BASE}/{market}/daily/klines/ETHUSDT/1h/ETHUSDT-1h-{d:%Y-%m-%d}.zip')
        if b: out.update(parse(b))
        d += dt.timedelta(days=1)
    return out


def parse(b):
    z = zipfile.ZipFile(io.BytesIO(b)); out = {}
    for name in z.namelist():
        for row in csv.reader(io.TextIOWrapper(z.open(name))):
            if not row or not row[0].isdigit(): continue
            t = int(row[0])
            if t > 10 ** 14: t //= 1000          # 2025+ spot files are in microseconds
            out[t] = float(row[4])
    return out


def main():
    sp = closes('spot'); fu = closes('futures/um')
    print(f'spot hours {len(sp)}, perp hours {len(fu)}')
    day = {}
    for t in sorted(set(sp) & set(fu)):
        d = dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc).date()
        day.setdefault(d, []).append((t, 100 * (fu[t] / sp[t] - 1)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', newline='') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['date', 'basis_mean', 'basis_close', 'hours'])
        for d in sorted(day):
            v = day[d]
            w.writerow([d, round(sum(x for _, x in v) / len(v), 5), round(max(v)[1], 5), len(v)])
    print(f'wrote {OUT}: {len(day)} days, {min(day)} to {max(day)}')


if __name__ == '__main__':
    main()
