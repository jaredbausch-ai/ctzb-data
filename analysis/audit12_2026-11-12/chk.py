import csv, os, math
OUT = os.path.dirname(os.path.abspath(__file__))
ROWS = []


def norm(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, float):
        if math.isfinite(v) and v == int(v) and abs(v) < 1e15:
            return repr(float(v))
        return repr(v)
    return str(v)


def eq(shown, yours):
    if shown is None and yours is None:
        return True
    if isinstance(shown, (int, float)) and not isinstance(shown, bool) and isinstance(yours, (int, float)) and not isinstance(yours, bool):
        return float(shown) == float(yours)
    if isinstance(shown, str) and isinstance(yours, (int, float)) and not isinstance(yours, bool):
        try:
            return float(shown) == float(yours)
        except ValueError:
            return False
    if shown == '' and yours is None or shown is None and yours == '':
        return True
    return norm(shown) == norm(yours)


def check(state, loc, label, shown, yours, cause='', ok=None):
    if ok is None:
        ok = eq(shown, yours)
    ROWS.append(dict(state=state, location=loc, label=label, shown=norm(shown), yours=norm(yours), ok='yes' if ok else 'NO', cause='' if ok else cause))
    return ok


def save(name='all_checks.csv'):
    with open(os.path.join(OUT, name), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause'])
        w.writeheader(); w.writerows(ROWS)
