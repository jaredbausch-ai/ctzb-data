import csv, json, os
OUT = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/audit8'
CHECKS = []


def norm(v):
    if v is None: return ''
    if isinstance(v, bool): return 'yes' if v else 'no'
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15: return repr(float(v))
        return repr(v)
    return str(v)


def eqv(shown, yours):
    if shown in (None, '') and yours in (None, ''): return True
    try:
        return abs(float(shown) - float(yours)) == 0
    except (TypeError, ValueError):
        return str(shown) == str(yours)


def add(state, loc, label, shown, yours, cause='', ok=None):
    if ok is None: ok = eqv(shown, yours)
    CHECKS.append(dict(state=state, location=loc, label=label, shown=norm(shown) if not isinstance(shown, str) else shown,
                       yours=norm(yours) if not isinstance(yours, str) else yours, ok='yes' if ok else 'no',
                       cause='' if ok else cause))
    return ok


def dump(name):
    with open(os.path.join(OUT, name), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause'])
        w.writeheader(); w.writerows(CHECKS)
