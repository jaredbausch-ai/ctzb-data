"""Fail the candle run if the fetched candles are not current (4 Nov 2026).

fetch.py can "succeed" with data that stopped advancing (an exchange serving a stale
page, a silent empty response). A stale fetch must count as a failure, so it is
retried, never committed as if it were fresh.

  - data/{ETH,BTC}_1D.csv: the last bar must be today's (UTC) forming daily bar
  - data/{ETH,BTC}_4H.csv: the last bar must be the current 4-hour bar or the one before
    it (the exchange can take a few minutes to open the new bar)
"""
import csv, os, sys, time, datetime as dt

D = sys.argv[1] if len(sys.argv) > 1 else "data"
now = time.time()
today = dt.datetime.now(dt.timezone.utc).date()
b4 = int(now // 14400 * 14400)
bad = []
for a in ("ETH", "BTC"):
    def last(name):
        with open(os.path.join(D, name)) as f:
            rows = list(csv.reader(f))
        return int(float(rows[-1][0]))
    d1 = dt.datetime.fromtimestamp(last(f"{a}_1D.csv"), dt.timezone.utc).date()
    if d1 != today:
        bad.append(f"{a}_1D last bar {d1}, expected {today}")
    h4 = last(f"{a}_4H.csv")
    if h4 < b4 - 14400:
        bad.append(f"{a}_4H last bar {dt.datetime.fromtimestamp(h4, dt.timezone.utc):%Y-%m-%d %H:%M} UTC, "
                   f"expected {dt.datetime.fromtimestamp(b4, dt.timezone.utc):%H:%M} UTC")
if bad:
    print("STALE CANDLES: " + "; ".join(bad))
    sys.exit(1)
print(f"candles current: 1D bars dated {today}, 4H bars through the current window")
