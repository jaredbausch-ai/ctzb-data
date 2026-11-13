import sys, datetime as dt, csv, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a16lib as L
BASE = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad/a16/'
OUT = os.path.dirname(os.path.abspath(__file__))
STATES = {'REPLAY': (BASE + 'replay_0414', dt.datetime(2026, 11, 12, 4, 14, 0, tzinfo=dt.timezone.utc)),
          'CURRENT': (BASE + 'current', None)}


def register(name, root, now):
    STATES[name] = (root, now)


def load_state(name):
    root, now = STATES[name]
    if now is None:
        g = json.load(open(root + '/feed/ctzb_feed.json'))['generated_at']
        now = dt.datetime.fromisoformat(g.replace('Z', '+00:00'))
    return L.State(root, now)


class Checks:
    def __init__(self, state):
        self.state = state; self.rows = []

    def add(self, location, label, shown, mine, ok=None, cause='', tol=None, group=''):
        if ok is None:
            if tol is not None and shown not in (None, '') and mine not in (None, ''):
                try:
                    ok = abs(float(shown) - float(mine)) <= tol
                except (TypeError, ValueError):
                    ok = shown == mine
            else:
                ok = norm(shown) == norm(mine)
        self.rows.append(dict(state=self.state, group=group, location=location, label=label, shown=shown, yours=mine, ok=bool(ok), cause=cause if not ok else ''))
        return bool(ok)

    def bad(self):
        return [r for r in self.rows if not r['ok']]

    def save(self, name):
        with open(os.path.join(OUT, name), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['state', 'group', 'location', 'label', 'shown', 'yours', 'ok', 'cause'])
            w.writeheader(); w.writerows(self.rows)


def norm(v):
    if v is None or v == '':
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return str(v)
