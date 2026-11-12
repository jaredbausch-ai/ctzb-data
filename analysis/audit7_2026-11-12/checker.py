import csv, os

OUT = os.path.dirname(os.path.abspath(__file__))


def norm(v):
    if v is None or v == '': return ''
    if isinstance(v, bool): return 'yes' if v else 'no'
    if isinstance(v, (int, float)):
        f = float(v)
        return repr(int(f)) if f.is_integer() else repr(f)
    s = str(v)
    try:
        f = float(s)
        return repr(int(f)) if f.is_integer() else repr(f)
    except ValueError:
        return s


class Checker:
    def __init__(self):
        self.rows = []

    def add(self, state, location, label, shown, yours, cause='', ok=None):
        if ok is None:
            ok = norm(shown) == norm(yours)
        self.rows.append(dict(state=state, location=location, label=label, shown='' if shown is None else shown,
                              yours='' if yours is None else yours, ok='yes' if ok else 'no', cause='' if ok else cause))
        return ok

    def write(self, path_all, path_bad):
        f = ['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']
        for p, rs in ((path_all, self.rows), (path_bad, [r for r in self.rows if r['ok'] == 'no'])):
            with open(p, 'w', newline='') as fh:
                w = csv.DictWriter(fh, fieldnames=f); w.writeheader(); w.writerows(rs)
