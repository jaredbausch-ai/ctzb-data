"""Shared check recorder."""
import csv, os
from mine import S
ROWS = []


def rec(state, check, location, label, shown, yours, ok, cause=''):
    ROWS.append(dict(state=state, check=check, location=location, label=label, shown=shown, yours=yours,
                     ok='yes' if ok else 'no', cause='' if ok else cause))
    return ok


def num_eq(shown, mine, nd):
    """shown is a figure rounded to nd places; mine unrounded. ok if shown == mine rounded half away."""
    from mine import rhaz
    if shown is None or shown == '' or mine is None:
        return (shown in (None, '')) and mine is None
    return abs(float(shown) - rhaz(mine, nd)) < 1e-9


def dump(name):
    p = f'{S}/audit3/{name}'
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'check', 'location', 'label', 'shown', 'yours', 'ok', 'cause'])
        w.writeheader(); w.writerows(ROWS)
