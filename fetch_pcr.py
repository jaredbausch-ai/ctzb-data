"""Options put/call ratio for BTC and ETH, from Deribit, daily, with HISTORY.

Built 27 Oct 2026 after Jared saw Krown's "Krown PCR" panel (BTC options,
Deribit + ETFs, daily PCR, 7-day average, 100-day percentile, zone). Krown
cannot release his because of paid back-end feeds. This is the free half of it:
Deribit, which carries most BTC and ETH options volume. The ETF (IBIT) options
leg is NOT here -- no free source has its history. NO API KEY.

The container cannot reach Deribit (agent proxy 403), so this runs in the
GitHub Action like the rest of the pipeline.

SOURCE. history.deribit.com public/get_last_trades_by_currency_and_time, every
option trade on the inverse (coin-settled) BTC and ETH books, all expiries,
back to the start of each book. Daily UTC aggregates are rebuilt from trades,
so the volume put/call ratio has a full history to backtest against. Open
interest has no history in that API; a daily snapshot is taken from the live
book summary from the first run onward.

Each run (a) fills forward to yesterday, (b) takes today's open-interest
snapshot once per UTC day, then (c) backfills older days, newest first, until
--budget seconds are used. Every finished day is written immediately, so a run
that is killed loses at most the day in progress. Once both histories reach
their start dates the backfill is a no-op.

Writes, under data/options/:
  {CUR}_pcr_daily.csv   date, trades, call_trades, put_trades, call_amt,
                        put_amt, call_usd, put_usd, call_prem_usd,
                        put_prem_usd, call_buy_amt, call_sell_amt,
                        put_buy_amt, put_sell_amt, pcr_amt, pcr_prem
      amt = contracts (1 = 1 coin); usd = amt x index price; prem_usd = the
      premium paid in USD. buy/sell = the taker's side. pcr_amt = put_amt /
      call_amt, the standard volume put/call ratio. pcr_prem = by premium.
  {CUR}_oi_snapshot.csv date, ts, call_oi, put_oi, pcr_oi, call_vol24, put_vol24
  fetch_log.txt         appended
"""
import argparse, csv, datetime as dt, json, os, time, urllib.parse, urllib.request

OUT = 'data/options'
HIST = 'https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time'
LIVE = 'https://www.deribit.com/api/v2/public/get_book_summary_by_currency'
START = {'BTC': dt.date(2016, 11, 1), 'ETH': dt.date(2019, 3, 1)}
COLS = ['date', 'trades', 'call_trades', 'put_trades', 'call_amt', 'put_amt', 'call_usd', 'put_usd',
        'call_prem_usd', 'put_prem_usd', 'call_buy_amt', 'call_sell_amt', 'put_buy_amt', 'put_sell_amt',
        'pcr_amt', 'pcr_prem']
OICOLS = ['date', 'ts', 'call_oi', 'put_oi', 'pcr_oi', 'call_vol24', 'put_vol24']
LOG = []


def log(m):
    print(m, flush=True); LOG.append(f'{dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M:%S} {m}')


def get(url, params, tries=6):
    q = url + '?' + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(q, headers={'User-Agent': 'ctzb-pipeline/1.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())['result']
        except Exception as e:
            wait = 2 ** i
            log(f'  {type(e).__name__}: {str(e)[:80]} -- retry in {wait}s')
            time.sleep(wait)
    raise RuntimeError(f'gave up on {q[:120]}')


def ms(d):
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.UTC).timestamp() * 1000)


def day_agg(cur, day):
    """Aggregate every option trade on `day` (UTC). Returns a row dict."""
    lo, hi = ms(day), ms(day + dt.timedelta(days=1)) - 1
    seen = set(); start = lo
    a = {k: 0.0 for k in COLS[1:14]}
    while True:
        res = get(HIST, dict(currency=cur, kind='option', start_timestamp=start, end_timestamp=hi,
                             count=1000, sorting='asc', include_old='true'))
        tr = res.get('trades', [])
        new = [t for t in tr if t['trade_id'] not in seen]
        for t in new:
            seen.add(t['trade_id'])
            name = t['instrument_name']
            if not name.startswith(cur + '-'):
                continue
            side = 'call' if name.endswith('-C') else 'put' if name.endswith('-P') else None
            if side is None:
                continue
            amt = float(t['amount']); idx = float(t.get('index_price') or 0); px = float(t['price'])
            a['trades'] += 1; a[f'{side}_trades'] += 1
            a[f'{side}_amt'] += amt; a[f'{side}_usd'] += amt * idx; a[f'{side}_prem_usd'] += px * amt * idx
            a[f'{side}_{"buy" if t.get("direction") == "buy" else "sell"}_amt'] += amt
        if not res.get('has_more') or not tr:
            break
        last = tr[-1]['timestamp']
        if not new:                              # a whole page inside one millisecond: step past it
            log(f'  WARNING {cur} {day}: >1000 trades at ts {last}, some may be skipped')
            start = last + 1
        else:
            start = last                         # re-request the boundary ms; ids dedupe it
        time.sleep(0.05)
    row = {'date': day.isoformat()}
    for k in COLS[1:14]:
        row[k] = int(a[k]) if k.endswith('trades') else round(a[k], 4)
    row['pcr_amt'] = round(a['put_amt'] / a['call_amt'], 4) if a['call_amt'] else ''
    row['pcr_prem'] = round(a['put_prem_usd'] / a['call_prem_usd'], 4) if a['call_prem_usd'] else ''
    return row


def load(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {r['date']: r for r in csv.DictReader(f)}


def save(path, rows, cols):
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for d in sorted(rows):
            w.writerow(rows[d])
    os.replace(tmp, path)


def oi_snapshot(cur):
    path = f'{OUT}/{cur}_oi_snapshot.csv'; rows = load(path)
    today = dt.datetime.now(dt.UTC).date().isoformat()
    if today in rows:
        return
    res = get(LIVE, dict(currency=cur, kind='option'))
    c = {'C': [0.0, 0.0], 'P': [0.0, 0.0]}
    for x in res:
        k = x['instrument_name'][-1]
        if k in c:
            c[k][0] += float(x.get('open_interest') or 0); c[k][1] += float(x.get('volume') or 0)
    rows[today] = dict(date=today, ts=dt.datetime.now(dt.UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
                       call_oi=round(c['C'][0], 2), put_oi=round(c['P'][0], 2),
                       pcr_oi=round(c['P'][0] / c['C'][0], 4) if c['C'][0] else '',
                       call_vol24=round(c['C'][1], 2), put_vol24=round(c['P'][1], 2))
    save(path, rows, OICOLS)
    log(f'{cur} OI snapshot {today}: pcr_oi {rows[today]["pcr_oi"]}')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--budget', type=int, default=1500)
    args = ap.parse_args()
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    yday = dt.datetime.now(dt.UTC).date() - dt.timedelta(days=1)
    data = {c: load(f'{OUT}/{c}_pcr_daily.csv') for c in START}

    def do(cur, day):
        row = day_agg(cur, day); data[cur][row['date']] = row
        save(f'{OUT}/{cur}_pcr_daily.csv', data[cur], COLS)
        log(f'{cur} {row["date"]}: {row["trades"]} trades, pcr_amt {row["pcr_amt"]}')

    try:
        for cur in START:                                       # (a) forward to yesterday
            have = sorted(data[cur])
            d = dt.date.fromisoformat(have[-1]) + dt.timedelta(days=1) if have else yday
            while d <= yday:
                do(cur, d); d += dt.timedelta(days=1)
        for cur in START:                                       # (b) open interest, once a day
            try:
                oi_snapshot(cur)
            except Exception as e:
                log(f'{cur} OI snapshot failed: {e}')
        while time.time() - t0 < args.budget:                   # (c) backfill, newest first
            moved = False
            for cur in START:
                have = sorted(data[cur])
                d = dt.date.fromisoformat(have[0]) - dt.timedelta(days=1)
                if d < START[cur]:
                    continue
                do(cur, d); moved = True
                if time.time() - t0 >= args.budget:
                    break
            if not moved:
                log('backfill complete for both books'); break
    finally:
        for cur in START:
            have = sorted(data[cur])
            if have:
                log(f'{cur} history {have[0]} -> {have[-1]} ({len(have)} days)')
        lp = f'{OUT}/fetch_log.txt'
        old = open(lp).read().splitlines() if os.path.exists(lp) else []
        with open(lp, 'w') as f:                                # keep the last 3,000 lines
            f.write('\n'.join((old + LOG)[-3000:]) + '\n')


if __name__ == '__main__':
    main()
