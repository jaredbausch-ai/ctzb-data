import csv, math

ROWS = []


def norm(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return v
    return v


def same(a, b):
    a, b = norm(a), norm(b)
    if a == '' or b == '':
        return (a == '' or a is None) and (b == '' or b is None)
    try:
        fa, fb = float(a), float(b)
        return fa == fb
    except (TypeError, ValueError):
        return str(a) == str(b)


def add(state, location, label, shown, yours, cause=''):
    ok = same(shown, yours)
    ROWS.append(dict(state=state, location=location, label=label, shown='' if shown is None else shown,
                     yours='' if yours is None else yours, ok='yes' if ok else 'NO', cause='' if ok else cause))
    return ok


def write(path_all, path_dis):
    keys = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
    with open(path_all, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(ROWS)
    with open(path_dis, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows([r for r in ROWS if r['ok'] != 'yes'])
