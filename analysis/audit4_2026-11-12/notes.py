"""Definitional side-checks. python3 notes.py <tag> <state_dir> <now>"""
import csv, datetime as dt, json, os, sys
from fractions import Fraction as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
from mine import State, all_rows, GRADED
import check as CK

tag, sdir, now_s = sys.argv[1:4]
now = dt.datetime.fromisoformat(now_s.replace('Z', '+00:00'))
S = State(sdir, now); rows = all_rows(S); out = {}
L = {(r['chart'], r['entry']): r for r in S.ledger}
led = [r for r in rows if (r['chart'], str(r['d0'])) in L and r['m']]
for r in led:
    x = L[(r['chart'], str(r['d0']))]; r['grade'] = x['grade']; r['lenses'] = set() if x['lenses'] == '-' else set(x['lenses'].split(' + '))

# 1. candle files served to the page = raw data
bad = []
for a in ('ETH', 'BTC'):
    for tf in ('1D', '2D', '3D', '5D', '8D'):
        raw = list(csv.DictReader(open(f'{sdir}/data/{a}_{tf}.csv')))[-70:]
        srv = list(csv.DictReader(open(f'{sdir}/datasets/candles_{a.lower()}_{tf.lower()}.csv')))
        if [(r['time'], r['open'], r['high'], r['low'], r['close']) for r in raw] != [(r['time'], r['open'], r['high'], r['low'], r['close']) for r in srv]:
            bad.append(f'{a}_{tf}')
out['candle_files_differ_from_raw'] = bad
ex = json.load(open(f'{sdir}/docs/artifacts/member-site/data/example_ETH-2D-2024-09-22.json'))
b2 = Bars(f'{sdir}/data/ETH_2D.csv')
mis = []
for b in ex['bars']:
    d = dt.datetime.fromtimestamp(b['t'], dt.timezone.utc).date(); i = b2.pos[d]
    for k, arr in (('o', b2.o), ('h', b2.h), ('l', b2.l), ('c', b2.c)):
        if F(str(b[k])) != arr[i]: mis.append((str(d), k, b[k], float(arr[i])))
out['example_json_bar_mismatches'] = mis
out['example_entry_bar_open'] = str(dt.datetime.fromtimestamp(ex['bars'][ex['entry_index']]['t'], dt.timezone.utc).date())
out['example_bars_after_entry'] = len(ex['bars']) - 1 - ex['entry_index']

# 2. ladder same-day ambiguity: does reading the bar the other way change any card figure?
def alt_ladder(day, e, w, th):
    up10 = e * F(11, 10); fall = e * (1 - F(th, 100)); liq = e * (1 - LIQ)
    for n, (k, j) in enumerate(w):
        if day.l[j] <= fall:       # fall read first
            for k2, j2 in w[n:]:
                if day.h[j2] >= up10: return 'ok'     # rise read first
                if day.l[j2] <= liq: return 'liq'
            return 'neither'
        if day.h[j] >= up10: return None
    return None
feed = S.feed
cards = [(c['signal_id'], c) for c in feed['cards']] + [(o['signal_id'], o['card']) for o in feed['open_signals'] if o['card']] + [('example', feed['example_card'])]
amb = []
for sid, c in cards:
    a, tf = c['asset'], c['timeframe']
    lens = set() if c['confirmations'] == 'none' else {CK.RPLAIN[x] for x in c['confirmations'].split('; ')}
    pool = [r for r in led if r['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)] if sid == 'example' else led
    Cf = [r for r in pool if r['a'] == a and r['tf'] == tf]
    ex_ = [r for r in Cf if r['lenses'] == lens]; sg = [r for r in Cf if r['grade'] == c['grade']]; ag = [r for r in pool if r['a'] == a and r['grade'] == c['grade']]
    G = ex_ if len(ex_) >= 15 else sg if len(sg) >= 15 else ag
    for th, row in zip((5, 10, 15, 20), c['if_it_falls_first']):
        res = [alt_ladder(S.day[a], r['entry'], r['m']['w'], th) for r in G]
        hit = sum(1 for x in res if x is not None); ok = sum(1 for x in res if x == 'ok'); lq = sum(1 for x in res if x == 'liq')
        alt = (hit, rnd(F(100 * ok, hit)) if hit else None, rnd(F(100 * lq, hit)) if hit else None)
        if alt != (row['past_trades'], row['still_rose10_pct'], row['went_on_to_fall25_pct']):
            amb.append(dict(card=sid, fell=th, shown=(row['past_trades'], row['still_rose10_pct'], row['went_on_to_fall25_pct']), other_reading=alt))
out['ladder_rows_that_depend_on_same_day_order'] = amb

# 3. tier: as coded (signals before 1 Jan, outcomes known later) vs only outcomes known by 1 Jan
f1, _ = CK.odds_fade(S, now); f2, _ = CK.odds_fade(S, now, strict=True)
out['tier_as_coded'] = f1['keep']; out['tier_strict_known_by_jan1'] = f2['keep']
out['fade_strict'] = dict(early=f2['early_dip'], day10=f2['day10'])

# 4. "up first" for misses: how many misses made their 60-day high only AFTER their deepest low
for a in ('ETH', 'BTC'):
    for g in ('A+', 'A', 'B', 'C'):
        ms = [r for r in led if r['a'] == a and r['grade'] == g and not r['m']['r10']]
        out[f'misses {a} {g}: high after the deepest low'] = f"{sum(1 for r in ms if r['m']['dpk'] > r['m']['ddday'])} of {len(ms)}"

for a, g in (('ETH', 'A+'), ('BTC', 'A+'), ('ETH', 'C'), ('BTC', 'C')):
    ms = [r for r in led if r['a'] == a and r['grade'] == g and not r['m']['r10']]
    lit = []
    for r in ms:
        day = S.day[a]; w = r['m']['w']; kl = r['m']['ddday']
        pre = [day.h[j] for k, j in w if k <= kl]
        lit.append(max(pre) > r['entry'])
    pk = [pct(max(S.day[a].h[j] for k, j in r['m']['w'] if k <= r['m']['ddday']), r['entry']) for r in ms]
    out[f'misses {a} {g}: above entry BEFORE the deepest low'] = f"{sum(lit)} of {len(ms)}; median peak before the deepest low {rnd(median(pk), 1)}"
# 5. gate on the trough date vs on the confirmation date: graded signals that would change
diff = []
for (a, tf), b in S.bars.items():
    if tf not in GRADED: continue
    tr, ct, k = troughs(b)
    for t in tr:
        d0 = b.close_date(t['ei'])
        if d0 is None: continue
        g1 = S.gate(b.date[t['ti']]); g2 = S.gate(d0)
        if g1 != g2: diff.append(f"{a} {tf} {d0} trough-gate={g1} confirm-gate={g2}")
out['gate_trough_vs_confirmation_differs'] = diff

# 6. A+ per year 2020-2025 (hard-coded "about 22 times a year (2020 to 2025 average)")
ap = [r for r in led if r['grade'] == 'A+' and 2020 <= r['d0'].year <= 2025]
out['A+ signals 2020-2025 per year (ETH+BTC, closed)'] = str(F(len(ap), 6)) + f' = {len(ap) / 6:.2f} ({len(ap)} signals)'
out['A+ distinct dates 2020-2025 per year'] = len({(r['a'], r['d0']) for r in ap}) / 6

# 7. 8D signals within 60 days (spec: open signals cover 1D-5D only)
out['8D signals inside 60 days'] = [f"{a} 8D {s['d0']}" for a in ('ETH', 'BTC') for s in S.sig[(a, '8D')] if s['d0'] and 0 <= (now.date() - s['d0']).days <= 60]

# 8. confirmation bars that confirmed on the still-forming bar are excluded (none listed); signals per chart today
out['now'] = now_s
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'notes_{tag}.json'), 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)[:6000])

# 9. where the multi-day trough bar's low was actually printed (daily candles)
lows = {}
for c in feed['cards'] + [o['card'] for o in feed['open_signals'] if o['card'] and o['grade'] == 'A+'] + [feed['example_card']]:
    tf = int(c['timeframe'][:-1]); a = c['asset']
    if tf == 1: continue
    b = Bars(f"{sdir}/data/{a}_{c['timeframe']}.csv"); i = b.pos[dt.date.fromisoformat(c['low_date'])]
    day = S.day[a]; ds = [b.date[i] + dt.timedelta(days=k) for k in range(tf)]
    lows[c['signal_id']] = dict(bar_open=c['low_date'], bar_low=float(b.l[i]), printed_on=[str(d) for d in ds if d in day.pos and day.l[day.pos[d]] == b.l[i]])
out['trough_low_printed_on'] = lows
# 10. ladder "still rose 10%": cases that rose 10% after the fall and THEN fell 25.3% within the 60 days
later = []
for sid, c in cards:
    a = c['asset']
    lens = set() if c['confirmations'] == 'none' else {CK.RPLAIN[x] for x in c['confirmations'].split('; ')}
    pool = [r for r in led if r['d0'] + dt.timedelta(days=60) <= dt.date(2024, 9, 22)] if sid == 'example' else led
    Cf = [r for r in pool if r['a'] == a and r['tf'] == c['timeframe']]
    ex_ = [r for r in Cf if r['lenses'] == lens]; sg = [r for r in Cf if r['grade'] == c['grade']]; ag = [r for r in pool if r['a'] == a and r['grade'] == c['grade']]
    G = ex_ if len(ex_) >= 15 else sg if len(sg) >= 15 else ag
    for th in (5, 10, 15, 20):
        k = 0
        for r in G:
            res, _ = ladder(S.day[a], r['d0'], r['entry'], r['m']['w'], th)
            if res == 'ok' and not r['m']['surv10']: k += 1
        if k: later.append(f'{sid} {th}%: {k} counted as "still rose 10%" then fell 25.3% later in the 60 days')
out['ladder_ok_then_fell_25'] = later
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f'notes_{tag}.json'), 'w'), indent=1, default=str)
