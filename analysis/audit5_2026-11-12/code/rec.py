"""Check recorder."""
import csv, os
from fractions import Fraction as Fr

CHECKS = []


def norm(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, Fr):
        return str(float(v))
    return str(v)


def same(a, b):
    if a is None and b is None:
        return True
    if (a is None) != (b is None):
        # '' and None are the same "blank"
        return (a in ('', None)) and (b in ('', None))
    if isinstance(a, bool) or isinstance(b, bool):
        return norm(a) == norm(b)
    try:
        return Fr(str(a)) == Fr(str(b))
    except (ValueError, ZeroDivisionError):
        return str(a).strip() == str(b).strip()


def chk(state, loc, label, shown, yours, cause=''):
    ok = same(shown, yours)
    CHECKS.append(dict(state=state, location=loc, label=label, shown=norm(shown), yours=norm(yours), ok='yes' if ok else 'no',
                       cause='' if ok else cause))
    return ok


def write(out):
    with open(os.path.join(out, 'all_checks.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause'])
        w.writeheader(); w.writerows(CHECKS)
    with open(os.path.join(out, 'disagreements.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause'])
        w.writeheader(); w.writerows([c for c in CHECKS if c['ok'] == 'no'])
