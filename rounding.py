"""One rounding rule for every figure a member sees (12 Nov 2026, independent audit).

Round half AWAY from zero, once, on the unrounded value: 62.5 -> 63, 22.5 -> 23, -2.5 -> -3.
Python's built-in round() rounds half to EVEN (62.5 -> 62), which the audit flagged as a
disagreement with what a reader expects. The page's JavaScript toFixed() also rounds half away
from zero, so the feed and the page now agree.

Modules that print figures import it as `round`, so every existing call keeps its shape:
    from rounding import rnd as round
round(x) returns an int, round(x, n) a float, exactly like the built-in.
It rounds the float's EXACT binary value, as JavaScript's toFixed() does, so the feed and the
page round any number the same way (2.675 is stored as 2.67499999... and rounds to 2.67).
"""
from decimal import Decimal, ROUND_HALF_UP
import builtins

_builtin_round = builtins.round


def rnd(x, nd=None):
    if x is None:
        raise TypeError("rnd() of None")
    if isinstance(x, int) and not isinstance(x, bool) and (nd is None or nd >= 0):
        return x if nd is None else x
    q = Decimal(1) if not nd else Decimal(1).scaleb(-nd)
    d = Decimal(float(x)).quantize(q, rounding=ROUND_HALF_UP)   # exact binary value, half away from zero
    return int(d) if nd is None else float(d)
