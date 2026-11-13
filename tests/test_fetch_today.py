"""fetch.today_from_hourly and check_fresh.py (12 Nov 2026 audit #17).

When the daily endpoint has not opened today's bar yet, fetch.py builds it from today's hourly candles; and
check_fresh.py no longer accepts yesterday's bar just after midnight. No network: fetch.get is replaced.

    python3 tests/test_fetch_today.py
"""
import csv, datetime as dt, os, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import fetch  # noqa: E402

ok = n = 0
def check(label, cond, detail=""):
    global ok, n
    n += 1; ok += bool(cond)
    print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f"  -- {detail}" if detail and not cond else ""))

today = dt.datetime.now(dt.timezone.utc).date()
t0 = int(dt.datetime.combine(today, dt.time(), dt.timezone.utc).timestamp())
# API rows are [time, low, high, open, close, volume], newest first; one row from yesterday must be ignored
rows = [[t0 + 7200, 99.0, 104.0, 101.0, 103.5, 5.0], [t0 + 3600, 98.0, 102.0, 100.5, 101.0, 7.0],
        [t0, 99.5, 101.0, 100.0, 100.5, 3.0], [t0 - 3600, 1.0, 999.0, 50.0, 60.0, 9.0]]
fetch.get = lambda url: rows
check("today's bar from hourly candles: open of the first hour, high, low, close of the last, volume summed",
      fetch.today_from_hourly("X-USD", today) == (100.0, 104.0, 98.0, 103.5, 15.0), str(fetch.today_from_hourly("X-USD", today)))
fetch.get = lambda url: [rows[-1]]
check("no hourly candle for today yet: no bar is invented", fetch.today_from_hourly("X-USD", today) is None)

def fresh(last_day):
    d = tempfile.mkdtemp()
    for a in ("ETH", "BTC"):
        with open(os.path.join(d, f"{a}_1D.csv"), "w", newline="") as f:
            csv.writer(f).writerows([["time", "open", "high", "low", "close", "volume"],
                                     [int(dt.datetime.combine(last_day, dt.time(), dt.timezone.utc).timestamp()), 1, 1, 1, 1, 1]])
        with open(os.path.join(d, f"{a}_4H.csv"), "w", newline="") as f:
            csv.writer(f).writerows([["time", "open", "high", "low", "close"], [int(time.time() // 14400 * 14400), 1, 1, 1, 1]])
    return subprocess.run([sys.executable, os.path.join(ROOT, ".github", "scripts", "check_fresh.py"), d], capture_output=True, text=True)

check("check_fresh passes when the last daily bar is today's", fresh(today).returncode == 0)
r = fresh(today - dt.timedelta(days=1))
check("check_fresh fails on yesterday's bar at any time of day (no early allowance)", r.returncode != 0 and "STALE" in r.stdout, r.stdout[:120])
print(f"\n{ok}/{n} passed"); sys.exit(0 if ok == n else 1)
