"""Family test for the scoring inputs' whole-file rules (14 Nov 2026, audit #29), on a copy of the committed data:

1. Malformed: a blank line anywhere in any file the history check reads (every candle file, 1D to 8D, 4H and 12H,
   and every daily series) fails. csv.DictReader skips blank lines, so a blank line in the funding series passed.
2. Malformed: no bar missing in a 4H or 12H file. Deleting bars from one asset's file fails (199 recent ETH 4H bars
   passed the 99% timeframe test), at the start, at the end, or to match the other asset's own one-asset gap (fix
   check); the same bar missing from both assets' files at once is an exchange outage and passes; the committed
   data, with the exchange's own gaps, passes.
3. Timing: a daily series row dated after the run's day fails, in the candle check and in the stack step's check.

    python3 tests/test_input_files.py      # exit 1 on failure
"""
import csv, datetime as dt, os, shutil, sys, tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import fetch

SERIES = [f"derivs/{a}_{s}_daily.csv" for a in ("ETH", "BTC") for s in ("funding", "lsratio", "oi")] + ["options/BTC_pcr_daily.csv"]
CANDLES = [f"{a}_{tf}.csv" for a in ("ETH", "BTC") for tf in ("1D", "2D", "3D", "5D", "8D", "4H", "12H")]
results = []


def ok(label, cond, detail=""):
    results.append(bool(cond)); print(f"  {'PASS' if cond else '*** FAIL ***'}  {label}" + (f"  -- {detail}" if detail and not cond else ""))


def main():
    T = tempfile.mkdtemp(prefix="inputfiles_")
    try:
        D = f"{T}/data"; shutil.copytree(f"{R}/data", D, ignore=shutil.ignore_patterns("tradingview", "ext", "flows", "onchain"))
        today = max(dt.date.fromisoformat(list(csv.DictReader(open(f"{D}/{p}")))[-1]["date"]) for p in SERIES)
        base = fetch.history_problems(D, today=today)
        ok("the committed data passes (the exchange's own 4H and 12H gaps included)", not base, str(base[:3]))
        if base: return 1

        def with_text(rel, fn, check):
            p = f"{D}/{rel}"; orig = open(p, newline="").read()
            try:
                open(p, "w", newline="").write(fn(orig)); return check()
            finally:
                open(p, "w", newline="").write(orig)

        # 1. blank lines
        for rel in CANDLES + SERIES:
            def mid(t):
                ls = t.splitlines(keepends=True); k = len(ls) // 2; return "".join(ls[:k] + ["\n"] + ls[k:])
            def end(t): return t + ("\r\n" if t.endswith("\r\n") else "\n")
            def sp(t):
                ls = t.splitlines(keepends=True); return "".join(ls[:-1] + ["  \n"] + ls[-1:])
            got = [bool(with_text(rel, f, lambda: fetch.history_problems(D, today=today))) for f in (mid, end, sp)]
            ok(f"{rel}: a blank line in the middle, at the end or of spaces fails ({sum(got)}/3)", all(got))

        # 2. missing intraday bars
        def drop(rel, keep):
            def f(t):
                ls = t.splitlines(keepends=True); return "".join(l for i, l in enumerate(ls) if keep(i, len(ls)))
            return f
        probs = with_text("ETH_4H.csv", drop("ETH_4H.csv", lambda i, n: not (n - 201 <= i < n - 2)), lambda: fetch.history_problems(D, today=today))
        ok("ETH_4H: 199 recent bars deleted (last bar kept) fails", any("ETH_4H" in x and "gap" in x for x in probs), str(probs[:2]))
        for rel in ("ETH_4H.csv", "BTC_4H.csv", "ETH_12H.csv", "BTC_12H.csv"):
            probs = with_text(rel, drop(rel, lambda i, n: i != n // 2), lambda: fetch.history_problems(D, today=today))
            ok(f"{rel}: one bar deleted in the middle fails", any(rel[:-4] in x and "gap" in x for x in probs), str(probs[:2]))
        # 14 Nov 2026 fix check: bars cut from the start, from the end of one asset's file, or deleted to match the
        # other asset's own one-asset gap
        for rel in ("ETH_4H.csv", "BTC_12H.csv"):
            probs = with_text(rel, drop(rel, lambda i, n: not (1 <= i <= 3)), lambda: fetch.history_problems(D, today=today))
            ok(f"{rel}: its first 3 bars deleted fails", any(rel[:-4] in x and "start" in x for x in probs), str(probs[:2]))
            probs = with_text(rel, drop(rel, lambda i, n: i < n - 1), lambda: fetch.history_problems(D, today=today))
            ok(f"{rel}: its last bar deleted fails", any(rel[:-4] in x and "end" in x for x in probs), str(probs[:2]))
        g0 = 1533859200   # BTC 4H's own gap, 10 Aug 2018: 4 steps to the next bar
        probs = with_text("ETH_4H.csv", lambda t: "".join(l for l in t.splitlines(keepends=True) if not (l[:1].isdigit() and g0 < float(l.split(",", 1)[0]) < g0 + 4 * 14400)),
                          lambda: fetch.history_problems(D, today=today))
        ok("ETH_4H: bars deleted to match BTC 4H's own one-asset gap fails", any("ETH_4H" in x and "gap" in x for x in probs), str(probs[:2]))
        # the same bar gone from both assets' files: an exchange outage
        t0 = list(csv.DictReader(open(f"{D}/ETH_4H.csv")))[-300]["time"]
        def both():
            pe, pb = f"{D}/ETH_4H.csv", f"{D}/BTC_4H.csv"; oe, ob = open(pe, newline="").read(), open(pb, newline="").read()
            try:
                for p, o in ((pe, oe), (pb, ob)):
                    open(p, "w", newline="").write("".join(l for l in o.splitlines(keepends=True) if not l.startswith(t0 + ",")))
                return fetch.history_problems(D, today=today)
            finally:
                open(pe, "w", newline="").write(oe); open(pb, "w", newline="").write(ob)
        probs = both()
        ok("ETH_4H and BTC_4H: the same bar gone from both (an exchange outage) passes", not probs, str(probs[:2]))

        # 3. a series row dated after the run's day
        for rel in SERIES:
            def ahead(t, k):
                ls = t.splitlines(keepends=True); last = ls[-1]; d = dt.date.fromisoformat(last.split(",", 1)[0])
                return t + str(d + dt.timedelta(days=k)) + "," + last.split(",", 1)[1]
            for k in (1, 2):
                end_ = dt.date.fromisoformat(list(csv.DictReader(open(f"{D}/{rel}")))[-1]["date"])
                day = end_ + dt.timedelta(days=k - 1)   # the appended row is one day after the run's day
                for lag in (False, True):
                    probs = with_text(rel, lambda t: ahead(t, k), lambda: fetch.history_problems(D, today=day, lag=lag))
                    ok(f"{rel}: a row dated the day after the run's day fails ({'stack step' if lag else 'candle check'}, {k} day(s) past the series end)",
                       any(rel.split("/")[-1][:-4] in x and "after" in x for x in probs), str(probs[:2]))
        print(f"\n{sum(results)}/{len(results)} passed")
        return 0 if all(results) else 1
    finally:
        shutil.rmtree(T, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
