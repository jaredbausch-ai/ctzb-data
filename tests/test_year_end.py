"""Year-end replays (12 Nov 2026 audit #15). 2D+ bars restart on 1 January, so a year's last bar can be
short. A low forming across a year-end must show the confirmation date the signal really gets (the ledger's
entry date), and keep the same signal id when it confirms.

    python3 tests/test_year_end.py
"""
import csv, json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# (replay date, chart, the confirmation date the low must show = the signal's entry date in today's ledger)
# The 2023 low went on to confirm, so its date must also be the ledger's entry date; the 2024 one did not confirm
# (no such ledger row), so only the bar arithmetic is checked: 5D bars of 2025 open 1, 6, 11 Jan.
CASES = [("2023-12-31", "ETH 2D", "2023-12-31", True), ("2024-12-31", "BTC 5D", "2025-01-10", False)]

def main():
    tmp = tempfile.mkdtemp(prefix="yearend_"); ok = 0; n = 0
    led = {(r["chart"], r["entry"]) for r in csv.DictReader(open(os.path.join(ROOT, "datasets", "ledger.csv")))}
    try:
        for date, chart, want, in_ledger in CASES:
            d = os.path.join(tmp, date)
            r = subprocess.run(["bash", os.path.join(ROOT, "tests", "replay_at.sh"), date, d], capture_output=True, text=True, timeout=1200)
            if r.returncode:
                n += 1; print(f"  *** FAIL ***  replay {date}: {r.stdout.strip()[-200:]}"); continue
            prints = [p for p in csv.DictReader(open(os.path.join(d, "datasets", "prints.csv"))) if p["state"] == "forming"]
            feed = json.load(open(os.path.join(d, "feed", "ctzb_feed.json")))
            # every forming low's confirmation date is a real bar close: on or before 31 Dec, or after it by whole bars
            p = next((x for x in prints if x["chart"] == chart), None)
            for name, cond, detail in [
                (f"{date}: {chart} is forming", p is not None, ""),
                (f"{date}: {chart} shows confirms {want}", bool(p) and p["confirms"] == want, p["confirms"] if p else ""),
                (f"{date}: that date is the signal's entry date in the ledger", (not in_ledger) or (chart, want) in led, ""),
                (f"{date}: any card for it carries the same date and id",
                 all(c["confirms_on"] == want and c["signal_id"].endswith(want) for c in feed["cards"] if c["chart"] == chart), ""),
            ]:
                n += 1; ok += bool(cond)
                print(f"  {'PASS' if cond else '*** FAIL ***'}  {name}" + (f"  -- {detail}" if detail and not cond else ""))
        print(f"\n{ok}/{n} passed"); sys.exit(0 if ok == n else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
