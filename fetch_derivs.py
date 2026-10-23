"""Pull BTC and ETH perpetual-futures positioning data from Coinalyze.

Runs in the GitHub Action after fetch.py. Needs the repository secret
COINALYZE_API_KEY (Settings -> Secrets and variables -> Actions); the key is
read from the environment and sent as the `api_key` header, never written to
disk or logs. Without the secret the script prints a note and exits cleanly,
so the candle pipeline is unaffected.

API (https://api.coinalyze.net/v1/doc/): 40 calls per minute per key, each
symbol in a request counts as one call, max 20 symbols per request; daily
history is kept indefinitely; 429 responses carry Retry-After.

Writes, under data/derivs/:
  markets.json                         the perpetual markets used, from /future-markets
  {SYM}_oi_daily.csv                   date, total open interest in USD (close), count of
                                       markets reporting, then one column per market
  {SYM}_funding_daily.csv              date, open-interest-weighted mean funding (close),
                                       simple mean, count, then one column per market
  {SYM}_lsratio_daily.csv              date, mean long/short ratio, count, per market
                                       (only markets that publish it)
Funding is stored exactly as Coinalyze returns it (per funding interval).

Incremental: each run refetches from 7 days before the newest stored date;
the first run backfills from 2019-01-01.
"""
import csv, datetime as dt, json, os, sys, time, urllib.request, urllib.error, urllib.parse

BASE = 'https://api.coinalyze.net/v1'
OUT = 'data/derivs'
START = dt.date(2019, 1, 1)
ASSETS = ('BTC', 'ETH')
QUOTES = ('USD', 'USDT', 'USDC')
EXCHANGE_NAMES = ('binance', 'bybit', 'okx', 'deribit', 'bitmex', 'coinbase', 'bitfinex', 'kraken')
PAUSE = 1.6          # seconds per symbol-call, stays under 40/min

KEY = os.environ.get('COINALYZE_API_KEY', '').strip()
LOG = []          # written to data/derivs/fetch_log.txt so failures are visible in the repo


def log(msg):
    print(msg); LOG.append(f'{dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} {msg}')


def call(path, params=None, cost=1):
    url = f'{BASE}{path}' + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'api_key': KEY, 'User-Agent': 'ctzb-pipeline'})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
            time.sleep(PAUSE * cost)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get('Retry-After', '30')) + 1
                print(f'  rate limited, waiting {wait}s'); time.sleep(wait); continue
            if e.code in (401, 403):
                log(f'Coinalyze refused the key (HTTP {e.code}). Check the COINALYZE_API_KEY secret.')
                flush(); sys.exit(1)
            if 400 <= e.code < 500:
                body = e.read().decode('utf-8', 'replace')[:300]
                log(f'HTTP {e.code} on {path} {dict((k, v) for k, v in (params or {}).items())}: {body}')
                return None
            if attempt == 5:
                log(f'HTTP {e.code} on {path}, giving up'); return None
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == 5:
                log(f'{type(e).__name__} on {path}: {e}'); return None
            time.sleep(2 ** attempt)


def flush():
    os.makedirs(OUT, exist_ok=True)
    with open(f'{OUT}/fetch_log.txt', 'w') as f:
        f.write('\n'.join(LOG[-300:]) + '\n')


def ts(d):
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())


def read_existing(path):
    if not os.path.exists(path):
        return {}, []
    with open(path) as f:
        rd = csv.reader(f); hdr = next(rd)
        return {r[0]: r for r in rd}, hdr


def history(path, symbols, start, extra=None):
    """{symbol: {date: point}} for one history endpoint, chunked by 20 symbols and by year."""
    out = {s: {} for s in symbols}
    today = dt.datetime.now(dt.timezone.utc).date()
    for i in range(0, len(symbols), 20):
        chunk = symbols[i:i + 20]
        a = start
        while a <= today:
            b = min(dt.date(a.year, 12, 31), today)
            now = int(time.time())
            params = dict(symbols=','.join(chunk), interval='daily', **{'from': ts(a), 'to': min(ts(b) + 86399, now)})
            if extra:
                params.update(extra)
            res = call(path, params, cost=len(chunk))
            if res is not None and not isinstance(res, list):
                log(f'unexpected reply on {path}: {str(res)[:300]}'); res = None
            if res is None and len(chunk) > 1:          # one bad symbol can sink a chunk: retry singly
                res = []
                for sym in chunk:
                    r1 = call(path, dict(params, symbols=sym), cost=1)
                    if isinstance(r1, list):
                        res.extend(r1)
                    elif r1 is not None:
                        log(f'unexpected reply on {path} {sym}: {str(r1)[:300]}')
            for row in res or []:
                for p in row.get('history', []):
                    d = dt.datetime.fromtimestamp(p['t'], dt.timezone.utc).date().isoformat()
                    out.setdefault(row['symbol'], {})[d] = p
            a = b + dt.timedelta(days=1)
    return out


def write(path, cols, rows):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows:
            w.writerow(r)


def main():
    if not KEY:
        print('COINALYZE_API_KEY not set; skipping derivatives fetch.')
        return
    os.makedirs(OUT, exist_ok=True)
    ex = call('/exchanges'); markets = call('/future-markets')
    if not ex or not markets:
        log('could not read /exchanges or /future-markets'); flush(); sys.exit(1)
    exch = {e['code']: e['name'] for e in ex}
    use = [m for m in markets if m.get('is_perpetual') and m.get('base_asset') in ASSETS
           and m.get('quote_asset') in QUOTES
           and any(n in exch.get(m['symbol'].rsplit('.', 1)[-1], '').lower() for n in EXCHANGE_NAMES)]
    with open(f'{OUT}/markets.json', 'w') as f:
        json.dump([dict(m, exchange_name=exch.get(m['symbol'].rsplit('.', 1)[-1])) for m in use], f, indent=1)
    log(f'{len(use)} perpetual markets selected')
    for asset in ASSETS:
        syms = sorted(m['symbol'] for m in use if m['base_asset'] == asset)
        if not syms:
            continue
        files = {k: f'{OUT}/{asset}_{k}_daily.csv' for k in ('oi', 'funding', 'lsratio')}
        ls_syms = sorted(m['symbol'] for m in use if m['base_asset'] == asset and m.get('has_long_short_ratio_data'))
        cols = {'oi': ['date', 'oi_usd_total', 'n_markets'] + syms,
                'funding': ['date', 'funding_oi_weighted', 'funding_mean', 'n_markets'] + syms,
                'lsratio': ['date', 'ls_ratio_mean', 'n_markets'] + ls_syms}
        old = {k: read_existing(p) for k, p in files.items()}
        same = all(old[k][1] == cols[k] for k in ('oi', 'funding')) and all(old[k][0] for k in ('oi', 'funding'))
        if same:
            newest = min(max(old[k][0]) for k in ('oi', 'funding'))
            start = dt.date.fromisoformat(newest) - dt.timedelta(days=7)
        else:                                  # first run, or the market list changed: full backfill
            old = {k: ({}, []) for k in files}
            start = START
        print(f'{asset}: {len(syms)} markets, fetching from {start}')
        oi = history('/open-interest-history', syms, start, {'convert_to_usd': 'true'})
        fr = history('/funding-rate-history', syms, start)
        ls = history('/long-short-ratio-history', ls_syms, start) if ls_syms else {}

        def merge(kind, _cols, rowfn, series_dates):
            rows = dict(old[kind][0])
            for d in series_dates:
                rows[d] = rowfn(d)
            write(files[kind], cols[kind], [rows[d] for d in sorted(rows)])

        dates = sorted({d for s in oi.values() for d in s})
        def oi_row(d):
            vals = [oi[s][d]['c'] if d in oi.get(s, {}) else '' for s in syms]
            num = [v for v in vals if v != '']
            return [d, round(sum(num), 2) if num else '', len(num)] + vals
        merge('oi', ['date', 'oi_usd_total', 'n_markets'] + syms, oi_row, dates)

        fdates = sorted({d for s in fr.values() for d in s})
        def fr_row(d):
            vals = [fr[s][d]['c'] if d in fr.get(s, {}) else '' for s in syms]
            pairs = [(fr[s][d]['c'], oi[s][d]['c']) for s in syms
                     if d in fr.get(s, {}) and d in oi.get(s, {}) and oi[s][d]['c']]
            w = sum(o for _, o in pairs)
            wavg = sum(f * o for f, o in pairs) / w if w else ''
            num = [v for v in vals if v != '']
            return [d, wavg, sum(num) / len(num) if num else '', len(num)] + vals
        merge('funding', ['date', 'funding_oi_weighted', 'funding_mean', 'n_markets'] + syms, fr_row, fdates)

        if ls_syms:
            ldates = sorted({d for s in ls.values() for d in s})
            def ls_row(d):
                vals = [ls[s][d]['r'] if d in ls.get(s, {}) else '' for s in ls_syms]
                num = [v for v in vals if v != '']
                return [d, sum(num) / len(num) if num else '', len(num)] + vals
            merge('lsratio', ['date', 'ls_ratio_mean', 'n_markets'] + ls_syms, ls_row, ldates)
        log(f'{asset}: {len(syms)} markets from {start}; OI days {len(dates)}, funding days {len(fdates)}, '
            f'long/short markets {len(ls_syms)}')
    flush()


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        import traceback
        log('CRASH: ' + traceback.format_exc()[-1500:])
        flush()
        raise
