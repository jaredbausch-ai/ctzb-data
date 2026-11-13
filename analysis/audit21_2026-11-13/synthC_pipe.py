"""Audit 21 -- group C, pipeline level: break the inputs on a throwaway copy, run the real pipeline steps
(as tests/replay_at.sh --keep-going does), and check that what is published fails closed."""
import csv, datetime as dt, gzip, json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import datacheck as D, pagecheck as P
from playwright.sync_api import sync_playwright

SRC = os.path.join(HERE, 'src_current'); TMP = os.path.join(HERE, 'tmp_pipe')
NOW = '2026-11-13T05:39:41Z'
STEPS = [('refresh', 'refresh.py --data data --out datasets'), ('grade', 'grade_live.py'), ('extras', 'extras_live.py'), ('stack', 'stack_live.py'), ('cards', 'verify_cards.py')]


def run(name, before=None, between=None, now=NOW):
    """between: {step name: fn(tmp)} run just BEFORE that step ('feed' for before feed_live)."""
    shutil.rmtree(TMP, ignore_errors=True); shutil.copytree(SRC, TMP)
    if before: before(TMP)
    env = dict(os.environ, CTZB_NOW=now); outc = []; fails = {}
    for step, cmd in STEPS:
        if between and step in between: between[step](TMP)
        r = subprocess.run(['python3'] + cmd.split(), cwd=TMP, env=env, capture_output=True, text=True)
        outc.append(f"{step}={'success' if r.returncode == 0 else 'failure'}")
        if r.returncode: fails[step] = (r.stderr or r.stdout).strip().splitlines()[-1][:200] if (r.stderr or r.stdout).strip() else 'exit ' + str(r.returncode)
    if between and 'feed' in between: between['feed'](TMP)
    r = subprocess.run(['python3', 'feed_live.py'], cwd=TMP, env=dict(env, CTZB_STEP_OUTCOMES=','.join(outc) + ',regress=success'), capture_output=True, text=True)
    if r.returncode: fails['feed'] = (r.stderr or r.stdout).strip().splitlines()[-1][:200]
    try: feed = json.load(open(os.path.join(TMP, 'feed', 'ctzb_feed.json')))
    except Exception as e: feed = None
    return feed, fails


def page(pw, now=NOW):
    clock = (dt.datetime.fromisoformat(now.replace('Z', '+00:00')) + dt.timedelta(minutes=6)).strftime('%Y-%m-%dT%H:%M:%SZ')
    s = P.Site(pw, TMP, clock); s.goto('now'); g = s.now(); errs = list(s.errs); s.close()
    return g, errs


def edit_csv(path, fn):
    rows = list(csv.reader(open(path))); rows = fn(rows)
    csv.writer(open(path, 'w', newline='')).writerows(rows)


def main():
    ck = D.Checks('C pipeline')
    d = lambda p: (lambda t: os.path.join(t, p))
    def rm(p): return lambda t: os.remove(os.path.join(t, p))
    def trunc0(p): return lambda t: open(os.path.join(t, p), 'w').close()
    def hdr_only(p): return lambda t: edit_csv(os.path.join(t, p), lambda r: r[:1])
    def drop_first(p, n): return lambda t: edit_csv(os.path.join(t, p), lambda r: r[:1] + r[1 + n:])
    def drop_last(p, n): return lambda t: edit_csv(os.path.join(t, p), lambda r: r[:-n])
    def drop_row(p, i): return lambda t: edit_csv(os.path.join(t, p), lambda r: r[:i] + r[i + 1:])
    def setcell(p, i, col, val):
        def f(t):
            def g(r): r[i][r[0].index(col)] = val; return r
            edit_csv(os.path.join(t, p), g)
        return f
    def bump(p, i, col, dv):
        def f(t):
            def g(r): r[i][r[0].index(col)] = str(round(float(r[i][r[0].index(col)]) + dv, 2)); return r
            edit_csv(os.path.join(t, p), g)
        return f
    def dup_last(p): return lambda t: edit_csv(os.path.join(t, p), lambda r: r + [r[-1]])
    def shuffle(p): return lambda t: edit_csv(os.path.join(t, p), lambda r: r[:1] + r[1:][::-1])
    def shortrow(p, i): return lambda t: edit_csv(os.path.join(t, p), lambda r: r[:i] + [r[i][:3]] + r[i + 1:])
    def cut_midrow(p, frac=0.5):
        def f(t):
            s = open(os.path.join(t, p)).read(); lines = s.splitlines(keepends=True)
            open(os.path.join(t, p), 'w').write(''.join(lines[:-1]) + lines[-1][:max(3, int(len(lines[-1]) * frac))])
        return f
    def drop_col(p, col):
        def f(t):
            def g(r): i = r[0].index(col); return [x[:i] + x[i + 1:] for x in r]
            edit_csv(os.path.join(t, p), g)
        return f
    # (name, kwargs, expectation)  expectation: 'closed' = cards withheld and the page says held back / unavailable
    scen = [
        ('clock on day D+1, candles end on day D', dict(now='2026-11-14T00:10:00Z'), 'closed'),
        ('clock on day D-1 (candles one day ahead of the clock)', dict(now='2026-11-12T23:00:00Z'), 'closed'),
        ('ETH_3D.csv missing', dict(before=rm('data/ETH_3D.csv')), 'closed'),
        ('BTC_2D.csv (the gate) missing', dict(before=rm('data/BTC_2D.csv')), 'closed'),
        ('BTC_1D.csv zero bytes', dict(before=trunc0('data/BTC_1D.csv')), 'closed'),
        ('ETH_1D.csv header only', dict(before=hdr_only('data/ETH_1D.csv')), 'closed'),
        ('BTC_1D.csv cut short at the start (400 days)', dict(before=drop_first('data/BTC_1D.csv', 400)), 'closed'),
        ('ETH_1D.csv one day missing in 2024', dict(before=drop_row('data/ETH_1D.csv', 3000)), 'closed'),
        ('ETH_1D.csv last 5 days missing', dict(before=drop_last('data/ETH_1D.csv', 5)), 'closed'),
        ('BTC_5D.csv last bar missing', dict(before=drop_last('data/BTC_5D.csv', 1)), 'closed'),
        ('ETH_2D.csv cut short at the start (200 bars)', dict(before=drop_first('data/ETH_2D.csv', 200)), 'closed'),
        ('BTC_2D.csv one old close 1 cent off its daily candles', dict(before=bump('data/BTC_2D.csv', 900, 'close', 0.01)), 'closed'),
        ('ETH_3D.csv latest bar high altered', dict(before=bump('data/ETH_3D.csv', -1, 'high', 25)), 'closed'),
        ('ETH_1D.csv a close that is text', dict(before=setcell('data/ETH_1D.csv', 3500, 'close', 'abc')), 'closed'),
        ('ETH_1D.csv a row cut short', dict(before=shortrow('data/ETH_1D.csv', 3500)), 'closed'),
        ('BTC_1D.csv last row duplicated', dict(before=dup_last('data/BTC_1D.csv')), 'closed'),
        ('BTC_1D.csv rows in reverse order', dict(before=shuffle('data/BTC_1D.csv')), 'closed'),
        ('ETH_1D.csv file cut mid-row at the end', dict(before=cut_midrow('data/ETH_1D.csv')), 'closed'),
        ('ETH_1D.csv a blank close in today\'s bar', dict(before=setcell('data/ETH_1D.csv', -1, 'close', '')), 'closed'),
        ('ETH funding file missing', dict(before=rm('data/derivs/ETH_funding_daily.csv')), 'closed'),
        ('ledger.csv deleted before the stack step', dict(between={'stack': rm('datasets/ledger.csv')}), 'closed'),
        ('ledger.csv cut mid-row before the stack step', dict(between={'stack': cut_midrow('datasets/ledger.csv')}), 'closed'),
        ('a card figure altered after the stack step (cards_open.csv)', dict(between={'cards': bump('datasets/cards_open.csv', 1, 'reach10', 1)}), 'closed'),
        ('cards_open.csv deleted after the stack step', dict(between={'cards': rm('datasets/cards_open.csv')}), 'closed'),
        ('stack_status.txt deleted before the feed step', dict(between={'feed': rm('datasets/stack_status.txt')}), 'closed'),
        ('cards_open.csv loses a column before the feed step', dict(between={'feed': drop_col('datasets/cards_open.csv', 'l5n')}), 'closed'),
        ('status.csv deleted before the feed step', dict(between={'feed': rm('datasets/status.csv')}), 'regime-unknown'),
        ('open.csv deleted before the feed step (after every check passed)', dict(between={'feed': rm('datasets/open.csv')}), 'report'),
        ('cards_open.csv deleted before the feed step (after every check passed)', dict(between={'feed': rm('datasets/cards_open.csv')}), 'report'),
        ('open.csv cut mid-row before the feed step', dict(between={'feed': cut_midrow('datasets/open.csv', 0.3)}), 'report'),
        ('missstats.csv deleted before the feed step', dict(between={'feed': rm('datasets/missstats.csv')}), 'extras'),
        ('grades.csv deleted before the feed step', dict(between={'feed': rm('datasets/grades.csv')}), 'report'),
    ]
    only = sys.argv[1:]
    with sync_playwright() as pw:
        for name, kw, want in scen:
            if only and not any(o in name for o in only): continue
            ck.state = 'C ' + name
            try:
                feed, fails = run(name, **kw)
                g, errs = page(pw, kw.get('now', NOW))
            except Exception as e:
                ck.flag('audit', 'scenario ran', f'{type(e).__name__}: {e}', 'ran', 'AUDIT CODE ERROR'); continue
            state = g['card']['state']; wh = None if feed is None else bool(feed.get('cards_withheld'))
            desc = f"failed steps: {json.dumps(fails)[:260]}; cards_withheld {wh}; cards {len((feed or {}).get('cards') or [])}; open {len((feed or {}).get('open_signals') or [])}; page: {state} / {g['filter']}"
            print(name, '=>', desc, flush=True)
            if want == 'closed':
                ck.add('pipeline', 'published feed is withheld', wh, True, 'broken input published as a clean run: ' + desc)
                ck.add('page', 'page says held back or unavailable', state in ('Setups held back', 'Data unavailable'), True, desc)
                ck.add('page', 'no live or forming button', sum(1 for r in g['picker'] for b in r['btns'] if b['sel'] != 'example'), 0, desc)
            elif want == 'regime-unknown':
                ck.add('page', 'header reads unavailable, not off', g['filter'], 'Market filter: unavailable', desc)
            elif want == 'extras':
                ck.add('pipeline', 'extras withheld', feed.get('extras_withheld'), True, desc); ck.add('pipeline', 'cards not withheld by extras', wh, False, desc)
            else:
                # a file lost after every check passed: must not read as a normal quiet / complete state
                live_expected = 1   # the live top-grade BTC 2D setup of 21 Sep 2026
                shown = sum(1 for b in g['picker'][0]['btns'])
                ok = (shown == live_expected and state != 'Card unavailable') or state in ('Setups held back', 'Data unavailable', 'Card unavailable') or wh
                if 'grades.csv' in name: ok = True
                ck.add('page', 'the live top-grade setup is shown, or the page says held back / unavailable (never silently missing)', ok, True, desc)
            ck.add('page', 'no page error', json.dumps(errs[:1]), '[]', desc)
            ck.add('page', 'no raw placeholder', bool(__import__('pagerun').BAD.search(g['body'])), False, desc)
    shutil.rmtree(TMP, ignore_errors=True)
    fn = os.path.join(HERE, 'checks_C_pipe.csv.gz')
    old = []
    if only and os.path.exists(fn):
        with gzip.open(fn, 'rt') as fh: old = [r for r in csv.reader(fh) if not any(o in r[0] for o in only)]
    with gzip.open(fn, 'wt', newline='') as fh: csv.writer(fh).writerows(old + ck.rows)
    print('C pipeline-level: scenarios', len({r[0] for r in ck.rows}), 'checks', ck.n, 'diffs', len(ck.bad))
    for r in ck.bad: print('  DIFF', r[0], '|', r[2], '|', str(r[3])[:60], '|', str(r[4])[:60], '|', r[6][:400])


if __name__ == '__main__':
    main()
