"""Items 1-7: compare the feed and datasets with my own values. Appends rows to checks_<state>.csv."""
import csv, datetime as dt, json, os, pickle, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import *

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = sys.argv[1]
NAME = os.path.basename(STATE.rstrip('/'))
P = pickle.load(open(os.path.join(HERE, f'sig_{NAME}.pkl'), 'rb'))
NOW, SIG = P['NOW'], P['SIG']
TODAY = NOW.date()
feed = json.load(open(os.path.join(STATE, 'feed', 'ctzb_feed.json')))
LED = list(csv.DictReader(open(os.path.join(STATE, 'datasets', 'ledger.csv'))))
daily = {a: Daily(STATE, a, NOW) for a in ('ETH', 'BTC')}
OUT = []


def same(x, y):
    if x is None or x == '':
        return y is None or y == ''
    if y is None or y == '':
        return False
    if isinstance(x, bool) or isinstance(y, bool):
        return x == y
    try:
        return float(x) == float(y)
    except (TypeError, ValueError):
        return str(x) == str(y)


def chk(loc, label, shown, mine, cause=''):
    ok = same(shown, mine)
    OUT.append(dict(state=NAME, location=loc, label=label, shown=shown, yours=mine, ok=ok, cause='' if ok else cause))
    return ok


# ------------------------------------------------------------------ 1. ledger
mine_led = {}
for (a, tf), v in SIG.items():
    if tf == '8D':
        continue
    for s in v['sig']:
        if not (s['gated'] and s['closed'] and s['m'] is not None):
            continue
        if a == 'ETH' and not s['fund_ok']:
            continue
        mine_led[(s['chart'], str(s['d0']))] = s
shown_led = {(r['chart'], r['entry']): r for r in LED}
for k in sorted(set(mine_led) | set(shown_led)):
    chk('ledger membership', f'{k[0]} {k[1]}', 'in ledger' if k in shown_led else 'absent', 'in ledger' if k in mine_led else 'absent',
        'membership')
for k in sorted(set(mine_led) & set(shown_led)):
    s, r = mine_led[k], shown_led[k]; m = s['m']; loc = f'ledger {k[0]} {k[1]}'
    chk(loc, 'low (trough bar open date)', r['low'], str(s['tdate']))
    chk(loc, 'entryPrice', r['entryPrice'], rha(s['e'], 2))
    chk(loc, 'entry = daily close on entry date', r['entryPrice'], rha(s['dclose'], 2))
    chk(loc, 'tags', r['tags'], tagstr(s))
    chk(loc, 'bestMove', r['bestMove'], r6(m['up']))
    chk(loc, 'maxDrawdown', r['maxDrawdown'], r6(m['dd']))
    chk(loc, 'dipBeforeHigh', r['dipBeforeHigh'], r6(m['ddpk']))
    chk(loc, 'return60d', r['return60d'], r6(m['ret']))
    chk(loc, 'daysToHigh', r['daysToHigh'], m['dpk'])
    chk(loc, 'year', r['year'], s['d0'].year)
    yn = lambda b: 'yes' if b else 'no'
    chk(loc, 'reached10', r['reached10'], yn(m['r10']))
    chk(loc, 'reached15', r['reached15'], yn(m['r15']))
    chk(loc, 'reached20', r['reached20'], yn(m['r20']))
    chk(loc, 'touched30', r['touched30'], yn(m['t30']))
    chk(loc, 'surv10', r['surv10'], yn(m['surv10']))
    chk(loc, 'scaled20', r['scaled20'], '' if s['sc20'] is None else yn(s['sc20']))
    s['grade'] = r['grade']; s['lenses'] = r['lenses']
LG = [mine_led[k] for k in sorted(mine_led, key=lambda k: (k[1], k[0])) if k in shown_led]

# ------------------------------------------------------------------ 2. grade_odds
GO = {(g['asset'], g['grade']): g for g in feed['grade_odds']}
def med6(xs):
    return st.median([r6(x) for x in xs])
def grp_stats(G):
    n = len(G)
    return dict(n=n, r10=rha(100 * sum(s['m']['r10'] for s in G) / n), s10=rha(100 * sum(s['m']['surv10'] for s in G) / n),
                r20=rha(100 * sum(s['m']['r20'] for s in G) / n), md=rha(med6([s['m']['dd'] for s in G]), 1),
                mdfull=rha(st.median([s['m']['dd'] for s in G]), 1),
                sample=f"{min(s['d0'] for s in G)} to {max(s['d0'] for s in G)}")
groups = {}
for a in ('ETH', 'BTC'):
    for g in ('A+', 'A', 'B', 'C'):
        groups[(a, g)] = [s for s in LG if s['a'] == a and s['grade'] == g]
groups[('ETH', 'diamond or prime dot')] = [s for s in LG if s['a'] == 'ETH' and (s['dis'] or s['prime'])]
groups[('ETH', 'no diamond or prime dot')] = [s for s in LG if s['a'] == 'ETH' and not (s['dis'] or s['prime'])]
for key, G in groups.items():
    g = GO.get(key); loc = f'grade_odds {key[0]} {key[1]}'
    if g is None:
        chk(loc, 'row present', 'absent', 'present', 'missing row'); continue
    x = grp_stats(G)
    chk(loc, 'past_trades', g['past_trades'], x['n']); chk(loc, 'past_signals', g['past_signals'], x['n'])
    chk(loc, 'rose10_within60d_pct', g['rose10_within60d_pct'], x['r10'])
    chk(loc, 'rose10_never_fell25_within60d_pct', g['rose10_never_fell25_within60d_pct'], x['s10'])
    chk(loc, 'rose20_within60d_pct', g['rose20_within60d_pct'], x['r20'])
    chk(loc, 'median_deepest_dip_pct', g['median_deepest_dip_pct'], x['md'])
    if x['md'] != x['mdfull']:
        OUT.append(dict(state=NAME, location=loc, label='median_deepest_dip_pct (full precision vs 6dp)', shown=x['mdfull'], yours=x['md'], ok=False, cause='6dp vs full precision median'))
    chk(loc, 'sample', g['sample'], x['sample'])
    chk(loc, 'label', g['label'][:24], 'Computed signal, not a f')
for key in GO:
    if key not in groups:
        OUT.append(dict(state=NAME, location=f'grade_odds {key[0]} {key[1]}', label='HTF-divergence row (lens logic, out of scope)', shown='', yours='', ok=True, cause='not checked: lens logic'))

# ------------------------------------------------------------------ 3. if_it_misses
for mrow in feed['if_it_misses']:
    a, g = mrow['asset'], mrow['grade']; loc = f'if_it_misses {a} {g}'
    G = groups[(a, g)]; M = [s for s in G if not s['m']['r10']]
    best = [r6(s['m']['up']) for s in M]
    chk(loc, 'signals', mrow['signals'], len(G)); chk(loc, 'misses', mrow['misses'], len(M))
    chk(loc, 'up_first (went above entry)', mrow['up_first'], sum(max(h for h, l in s['m']['w']) > s['e'] for s in M))
    chk(loc, 'median_peak_pct', mrow['median_peak_pct'], rha(st.median(best), 1) if M else None)
    chk(loc, 'mean_peak_pct', mrow['mean_peak_pct'], rha(st.mean(best), 1) if M else None)
    chk(loc, 'peaked_5_or_more', mrow['peaked_5_or_more'], sum(max(h for h, l in s['m']['w']) >= s['e'] * 1.05 for s in M))
    chk(loc, 'peaked_10_or_more', mrow['peaked_10_or_more'], sum(max(h for h, l in s['m']['w']) >= s['e'] * 1.10 for s in M))
    chk(loc, 'median_worst_drop_pct', mrow['median_worst_drop_pct'], rha(st.median([r6(s['m']['dd']) for s in M]), 1) if M else None)
    chk(loc, 'median_day60_pct', mrow['median_day60_pct'], rha(st.median([r6(s['m']['ret']) for s in M]), 1) if M else None)
    chk(loc, 'miss_rule', mrow['miss_rule'], 'did not rise 10% within 60 days')
    if M:
        for lab, xs in (('median_peak_pct', [s['m']['up'] for s in M]), ('median_worst_drop_pct', [s['m']['dd'] for s in M]), ('median_day60_pct', [s['m']['ret'] for s in M])):
            if rha(st.median(xs), 1) != rha(st.median([r6(x) for x in xs]), 1):
                OUT.append(dict(state=NAME, location=loc, label=lab + ' full-precision vs 6dp', shown=rha(st.median(xs), 1), yours=rha(st.median([r6(x) for x in xs]), 1), ok=False, cause='precision'))
present = {(m['asset'], m['grade']) for m in feed['if_it_misses']}
for a in ('ETH', 'BTC'):
    for g in ('A+', 'A', 'B', 'C'):
        if (a, g) not in present and groups[(a, g)]:
            chk(f'if_it_misses {a} {g}', 'row present', 'absent', 'present', 'missing row')

pickle.dump(dict(LG=LG, groups=groups), open(os.path.join(HERE, f'led_{NAME}.pkl'), 'wb'))
exec(open(os.path.join(HERE, 'checks2.py')).read())

with open(os.path.join(HERE, f'checks_{NAME}.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(OUT)
bad = [o for o in OUT if not o['ok']]
print(NAME, len(OUT), 'checks', len(bad), 'disagree')
for o in bad[:80]:
    print('  ', o['location'], '|', o['label'], '| shown', o['shown'], '| mine', o['yours'], '|', o['cause'])
