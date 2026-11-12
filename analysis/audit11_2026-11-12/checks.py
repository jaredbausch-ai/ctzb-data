"""Shared check recorder."""
import csv, json, os

OUT = os.path.dirname(os.path.abspath(__file__))
ROWS = []


def norm(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return str(int(v)) if False else repr(v)
    return str(v)


def eq(shown, yours):
    """Numbers compare by value, everything else as text."""
    if shown in (None, '') and yours in (None, ''):
        return True
    try:
        if isinstance(shown, bool) or isinstance(yours, bool):
            raise ValueError
        return float(shown) == float(yours)
    except (TypeError, ValueError):
        return str(shown) == str(yours)


def chk(state, location, label, shown, yours, cause='', ok=None):
    if ok is None:
        ok = eq(shown, yours)
    ROWS.append(dict(state=state, location=location, label=label, shown=norm(shown), yours=norm(yours),
                     ok='yes' if ok else 'no', cause='' if ok else cause))
    return ok


def dump(name):
    with open(os.path.join(OUT, name), 'w') as f:
        json.dump(ROWS, f)
