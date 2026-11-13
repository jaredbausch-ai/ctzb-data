"""Group C: made-up prices against the candle sanity check (.github/scripts/check_candles.py), run offline with the
second exchange replaced by the untouched closes. Multi-day files are rebuilt from the altered daily file."""
import csv, datetime as dt, gzip, importlib.util, io, os, shutil, sys, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import datacheck as D
SRC = os.path.join(HERE, 'src_current'); T = os.path.join(HERE, 'tmp_cc')
TODAY = dt.date(2026, 11, 13)

def setup():
    shutil.rmtree(T, ignore_errors=True); os.makedirs(os.path.join(T, '.github', 'scripts')); os.makedirs(os.path.join(T, 'datasets'))
    shutil.copytree(os.path.join(SRC, 'data'), os.path.join(T, 'data'), ignore=shutil.ignore_patterns('derivs', 'ext', 'flows', 'onchain', 'options', 'tradingview'))
    shutil.copy(os.path.join(SRC, 'fetch.py'), T); shutil.copy(os.path.join(SRC, '.github', 'scripts', 'check_candles.py'), os.path.join(T, '.github', 'scripts'))

def daily(a):
    rows = list(csv.DictReader(open(os.path.join(T, 'data', f'{a}_1D.csv'))))
    return rows

def write_daily(a, rows, rebuild=True):
    p = os.path.join(T, 'data', f'{a}_1D.csv')
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    if rebuild:
        sys.path.insert(0, T); import fetch
        dd = {dt.datetime.fromtimestamp(float(r['time']), dt.timezone.utc).date(): tuple(float(r[k]) for k in ('open', 'high', 'low', 'close', 'volume')) for r in rows}
        for tf in (2, 3, 5, 8):
            pt = os.path.join(T, 'data', f'{a}_{tf}D.csv'); t0 = float(next(csv.DictReader(open(pt)))['time'])
            d0 = dt.datetime.fromtimestamp(t0, dt.timezone.utc).date()
            fetch.write(pt, {d: v for d, v in fetch.resample(dd, tf).items() if d >= d0})

def run_check():
    spec = importlib.util.spec_from_file_location('cc', os.path.join(T, '.github', 'scripts', 'check_candles.py')); cc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cc)
    def fake(asset):
        return {dt.datetime.fromtimestamp(float(r['time']), dt.timezone.utc).date(): float(r['close']) for r in csv.DictReader(open(os.path.join(SRC, 'data', f'{asset}_1D.csv')))
                if dt.datetime.fromtimestamp(float(r['time']), dt.timezone.utc).date() < TODAY}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cc.main([os.path.join(T, 'data'), '--out', os.path.join(T, 'datasets', 'candle_check.json'), '--cross', 'enforce', '--max-close-gap', '0.5'], kraken=fake, today=TODAY)
    return rc, buf.getvalue().strip().splitlines()[-1][:220]

def main():
    ck = D.Checks('C candle check')
    def case(name, fn, want_fail, rebuild=True, claim=True):
        setup(); rows = daily('ETH'); fn(rows); write_daily('ETH', rows, rebuild)
        rc, msg = run_check(); ck.state = 'C candle check: ' + name
        print(name, '=> exit', rc, '|', msg)
        if claim: ck.add('pipeline', 'candle check ' + ('fails the run' if want_fail else 'passes'), rc != 0, want_fail, msg)
        return rc, msg
    def close_pct(i, pct):
        def f(rows):
            c = round(float(rows[i]['close']) * (1 + pct / 100), 2); rows[i]['close'] = str(c)
            rows[i]['high'] = str(max(float(rows[i]['high']), c)); rows[i]['low'] = str(min(float(rows[i]['low']), c))
            if i + 1 < len(rows): pass
        return f
    def setv(i, k, v): return lambda rows: rows[i].__setitem__(k, str(v))
    def mulv(i, k, m): return lambda rows: rows[i].__setitem__(k, str(round(float(rows[i][k]) * m, 2)))
    case('untouched files', lambda rows: None, False)
    case("yesterday's close made up (+1%)", close_pct(-2, 1.0), True)
    case('a close 20 days ago made up (+0.6%)', close_pct(-21, 0.6), True)
    case("yesterday's low is zero", setv(-2, 'low', 0), True)
    case("yesterday's high below its close", mulv(-2, 'high', 0.9), True)
    obs = []
    obs.append(('a close 45 days ago made up (+5%), inside every live signal\'s 60 days but outside the 30-day window',) + case('a close 45 days ago made up (+5%)', close_pct(-46, 5.0), True, claim=False))
    obs.append(("yesterday's high made up (+20%, close untouched)",) + case("yesterday's high made up (+20%)", mulv(-2, 'high', 1.2), True, claim=False))
    obs.append(("today's open bar price made up (+10%)",) + case("today's price made up (+10%)", close_pct(-1, 10.0), True, claim=False))
    for name, rc, msg in obs:
        ck.state = 'C candle check: ' + name
        ck.rows.append([ck.state, 'pipeline', 'observation only (outside what the check claims): made-up price passes', 'passes' if rc == 0 else 'fails', 'n/a', 'ok', ''])
    with gzip.open(os.path.join(HERE, 'checks_C_cc.csv.gz'), 'wt', newline='') as fh: csv.writer(fh).writerows(ck.rows)
    print('checks', ck.n, 'diffs', len(ck.bad)); shutil.rmtree(T, ignore_errors=True)

if __name__ == '__main__':
    main()
