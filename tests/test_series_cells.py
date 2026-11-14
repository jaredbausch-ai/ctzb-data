"""Family test for the daily series the scoring steps read (13 Nov 2026, audit #27): funding, long/short ratio, open
interest (per asset) and BTC put/call.

1. Every column, any row: a cell holding text, inf or nan fails the whole-history check (fetch.history_problems).
   Audit #27 found funding_oi_weighted, the column the scorer reads first, unchecked: inf, nan, 1e300 or 3.0 in it
   were scored and changed a card.
2. Every column the scorer reads: an out-of-range number fails.
3. Each series ending further behind today than its normal lag fails; at its normal lag it passes (a series 3 days
   behind changed the ETH 1D card).

    python3 tests/test_series_cells.py      # exit 1 on failure
"""
import csv, datetime as dt, os, shutil, sys, tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import fetch

SERIES = [f"derivs/{a}_{s}_daily.csv" for a in ("ETH", "BTC") for s in ("funding", "lsratio", "oi")] + ["options/BTC_pcr_daily.csv"]
READ = {"funding": [("funding_oi_weighted", "3.0"), ("funding_oi_weighted", "-1.5"), ("funding_mean", "3.0")],
        "lsratio": [("ls_ratio_mean", "25")], "oi": [("oi_usd_total", "-5")], "pcr": [("pcr_amt", "-1")]}
results = []


def ok(label, cond):
    results.append(bool(cond)); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}")


def main():
    T = tempfile.mkdtemp(prefix="seriescells_")
    try:
        D = f"{T}/data"; shutil.copytree(f"{R}/data", D, ignore=shutil.ignore_patterns("tradingview", "ext", "flows", "onchain"))
        last = max(dt.date.fromisoformat(list(csv.DictReader(open(f"{D}/{p}")))[-1]["date"]) for p in SERIES if "derivs" in p)
        today = last   # the data's own day: the derivatives end today in the committed data
        if fetch.history_problems(D, today=today):
            print("real data does not pass:", fetch.history_problems(D, today=today)[:3]); return 1
        for rel in SERIES:
            p = f"{D}/{rel}"; orig = open(p).read()
            rows = list(csv.DictReader(open(p))); cols = list(rows[0])
            def write(rs):
                with open(p, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n"); w.writeheader(); w.writerows(rs)
            # 1. every column, the last row and a row in the middle
            caught = tried = 0
            for c in cols[1:]:
                for i in (len(rows) - 1, len(rows) // 2):
                    for bad in ("abc", "inf", "nan"):
                        rs = [dict(r) for r in rows]; rs[i][c] = bad; write(rs); tried += 1
                        caught += bool(fetch.history_problems(D, today=today))
            ok(f"{rel}: text, inf or nan in any of {len(cols) - 1} columns fails ({caught}/{tried})", caught == tried)
            # 2. read columns out of range
            kind = rel.split("_")[-2] if "derivs" in rel else "pcr"
            for c, v in READ[kind]:
                rs = [dict(r) for r in rows]; rs[-1][c] = v; write(rs)
                ok(f"{rel}: {c} = {v} fails", fetch.history_problems(D, today=today))
            # 3. lag: normal passes, one more day fails
            lag = fetch.MAX_LAG_DAYS[kind]
            end = dt.date.fromisoformat(rows[-1]["date"])
            open(p, "w").write(orig)
            stem = rel.split("/")[-1].split(".")[0]
            probs = fetch.history_problems(D, today=end + dt.timedelta(days=lag), lag=True)
            ok(f"{rel}: ending {lag} day(s) behind passes the stack step's check", not any(stem in x and "day(s) before" in x for x in probs))
            probs = fetch.history_problems(D, today=end + dt.timedelta(days=lag + 1), lag=True)
            ok(f"{rel}: ending {lag + 1} day(s) behind fails the stack step's check", any(stem in x and "day(s) before" in x for x in probs))
            ok(f"{rel}: ... but not the candle check, which runs before the fetch that catches it up",
               not any(stem in x and "day(s) before" in x for x in fetch.history_problems(D, today=end + dt.timedelta(days=lag + 5))))
            if kind == "pcr":   # lag is measured on the read column: blank put/call days at the end count as behind
                rs = [dict(r) for r in rows]
                for r in rs[-3:]: r["pcr_amt"] = ""
                write(rs)
                ok(f"{rel}: its last 3 pcr_amt cells blank fails the stack step's check", any(stem in x and "day(s) before" in x for x in fetch.history_problems(D, today=end, lag=True)))
            open(p, "w").write(orig)
        print(f"\n{sum(results)}/{len(results)} passed")
        return 0 if all(results) else 1
    finally:
        shutil.rmtree(T, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
