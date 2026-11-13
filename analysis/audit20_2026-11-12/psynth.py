"""Audit #20 group C -- pipeline-level broken states: tamper with a copy, run the real steps, see what is published."""
import json, csv, os, re, sys, shutil, subprocess, datetime as dt, gzip, glob
from playwright.sync_api import sync_playwright
import apage as P
from apage import norm
from adata import Checks

HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.join(HERE, 'base'); WORK = os.path.join(HERE, 'c')
STEPS = [('refresh', 'refresh.py --data data --out datasets'), ('grade', 'grade_live.py'), ('extras', 'extras_live.py'), ('stack', 'stack_live.py'), ('cards', 'verify_cards.py')]
C = Checks('synthetic-pipeline')


def sh(cmd, cwd=None, env=None):
    e = dict(os.environ); e.update(env or {})
    return subprocess.run(cmd, shell=True, cwd=cwd, env=e, capture_output=True, text=True)


def replay(date, name, clock, keep=True):
    d = os.path.join(WORK, name); shutil.rmtree(d, ignore_errors=True)
    r = sh(f'bash {BASE}/tests/replay_at.sh {date} {d} {clock} {"--keep-going" if keep else ""}')
    return d, (r.stdout + r.stderr)[-400:]


def pipeline(d, clock, between=None, only=None):
    """Run the scoring steps like tests/replay_at.sh --keep-going. `between`: {step name: function(dir)} run AFTER that step."""
    out = []
    for name, s in STEPS:
        if only is None or name in only:
            r = sh(f'python3 {s}', cwd=d, env={'CTZB_NOW': clock}); out.append(f"{name}={'success' if r.returncode == 0 else 'failure'}")
        if between and name in between: between[name](d)
    r = sh('python3 feed_live.py', cwd=d, env={'CTZB_NOW': clock, 'CTZB_STEP_OUTCOMES': ','.join(out) + ',regress=success'})
    return ','.join(out), r.returncode


def look(pw, d, name, expect):
    """expect: 'held' | 'failclosed' | 'published' | 'extras'"""
    C.state = 'C:pipeline ' + name
    fp = os.path.join(d, 'feed/ctzb_feed.json')
    try: f = json.load(open(fp))
    except Exception as e: f = None
    if f is None:
        C.add('feed', 'feed file readable', 'no', 'yes', 'no feed written'); return None
    st = open(os.path.join(d, 'datasets/stack_status.txt')).read().strip() if os.path.exists(os.path.join(d, 'datasets/stack_status.txt')) else ''
    info = dict(withheld=f.get('cards_withheld'), cards=len(f.get('cards') or []), open=len(f.get('open_signals') or []), failed=(f.get('checks') or {}).get('failed_steps'), err=f.get('feed_error'), extras=f.get('extras_withheld'), stack=st[:140])
    if expect in ('held', 'failclosed'):
        C.add('feed', 'cards withheld', f.get('cards_withheld'), True, 'not failed closed'); C.add('feed', 'no cards, no open signals', [info['cards'], info['open']], [0, 0], 'cards published from a broken run')
        C.add('feed', 'alerts withheld and empty', [f.get('alerts_withheld'), len(f.get('alerts') or [])], [True, 0], 'alerts published from a broken run')
        if expect == 'failclosed': C.add('feed', 'fail-closed marker', bool(f.get('feed_error')) and f.get('market_regime') in (None, ''), True, 'not a fail-closed feed')
    s = P.Site(d, pw=pw, clock=dt.datetime.fromisoformat(f['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)).open()
    n = s.now(); s.tab('chart'); ct = s.pg.inner_text('#view-chart'); s.tab('record'); rt = s.pg.inner_text('#view-record'); errs = list(s.errors); s.close()
    info['page_state'] = norm(n['card']['state']); info['filter'] = norm(n['filter'])
    if expect in ('held', 'failclosed'):
        C.add('page', 'card state', norm(n['card']['state']), 'Setups held back', 'page does not say held back')
        C.add('page', 'no setup figure on the Now card', bool(re.search(r'\d+%', (n['card']['big'] or '') + ' '.join(n['card']['emptySmalls']))), False, 'figure shown from a broken run')
        C.add('page', 'footer says checks failed', 'checks FAILED, cards held back' in norm(n['foot']), True, 'footer')
        if expect == 'failclosed': C.add('page', 'filter pill', norm(n['filter']), 'Market filter: unavailable', 'fail-closed filter')
    C.add('page', 'javascript errors', len(errs), 0, 'page error ' + '; '.join(errs)[:120])
    C.add('page', 'no raw placeholder', bool(re.search(r"\$\{|undefined|NaN|null%|n/a%|\[object", n['body'] + ct + rt)), False, 'placeholder')
    return info


def edit_csv(path, fn):
    rows = list(csv.reader(open(path))); fn(rows); csv.writer(open(path, 'w', newline='')).writerows(rows)


def main():
    os.makedirs(WORK, exist_ok=True); res = {}
    with sync_playwright() as pw:
        # --- the pipeline's envelope: the last daily candle must be today's
        for name, date, clock in (('clock D+1 00:05, candles end D', '2026-11-11', '2026-11-12T00:05:00Z'), ('clock D+2, candles end D', '2026-11-10', '2026-11-12T12:00:00Z'),
                                  ('clock D-1, candles end D (bar from the future)', '2026-11-12', '2026-11-11T12:00:00Z'), ('clock D+1 00:05, candles end D (2024, top grade forming)', '2024-11-06', '2024-11-07T00:05:00Z'),
                                  ('clock D+30, candles end D', '2025-06-01', '2025-07-01T04:14:00Z')):
            d, log = replay(date, 'x', clock); res[name] = look(pw, d, name, 'held')
            if res[name]: C.add('feed', "stack status names the missing bar", "today's bar is missing" in res[name]['stack'], True, 'fail-closed reason')
        # --- a healthy copy to tamper with (12 Nov 2026 data, 4 forming setups, a live top-grade BTC 2D)
        ok_clock = '2025-03-15T04:14:00Z'
        good, log = replay('2025-03-15', 'good', ok_clock, keep=False)
        def fresh():
            d = os.path.join(WORK, 'x'); shutil.rmtree(d, ignore_errors=True); shutil.copytree(good, d, symlinks=True); return d
        def rm(rel): return lambda d: os.remove(os.path.join(d, rel))
        def write(rel, text): return lambda d: open(os.path.join(d, rel), 'w').write(text)
        def keep_rows(rel, sl): return lambda d: (lambda L: open(os.path.join(d, rel), 'w').write('\n'.join(L[:1] + L[1:][sl]) + '\n'))(open(os.path.join(d, rel)).read().splitlines())
        def append(rel, text): return lambda d: open(os.path.join(d, rel), 'a').write(text)
        def lastbar(rel, **kw):
            def f(d):
                def g(rows):
                    h = rows[0]
                    for k, v in kw.items(): rows[-1][h.index(k)] = str(v(float(rows[-1][h.index(k)])) if callable(v) else v)
                edit_csv(os.path.join(d, rel), g)
            return f
        pre = [  # (name, tamper before the pipeline, expectation)
            ('ETH_1D.csv missing', rm('data/ETH_1D.csv'), 'held'), ('BTC_1D.csv missing', rm('data/BTC_1D.csv'), 'held'), ('BTC_2D.csv missing (the gate)', rm('data/BTC_2D.csv'), 'held'),
            ('ETH_5D.csv missing', rm('data/ETH_5D.csv'), 'held'), ('BTC_8D.csv missing', rm('data/BTC_8D.csv'), 'held'),
            ('ETH_3D.csv header only', keep_rows('data/ETH_3D.csv', slice(0, 0)), 'held'), ('ETH_1D.csv empty file', write('data/ETH_1D.csv', ''), 'held'),
            ('BTC_1D.csv cut to its last 40 bars', keep_rows('data/BTC_1D.csv', slice(-40, None)), 'held'), ('ETH_2D.csv cut to its first half', keep_rows('data/ETH_2D.csv', slice(0, 900)), 'held'),
            ('ETH_1D.csv last two bars missing (stale)', keep_rows('data/ETH_1D.csv', slice(0, -2)), 'held'), ('BTC_1D.csv last bar missing (stale)', keep_rows('data/BTC_1D.csv', slice(0, -1)), 'held'),
            ('ETH_1D.csv garbage row appended', append('data/ETH_1D.csv', 'abc,def,ghi\n'), 'held'), ('BTC_3D.csv text in a price', lastbar('data/BTC_3D.csv', close='n/a'), 'held'),
            ('ETH_1D.csv one mid day deleted (2025-02-10)', lambda d: edit_csv(os.path.join(d, 'data/ETH_1D.csv'), lambda rows: rows.remove(next(r for r in rows[1:] if r[0] == '1739145600'))), 'any'),
            ('funding file missing', rm('data/derivs/ETH_funding_daily.csv'), 'held'),
            ('made-up price: ETH today close x0.5 (1D only)', lastbar('data/ETH_1D.csv', close=lambda v: round(v * 0.5, 2), low=lambda v: round(v * 0.45, 2)), 'any'),
            ('made-up flash print: ETH today low 0.01', lastbar('data/ETH_1D.csv', low=0.01), 'any'),
            ('made-up negative price: BTC today close -5', lastbar('data/BTC_1D.csv', close=-5), 'any'),
            ('made-up zero price: BTC 2D last close 0', lastbar('data/BTC_2D.csv', close=0), 'any'),
        ]
        for name, tamper, exp in pre:
            d = fresh()
            try: tamper(d)
            except Exception as e: C.state = 'C:pipeline ' + name; C.add('setup', 'tamper applied', str(e)[:80], 'ok', 'harness'); continue
            oc, rc = pipeline(d, ok_clock); info = look(pw, d, name, exp if exp != 'any' else 'none')
            if info: info['steps'] = oc; info['feed_rc'] = rc
            res[name] = info
            if exp == 'any' and info and not info['withheld']:
                # the run published: audit what it published with my own code on the same (tampered) candles
                r = sh(f'python3 {HERE}/run_state.py {d} {ok_clock} cp_{re.sub("[^a-z0-9]+", "_", name.lower())[:40]} --out {HERE}/synthetic', cwd=HERE, env={'SHOW': '6'})
                info['audit'] = (r.stdout + r.stderr)[-900:]
        # --- tamper between steps (hand-edited outputs)
        def ed(rel, fn): return lambda d: edit_csv(os.path.join(d, rel), fn)
        def setcol(col, val, row=1):
            def f(rows): rows[row][rows[0].index(col)] = str(val)
            return f
        mid = [
            ('cards.csv hand-edited (reach10 +1) before the card check', {'stack': ed('datasets/cards.csv', lambda rows: setcol('reach10', int(rows[1][rows[0].index('reach10')]) + 1)(rows))}, 'held'),
            ('cards_open.csv hand-edited (ladder share) before the card check', {'stack': ed('datasets/cards_open.csv', setcol('l5ok', 99))}, 'held'),
            ('cards_example.csv hand-edited (median) before the card check', {'stack': ed('datasets/cards_example.csv', setcol('bestMove', 99.9))}, 'held'),
            ('cards_open.csv one live card deleted before the card check', {'stack': ed('datasets/cards_open.csv', lambda rows: rows.pop(1))}, 'held'),
            ('cards.csv n hand-edited before the card check', {'stack': ed('datasets/cards.csv', setcol('n', 999))}, 'held'),
            ('cards.csv exact median hand-edited by 0.00001 before the card check', {'stack': ed('datasets/cards.csv', lambda rows: setcol('maxDip60Exact', round(float(rows[1][rows[0].index('maxDip60Exact')]) + 0.00001, 6))(rows))}, 'held'),
            ('ledger.csv figure hand-edited after grading (a top-grade best move)', {'grade': ed('datasets/ledger.csv', lambda rows: setcol('bestMove', 1.0, next(i for i, r in enumerate(rows) if r[6] == 'A+'))(rows))}, 'any'),
            ('stack_status.txt carries a FAILED line', {'cards': append('datasets/stack_status.txt', '2025-03-15 04:14 UTC FAILED made-up failure\n')}, 'held'),
            ('missstats.csv deleted after the extras step', {'cards': rm('datasets/missstats.csv')}, 'extras'),
            ('prints.csv loses a column (feed_live crashes)', {'cards': ed('datasets/prints.csv', lambda rows: [r.pop(1) for r in rows])}, 'failclosed'),
            ('status.csv deleted (feed_live reads nothing)', {'cards': rm('datasets/status.csv')}, 'any'),
            ('grades.csv emptied', {'cards': write('datasets/grades.csv', '')}, 'any'),
            ('open.csv emptied to its header', {'cards': keep_rows('datasets/open.csv', slice(0, 0))}, 'any'),
        ]
        for name, between, exp in mid:
            d = fresh()
            try: oc, rc = pipeline(d, ok_clock, between=between)
            except Exception as e: C.state = 'C:pipeline ' + name; C.add('setup', 'tamper applied', repr(e)[:80], 'ok', 'harness'); continue
            info = look(pw, d, name, exp if exp in ('held', 'failclosed') else 'none')
            if info: info['steps'] = oc; info['feed_rc'] = rc
            res[name] = info
            if exp == 'extras' and info:
                C.add('feed', 'extras withheld, cards still published', [info['extras'], info['withheld']], [True, False], 'extras gating')
        # a step outcome reported as failure though it ran (the workflow's own gate)
        for stp in ('refresh', 'grade', 'stack', 'cards', 'regress'):
            d = fresh(); r = sh('python3 feed_live.py', cwd=d, env={'CTZB_NOW': ok_clock, 'CTZB_STEP_OUTCOMES': ','.join(f"{s}={'failure' if s == stp else 'success'}" for s in ('refresh', 'grade', 'extras', 'stack', 'cards', 'regress'))})
            res[f'step {stp} reported failed'] = look(pw, d, f'step {stp} reported failed', 'held')
        d = fresh(); r = sh('python3 feed_live.py', cwd=d, env={'CTZB_NOW': ok_clock, 'CTZB_STEP_OUTCOMES': 'refresh=success,grade=success,extras=failure,stack=success,cards=success,regress=success'})
        info = look(pw, d, 'step extras reported failed', 'none'); res['step extras reported failed'] = info
        if info: C.add('feed', 'extras withheld, cards still published', [info['extras'], info['withheld']], [True, False], 'extras gating')
    shutil.rmtree(os.path.join(WORK, 'x'), ignore_errors=True)
    json.dump(res, open(os.path.join(HERE, 'synthetic', 'pipeline_states.json'), 'w'), indent=1)
    bad = C.bad()
    print('pipeline synthetic states:', len(res), 'comparisons', C.n(), 'disagreements', len(bad))
    for r in bad: print('  ', r)
    for k, v in res.items(): print(' *', k, '->', {kk: vv for kk, vv in (v or {}).items() if kk not in ('audit',)}, '\n      AUDIT:', (v or {}).get('audit', '')[:700].replace('\n', ' | ') if (v or {}).get('audit') else '')
    with gzip.open(os.path.join(HERE, 'synthetic', 'checks_synthetic_pipeline.csv.gz'), 'wt', newline='') as f: csv.writer(f).writerows(C.rows)


if __name__ == '__main__':
    main()
