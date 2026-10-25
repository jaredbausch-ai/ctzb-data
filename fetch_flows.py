"""Pull the Coinbase Premium: US spot bid against offshore, daily, for BTC and ETH.

Runs in the GitHub Action after fetch.py. Needs NO API key -- both endpoints are
public. The container cannot reach either (the agent proxy returns 403), which
is why this lives in the Action like the rest of the pipeline.

WHAT THIS MEASURES, stated plainly because it is easy to oversell. The Coinbase
Premium is the gap between Coinbase's USD price and Binance's USDT price for the
same asset at the same UTC daily close. Coinbase is where US institutions, funds
and the spot ETF authorised participants transact; Binance is offshore retail and
market makers. A persistent positive premium means US buyers are lifting offers
harder than offshore ones. It is the standard free proxy for US institutional
accumulation and it is what CryptoQuant sells under that name.

It is NOT a whale wallet measure. It cannot see individual holders, exchange
netflow, or on-chain cohort supply -- those need a paid API (Glassnode,
CryptoQuant, Nansen). What it has going for it is that it is a FLOW measure
rather than another transform of the same closes, which per CONTEXT.md is the
test that has separated the two filters that worked from the ninety-odd that did
not.

KNOWN CAVEAT: the premium includes any USDT depeg, since it compares a USD price
to a USDT price. During a depeg the premium moves for reasons that have nothing
to do with US buying. The industry-standard index has the same flaw.

Writes, under data/flows/:
  {SYM}_binance_daily.csv    date, close        (Binance spot, USDT pair)
  {SYM}_premium_daily.csv    date, cb_close, bn_close, premium_pct
  fetch_log.txt              so failures are visible in the repo

Incremental: refetches from 5 days before the newest stored date; first run
backfills from 2017-08-17, when Binance's BTCUSDT pair opens.
"""
import csv, datetime as dt, json, os, sys, time, urllib.request, urllib.error

BINANCE = 'https://api.binance.com/api/v3/klines'
OUT = 'data/flows'
START = dt.date(2017, 8, 17)
PAIRS = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT'}
LOG = []


def log(m):
    print(m); LOG.append(f'{dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M:%S} {m}')


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'ctzb-pipeline'})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get('Retry-After', 30))
                log(f'  429, sleeping {wait}s'); time.sleep(wait); continue
            log(f'  HTTP {e.code} on {url[:90]}')
            if i == tries - 1: return None
        except Exception as e:
            log(f'  {type(e).__name__} on {url[:90]}')
            if i == tries - 1: return None
        time.sleep(2 ** i)
    return None


def binance_daily(pair, since):
    """Daily closes from `since`, paging 1000 bars at a time."""
    out = {}
    cur = dt.datetime.combine(since, dt.time(), dt.UTC)
    end = dt.datetime.now(dt.UTC)
    while cur < end:
        ms = int(cur.timestamp() * 1000)
        rows = get(f'{BINANCE}?symbol={pair}&interval=1d&startTime={ms}&limit=1000')
        if not rows:
            break
        for r in rows:
            d = dt.datetime.fromtimestamp(r[0] / 1000, dt.UTC).date()
            out[d] = float(r[4])
        last = dt.datetime.fromtimestamp(rows[-1][0] / 1000, dt.UTC)
        if len(rows) < 1000:
            break
        cur = last + dt.timedelta(days=1)
        time.sleep(0.4)
    return out


def read_two(path, key, val):
    out = {}
    if not os.path.exists(path): return out
    with open(path) as f:
        for r in csv.DictReader(f):
            if r.get(val) not in ('', None):
                out[dt.date.fromisoformat(r[key])] = float(r[val])
    return out


def coinbase_daily(sym):
    """Closes from the candle file fetch.py already wrote."""
    out = {}
    p = f'data/{sym}_1D.csv'
    if not os.path.exists(p):
        log(f'  {p} missing -- run fetch.py first'); return out
    with open(p) as f:
        for r in csv.DictReader(f):
            d = dt.datetime.fromtimestamp(int(r['time']), dt.UTC).date()
            out[d] = float(r['close'])
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for sym, pair in PAIRS.items():
        bpath = f'{OUT}/{sym}_binance_daily.csv'
        have = read_two(bpath, 'date', 'close')
        since = max(have) - dt.timedelta(days=5) if have else START
        log(f'{sym}: fetching {pair} from {since}')
        fresh = binance_daily(pair, since)
        if not fresh and not have:
            log(f'  no Binance data for {pair}; skipping'); continue
        have.update(fresh)
        with open(bpath, 'w', newline='') as f:
            w = csv.writer(f); w.writerow(['date', 'close'])
            for d in sorted(have): w.writerow([d.isoformat(), f'{have[d]:.8f}'])
        cb = coinbase_daily(sym)
        both = sorted(set(cb) & set(have))
        with open(f'{OUT}/{sym}_premium_daily.csv', 'w', newline='') as f:
            w = csv.writer(f); w.writerow(['date', 'cb_close', 'bn_close', 'premium_pct'])
            for d in both:
                if have[d] <= 0: continue
                w.writerow([d.isoformat(), f'{cb[d]:.2f}', f'{have[d]:.2f}',
                            f'{(cb[d] / have[d] - 1) * 100:.4f}'])
        log(f'  {len(have)} Binance days, {len(both)} overlapping with Coinbase, '
            f'{min(both) if both else "-"} -> {max(both) if both else "-"}')
    with open(f'{OUT}/fetch_log.txt', 'w') as f:
        f.write('\n'.join(LOG) + '\n')


if __name__ == '__main__':
    main()
