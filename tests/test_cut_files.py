"""Family test for damaged input files (13 Nov 2026, audit #26): every candle file and every daily series the
scoring steps read, cut short at every cell boundary and inside every cell of its last line, must fail the
whole-history check (fetch.history_problems), which check_candles and stack_live both run.

Earlier rounds tested single cut points and fixed the files named; audit #26 found a cut just after a row's last
comma still passed on the 2D-8D files. A cut drops the line end, so a file that doesn't end with a whole line
fails. A series or 4H/12H file missing only its whole last row reads as one a row behind, which is not a visible
cut (the daily candle files are caught there too: today's bar is missing). This test covers every cut point of the
family on every file, so a new file or a new reader can't reopen it unnoticed.

    python3 tests/test_cut_files.py     # exit 1 if any cut passes
"""
import os, shutil, sys, tempfile

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, R)
import fetch

FILES = [f"{a}_{tf}.csv" for a in ("ETH", "BTC") for tf in ("1D", "2D", "3D", "5D", "8D", "4H", "12H")] + \
        [f"derivs/{a}_{s}_daily.csv" for a in ("ETH", "BTC") for s in ("funding", "lsratio", "oi")] + \
        ["options/BTC_pcr_daily.csv"]


def cut_points(last):
    """Every position at a cell boundary (just before and just after each comma) and the middle of each cell."""
    pts, start = {0}, 0
    for i, ch in enumerate(last + ","):
        if ch == ",":
            if i > start: pts.add((start + i) // 2)
            pts.update({i, i + 1}); start = i + 1
    return sorted(p for p in pts if p < len(last))


def main():
    T = tempfile.mkdtemp(prefix="cutfiles_")
    try:
        D = f"{T}/data"; shutil.copytree(f"{R}/data", D, ignore=shutil.ignore_patterns("tradingview", "ext", "flows", "onchain"))
        base = fetch.history_problems(D)
        if base:
            print("real data does not pass the whole-history check:", base[:3]); return 1
        tried = failed_to_catch = 0
        for rel in FILES:
            p = f"{D}/{rel}"; orig = open(p).read()
            head, last = orig.rstrip("\n").rsplit("\n", 1)
            for k in cut_points(last):
                if k == 0 and ("/" in rel or rel.endswith(("4H.csv", "12H.csv"))):
                    continue   # a series or 4H/12H file missing its whole last row reads as one a row behind: no cut is visible, and no scoring step needs that row
                open(p, "w").write(head + "\n" + last[:k])   # a cut drops the line end too
                tried += 1
                if not fetch.history_problems(D):
                    failed_to_catch += 1; print(f"  *** PASSED (should fail): {rel} cut at {k} of {len(last)}: {last[:k]!r}")
            open(p, "w").write(orig)
        print(f"{tried - failed_to_catch}/{tried} cut files caught across {len(FILES)} files")
        return 1 if failed_to_catch else 0
    finally:
        shutil.rmtree(T, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
