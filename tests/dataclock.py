"""Test helper: pin the clock (CTZB_NOW) to the repo data's own day, so tests that run pipeline steps on the
repo's data give the same result whatever the wall clock says.

Before 13 Nov 2026 these tests used the real clock, so they failed in any window where the wall clock had moved
past the data (after midnight UTC before the next pipeline run, or more than 2 hours after the run that sealed the
datasets). A run at 04:14 UTC on the day of the last daily candle is a normal pipeline run for that data.

    import dataclock; dataclock.pin()      # sets os.environ['CTZB_NOW'] unless it is already set
"""
import csv, datetime as dt, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_now(root=ROOT):
    with open(os.path.join(root, "data", "ETH_1D.csv")) as f:
        last = float(list(csv.DictReader(f))[-1]["time"])
    day = dt.datetime.fromtimestamp(last, dt.timezone.utc).date()
    return f"{day.isoformat()}T04:14:00Z"


def pin(root=ROOT):
    os.environ.setdefault("CTZB_NOW", data_now(root))
    return os.environ["CTZB_NOW"]
