"""The pipeline's idea of "now" (12 Nov 2026).

Real time, unless CTZB_NOW is set (ISO 8601, e.g. 2026-11-12T04:14:00Z). Tests and audits set
it to replay a past pipeline run exactly on the data committed by that run. Nothing in the
live workflow sets it.
"""
import datetime as dt
import os


def now_utc():
    v = os.environ.get("CTZB_NOW")
    if v:
        return dt.datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc)
