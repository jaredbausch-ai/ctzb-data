"""Audit 15 -- data checks 1-7 for one state. Usage: python3 audit_data.py <state dir> <state name>
Writes checks_<state>.csv (state, location, label, shown, yours, ok, cause)."""
import sys, csv, json, datetime as dt, collections, re, pickle
from core import *
S, NAME = sys.argv[1], sys.argv[2]
now, feed = now_of(S)
W = World(S, now); C = Checks(NAME); today = W.today
led = list(csv.DictReader(open(f'{S}/datasets/ledger.csv')))
ALL = {(s['chart'], str(s['d0'])): s for v in W.sig.values() for s in v}
yn = lambda b: 'yes' if b else 'no'
D60 = dt.timedelta(days=60)

# ============================================================ 1. ledger
graded = {k: s for k, s in ALL.items() if s['tf'] in GRADED}
lk = {(r['chart'], r['entry']): r for r in led}
C.add('ledger', 'rows are unique (chart, entry)', len(lk), len(led))
first = {a: min(r['entry'] for r in led if r['asset'] == a) for a in ASSETS}
for k in lk:
    C.add('ledger membership', f'{k[0]} {k[1]} is one of my graded-chart signals with a closed 60-day window',
          'yes', yn(k in graded and graded[k]['m'] is not None), 'ledger row is not a signal by my detection, or its 60th day has not closed')
for k, s in graded.items():
    if s['m'] is None or k in lk: continue
    if s['a'] == 'ETH' and k[1] < first['ETH']: continue      # before ETH grading starts (funding history), CARD_SPEC
    C.add('ledger membership', f'{k[0]} {k[1]} (my signal, 60 days closed) is in the ledger', 'no', 'yes', 'signal missing from the ledger')
n_pre = sum(1 for k, s in graded.items() if s['m'] is not None and k not in lk and s['a'] == 'ETH' and k[1] < first['ETH'])
print('ETH signals before the first graded ETH signal (not in ledger, by design):', n_pre, 'first graded', first)

G_by = collections.defaultdict(list)
for r in led: G_by[(r['asset'], r['grade'])].append(r)
def M(r): return graded[(r['chart'], r['entry'])]['m']
def SG(r): return graded[(r['chart'], r['entry'])]
grade_stats = {}
for (a, g), G in G_by.items():
    n = len(G)
    grade_stats[(a, g)] = dict(n=n, r20=rhu(Fr(100 * sum(M(r)['r20'] for r in G), n)), t30=rhu(Fr(100 * sum(M(r)['t30'] for r in G), n)),
                               md=rhu(median([M(r)['dd'] for r in G]), 1))
hist = sorted(led, key=lambda r: r['entry'])
def day_odds(r):
    a, g, d0 = r['asset'], r['grade'], dt.date.fromisoformat(r['entry'])
    prior = [h for h in hist if h['asset'] == a and dt.date.fromisoformat(h['entry']) + D60 <= d0]
    Gp = [h for h in prior if h['grade'] == g]
    if len(Gp) < 10 or not prior: return ['', '', '', '', len(Gp), '', '']
    def rate(fn, ok=lambda h: True):
        P = [h for h in prior if ok(h)]; Gk = [h for h in Gp if ok(h)]
        if not P or not Gk: return ''
        base = Fr(sum(fn(h) for h in P), len(P))
        return rhu(100 * (sum(fn(h) for h in Gk) + 5 * base) / (len(Gk) + 5))
    sc = lambda h: W.scaled20(SG(h))
    return [rate(lambda h: M(h)['r10']), rate(lambda h: M(h)['r20']), rate(lambda h: M(h)['r30']), rate(lambda h: M(h)['t30']), len(Gp),
            rate(lambda h: M(h)['r10'] and not M(h)['liq']), rate(lambda h: bool(sc(h)), ok=lambda h: sc(h) is not None)]
for r in led:
    k = (r['chart'], r['entry'])
    if k not in graded or graded[k]['m'] is None: continue
    s = graded[k]; m = s['m']; loc = f'ledger {k[0]} {k[1]}'
    C.add(loc, 'asset', r['asset'], s['a'])
    C.add(loc, 'low (trough bar date)', r['low'], str(s['tdate']))
    C.add(loc, 'entryPrice (close of the confirmation bar)', r['entryPrice'], rhu(s['entry'], 2))
    C.add(loc, 'entryPrice equals the daily close on the entry date', r['entryPrice'], rhu(W.day[s['a']].c[W.day[s['a']].pos[s['d0']]], 2))
    C.add(loc, 'tags', r['tags'], s['tags'])
    C.add(loc, 'reached20', r['reached20'], yn(m['r20']))
    C.add(loc, 'touched30', r['touched30'], yn(m['t30']))
    C.add(loc, 'bestMove', r['bestMove'], rhu(m['up'], 6))
    C.add(loc, 'maxDrawdown', r['maxDrawdown'], rhu(m['dd'], 6))
    C.add(loc, 'dipBeforeHigh', r['dipBeforeHigh'], rhu(m['ddpk'], 6))
    C.add(loc, 'return60d', r['return60d'], rhu(m['ret'], 6))
    C.add(loc, 'daysToHigh', r['daysToHigh'], m['dpk'])
    C.add(loc, 'year', r['year'], s['d0'].year)
    C.add(loc, 'reached10', r['reached10'], yn(m['r10']))
    C.add(loc, 'reached15', r['reached15'], yn(m['r15']))
    C.add(loc, 'surv10 (rose 10%, never fell 25.3%)', r['surv10'], yn(m['r10'] and not m['liq']))
    sc = W.scaled20(s)
    C.add(loc, 'scaled20', r['scaled20'], '' if sc is None else yn(sc))
    gs = grade_stats[(r['asset'], r['grade'])]
    C.add(loc, 'gradeReach20', r['gradeReach20'], gs['r20'])
    C.add(loc, 'gradeTouched30', r['gradeTouched30'], gs['t30'])
    C.add(loc, 'gradeMedDrawdown', r['gradeMedDrawdown'], gs['md'])
    for lab, v in zip(('dayReach10', 'dayReach20', 'dayReach30', 'dayTouched30', 'dayN', 'daySurv10', 'dayScaled20'), day_odds(r)):
        C.add(loc, lab, r[lab], v)
    lens = [x for x in r['lenses'].split(' + ') if x != '-']
    C.add(loc, 'grade letter matches the count of its lenses (C 0-1, B 2, A 3, A+ 4+)', r['grade'],
          'C' if len(lens) <= 1 else 'B' if len(lens) == 2 else 'A' if len(lens) == 3 else 'A+')
print('1 ledger', len(C.rows), sum(1 for x in C.rows if x[5] == 'NO'))
pickle.dump(C.rows, open(f'rows_{NAME}_1.pkl', 'wb'))

# ============================================================ 2. grade_odds
LABEL_NEEDS = ('Computed signal', 'not a fill', 'Entry quality only', 'not a strategy return or a track record')
def label_ok(x): return yn(all(w.lower() in (x or '').lower() for w in LABEL_NEEDS))
def share(G, fn):
    return rhu(Fr(100 * sum(1 for r in G if fn(r)), len(G))) if G else ''
def eshare(k, n): return rhu(Fr(100 * k, n), 6) if n else ''
go = feed['grade_odds']
C.add('feed grade_odds', 'rows', len(go), 12)
eth_all = [r for r in led if r['asset'] == 'ETH']
for g in go:
    loc = f"feed grade_odds {g['asset']} {g['grade']}"
    if g['grade'] in ('A+', 'A', 'B', 'C'): G = G_by[(g['asset'], g['grade'])]
    elif g['grade'] == 'diamond or prime dot': G = [r for r in eth_all if 'diamond' in r['tags'] or 'prime dot' in r['tags']]
    elif g['grade'] == 'no diamond or prime dot': G = [r for r in eth_all if not ('diamond' in r['tags'] or 'prime dot' in r['tags'])]
    else: G = None
    C.add(loc, 'label says computed / entry quality only', label_ok(g['label']), 'yes')
    C.add(loc, 'past_signals twin equals past_trades', g['past_signals'], g['past_trades'])
    if G is None:
        continue       # the two HTF-divergence rows: lens logic, out of scope (definitional note h)
    C.add(loc, 'past_trades', g['past_trades'], len(G))
    C.add(loc, 'rose10_within60d_pct', g['rose10_within60d_pct'], share(G, lambda r: M(r)['r10']))
    C.add(loc, 'rose10_never_fell25_within60d_pct', g['rose10_never_fell25_within60d_pct'], share(G, lambda r: M(r)['r10'] and not M(r)['liq']))
    C.add(loc, 'rose20_within60d_pct', g['rose20_within60d_pct'], share(G, lambda r: M(r)['r20']))
    C.add(loc, 'median_deepest_dip_pct', g['median_deepest_dip_pct'], rhu(median([M(r)['dd'] for r in G]), 1))
    C.add(loc, 'sample (first to last signal)', g['sample'], f"{min(r['entry'] for r in G)} to {max(r['entry'] for r in G)}")
hd = {g['grade']: g for g in go if g['asset'] == 'ETH'}
C.add('feed grade_odds ETH HTF rows', 'HTF + no-HTF counts add up to all graded ETH signals', hd['HTF divergence']['past_trades'] + hd['no HTF divergence']['past_trades'], len(eth_all))
print('2 grade_odds', len(C.rows))

# ============================================================ 3. if_it_misses
def miss_stats(G):
    m = [r for r in G if not M(r)['r10']]; best = [M(r)['up'] for r in m]
    if not m: return dict(signals=len(G), misses=0)
    return dict(signals=len(G), misses=len(m), up_first=sum(b > 0 for b in best), median_peak_pct=rhu(median(best), 1),
                mean_peak_pct=rhu(sum(best) / len(best), 1), peaked_5_or_more=sum(b >= 5 for b in best),
                peaked_10_or_more=sum(b >= 10 for b in best), median_worst_drop_pct=rhu(median([M(r)['dd'] for r in m]), 1),
                median_day60_pct=rhu(median([M(r)['ret'] for r in m]), 1))
imm = feed['if_it_misses']
C.add('feed if_it_misses', 'one row per asset and grade present in the ledger', len(imm), len(G_by))
for x in imm:
    loc = f"feed if_it_misses {x['asset']} {x['grade']}"; mine = miss_stats(G_by[(x['asset'], x['grade'])])
    for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'mean_peak_pct', 'peaked_5_or_more', 'peaked_10_or_more', 'median_worst_drop_pct', 'median_day60_pct'):
        C.add(loc, k, x.get(k), mine.get(k))
    C.add(loc, 'miss_rule', x['miss_rule'], 'did not rise 10% within 60 days')
    C.add(loc, 'label says computed / entry quality only', label_ok(x['label']), 'yes')
EXD = dt.date(2024, 9, 22)
known = [r for r in led if dt.date.fromisoformat(r['entry']) + D60 <= EXD]
ex_ap = [r for r in known if r['asset'] == 'ETH' and r['grade'] == 'A+']
x = feed['example_if_it_misses'] or {'asset': 'ETH', 'grade': 'A+', 'miss_rule': 'did not rise 10% within 60 days', 'label': feed['label']}; mine = miss_stats(ex_ap) if ex_ap else {}
for k in ('signals', 'misses', 'up_first', 'median_peak_pct', 'median_worst_drop_pct', 'median_day60_pct'):
    C.add('feed example_if_it_misses', k, x.get(k), mine.get(k))
C.add('feed example_if_it_misses', 'asset/grade', f"{x['asset']} {x['grade']}", 'ETH A+')
C.add('feed example_if_it_misses', 'miss_rule', x['miss_rule'], 'did not rise 10% within 60 days')
C.add('feed example_if_it_misses', 'label says computed / entry quality only', label_ok(x['label']), 'yes')
print('3 misses', len(C.rows))

# ============================================================ 4. odds_fade (own implementation of the documented rule)
def zmin_series(ct):
    out = []; z = None
    for v in ct:
        if v is None: out.append(None); continue
        z = None if v >= 60 else (v if z is None else min(z, v)); out.append(z)
    return out
def tier_tags(s, zm):
    t = {s['bk'], 'any trough'}
    if s['dis']: t |= {'diamond', 'filled' if s['strong'] else 'hollow'}
    if s['prime']: t.add('prime dot')
    if s['dis'] and s['prime']: t.add('diamond+dot')
    if s['bk'] == 'B' and s['ct'] < 60 and zm[s['ti']] is not None and zm[s['ti']] >= 50: t.add('zone-exit B')
    return t
TAGLIST = ["any trough", "A", "B", "C", "D", "diamond", "filled", "hollow", "prime dot", "diamond+dot", "zone-exit B"]
tier_rows = []        # every gated ETH signal with a complete 60-day outcome on its own chart's bars
eth_sig_tags = {}
for tf in TFS:
    ch = W.ch[('ETH', tf)]; b = ch.b; zm = zmin_series(ch.ct)
    for p in ch.pivots:
        if not W.gate(p['tdate']): continue
        tg = tier_tags(p, zm); ei = p['ei']; eo = b.date[ei]
        eth_sig_tags[(tf, eo)] = tg
        end = eo + D60
        if b.date[-1] < end: continue
        js = [j for j in range(ei + 1, b.n) if b.date[j] <= end]
        if not js: continue
        tier_rows.append(dict(chart=f'ETH {tf}', tf=tf, tags=tg, d=eo, win=b.c[js[-1]] > b.c[ei]))
JAN1 = dt.date(today.year, 1, 1)
keep = []
for tf in TFS:
    for t in TAGLIST:
        sub = [r for r in tier_rows if r['tf'] == tf and t in r['tags'] and r['d'] + dt.timedelta(days=int(tf[:-1]) - 1 + 60) < JAN1]
        if len(sub) >= 8 and Fr(100 * sum(r['win'] for r in sub), len(sub)) >= 70: keep.append((tf, t))
print('tier on', JAN1, keep)
pool = []
for tf in TFS:
    ch = W.ch[('ETH', tf)]
    for s in W.sig[('ETH', tf)]:
        tg = eth_sig_tags[(tf, ch.b.date[s['ei']])]
        if not any(k[0] == tf and k[1] in tg for k in keep): continue
        if s['m'] is None: continue
        D = W.day['ETH']; ks = s['m']['ks']; e = s['entry']; d0 = s['d0']
        dn = lambda k: (D.date[k] - d0).days
        lo10 = min(D.l[k] for k in ks if dn(k) <= 10); hi_after = max(D.h[k] for k in ks if dn(k) > 10)
        c10 = [D.c[k] for k in ks if dn(k) == 10]
        pool.append(dict(dip=(lo10 / e - 1) * 100, r10=hi_after >= e * Fr(110, 100), r20=hi_after >= e * Fr(120, 100), green=(c10[0] >= e) if c10 else None))
BANDS = [(100, -2, "shallower than -2%"), (-2, -5, "-2% to -5%"), (-5, -10, "-5% to -10%"), (-10, -20, "-10% to -20%"), (-20, -100, "worse than -20%")]
of = feed['odds_fade']
C.add('feed odds_fade', 'posting_bar_pct', of['posting_bar_pct'], 70)
C.add('feed odds_fade', 'edge_measured_on', of['edge_measured_on'], 'rose 10% after day 10 (days 11 to 60)')
C.add('feed odds_fade', 'label says computed / entry quality only', label_ok(of['label']), 'yes')
C.add('feed odds_fade', 'sample text names the tier date (1 Jan of this year), in-sample, daily candles, days 11 to 60',
      yn(all(w in of['sample'] for w in (f'1 Jan {today.year}', 'In-sample', 'daily candles', 'days 11 to 60', 'from 2016'))), 'yes')
mine_ed = []
for hi, lo, lab in BANDS:
    g = [p for p in pool if lo < p['dip'] <= hi]
    if len(g) >= 5: mine_ed.append((lab, g))
C.add('feed odds_fade early_dip', 'bands listed', ' | '.join(b['band'] for b in of['early_dip']), ' | '.join(l for l, _ in mine_ed))
def fade_row(loc, b, g):
    n = len(g); k10 = sum(p['r10'] for p in g); k20 = sum(p['r20'] for p in g)
    C.add(loc, 'past_trades', b['past_trades'], n); C.add(loc, 'past_signals', b['past_signals'], n)
    C.add(loc, 'rose10_after_day10_pct', b['rose10_after_day10_pct'], rhu(Fr(100 * k10, n)))
    C.add(loc, 'rose20_after_day10_pct', b['rose20_after_day10_pct'], rhu(Fr(100 * k20, n)))
    C.add(loc, 'rose10_within60d_pct (alias)', b['rose10_within60d_pct'], rhu(Fr(100 * k10, n)))
    C.add(loc, 'rose20_within60d_pct (alias)', b['rose20_within60d_pct'], rhu(Fr(100 * k20, n)))
    C.add(loc, 'edge (exact share vs 70%)', b['edge'], 'intact' if Fr(100 * k10, n) >= 70 else 'gone')
for b in of['early_dip']:
    g = dict(mine_ed).get(b['band'])
    if g is not None: fade_row(f"feed odds_fade early_dip {b['band']}", b, g)
mine_d10 = [(lab, [p for p in pool if p['green'] is sel]) for lab, sel in (('green on day 10', True), ('red on day 10', False))]
mine_d10 = [(l, g) for l, g in mine_d10 if len(g) >= 5]
C.add('feed odds_fade day10', 'checks listed', ' | '.join(b['check'] for b in of['day10']), ' | '.join(l for l, _ in mine_d10))
for b in of['day10']:
    g = dict(mine_d10).get(b['check'])
    if g is not None: fade_row(f"feed odds_fade day10 {b['check']}", b, g)
C.add('feed odds_fade', 'pool size: early-dip bands add up to every tier signal', sum(b['past_trades'] for b in of['early_dip']), len(pool))
print('4 odds_fade', len(C.rows), 'pool', len(pool))

# top-level trades_a_year: the tier's deduped signals per year over the scoreable span (refresh.ds_tier)
T = {}
for r in sorted(tier_rows, key=lambda r: r['d']):
    if any(k[0] == r['tf'] and k[1] in r['tags'] for k in keep): T.setdefault((r['chart'], r['d']), r)
data_end = max(W.ch[('ETH', tf)].b.date[-1] for tf in TFS)
span = max(Fr(1, 4), Fr((data_end - D60 - min(r['d'] for r in T.values())).days * 100, 36525))
per_year = Fr(len(T)) / span
C.add('feed top level', 'trades_a_year', feed['trades_a_year'], f'{rhu(per_year)} on average')
C.add('feed top level', 'signals_a_year (twin)', feed['signals_a_year'], f'{rhu(per_year)} on average')
C.add('feed top level', 'schema_version', feed['schema_version'], 6)
C.add('feed top level', 'posting_bar_pct', feed['posting_bar_pct'], 70)
C.add('feed top level', 'scored_as_of', feed['scored_as_of'], str(today))
C.add('feed top level', 'market_regime (gate today)', feed['market_regime'], 'Bullish' if W.gate(today) else 'Bearish')
C.add('feed top level', 'label says computed / entry quality only', label_ok(feed['label']), 'yes')
C.add('feed top level', 'cards_withheld / alerts_withheld / extras_withheld all false', yn(not (feed['cards_withheld'] or feed['alerts_withheld'] or feed['extras_withheld'])), 'yes')
print('per_year', float(per_year), len(T))
pickle.dump(C.rows, open(f'rows_{NAME}_4.pkl', 'wb'))

# ============================================================ 5. cards
C0 = C
PLAIN = {'GAP': 'CT well above its Signal line', 'HIGH': 'a higher low than the last signal', 'AGREE': 'other charts already confirmed',
         'BTC3': 'a BTC 3D signal in the 10 days before', 'BTCX': 'an ETH 2D signal in the 10 days before', 'FUND': 'funding at or above its 90-day median',
         'FCOOL': 'funding not cooling', 'UP8': 'the 8D chart rising', 'FASTCT': 'CT recovering fast from the low'}
RPLAIN = {v: k for k, v in PLAIN.items()}
gp = lambda g: 'the top grade' if g == 'A+' else 'the same grade'
gof = lambda n: 'C' if n <= 1 else 'B' if n == 2 else 'A' if n == 3 else 'A+'
def lset(r): return frozenset(x for x in r['lenses'].split(' + ') if x != '-')

def next_open(d, tfd): return bucket_span(d, tfd)[1] + dt.timedelta(days=1)
def forming_low(ch):
    ct, k, b = ch.ct, ch.k, ch.b; n = b.n
    for back in (1, 2, 3):
        ti = n - 1 - back
        if ti - 3 < 0 or any(ct[j] is None for j in range(ti - 3, n)): continue
        if any(ct[j] <= ct[ti] for j in range(ti - 3, ti)): continue
        if any(ct[j] <= ct[ti] for j in range(ti + 1, n)): continue
        need = 3 - back; co = b.date[-1]
        for _ in range(need): co = next_open(co, ch.tfd)
        d0 = bucket_span(co, ch.tfd)[1]
        prev = [p for p in ch.pivots if p['ti'] < ti]
        dis = False
        if prev and k[ti] is not None:
            dc = ct[ti] - prev[-1]['ct']; dk = k[ti] - prev[-1]['k']
            dis = (dc > EPS and dk < -EPS) or (dc < -EPS and dk > EPS)
        strong = dis and ct[ti] < 50; prime = k[ti] is not None and 20 <= k[ti] < 50; bk = bucket_of(ct[ti])
        kill = None
        if need in (0, 1):
            # the close X on the confirmation bar at which CT equals the trough's CT (CT rises with the close).
            # need 1: assumes today's still-open bar closes at the current price (definitional note d)
            base = ch.b.cf[:-1] if need == 0 else ch.b.cf[:]
            lo, hi = 0.0, ch.b.cf[-1] * 3
            pre = RsiState(base)
            for _ in range(200):
                mid = (lo + hi) / 2
                if pre.next(mid) <= ct[ti]: lo = mid
                else: hi = mid
            kill = rhu(Fr(Decimal(repr((lo + hi) / 2))), 2)
        return dict(a=ch.a, tf=ch.tf, chart=f'{ch.a} {ch.tf}', ti=ti, tdate=b.date[ti], need=need, d0=d0, bk=bk, dis=dis, strong=strong,
                    prime=prime, tags=tagstr(bk, dis, strong, prime), price=b.c[-1], kill=kill, gate=W.gate(b.date[ti]))
    return None
class RsiState:
    """Wilder averages after a closed history, so the RSI for one more close is a formula"""
    def __init__(self, c, n=14):
        ups = [max(c[i] - c[i - 1], 0.0) for i in range(1, len(c))]; dns = [max(c[i - 1] - c[i], 0.0) for i in range(1, len(c))]
        au = sum(ups[:n]) / n; ad = sum(dns[:n]) / n
        for i in range(n, len(ups)):
            au = (au * (n - 1) + ups[i]) / n; ad = (ad * (n - 1) + dns[i]) / n
        self.au, self.ad, self.last, self.n = au, ad, c[-1], n
    def next(self, x):
        n = self.n; u = max(x - self.last, 0.0); d = max(self.last - x, 0.0)
        au = (self.au * (n - 1) + u) / n; ad = (self.ad * (n - 1) + d) / n
        return 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)

def low_day(a, tf, tdate):
    lo, hi = bucket_span(tdate, int(tf[:-1])); D = W.day[a]
    cand = [(D.l[D.pos[d]], d) for d in (lo + dt.timedelta(days=i) for i in range((hi - lo).days + 1)) if d in D.pos and d >= tdate]
    return str(min(cand)[1])

def my_edge(fe_exact, lad_exact):
    if fe_exact != '' and fe_exact < 70: return 0
    for th, x in zip((5, 10, 15, 20), lad_exact):
        if x != '' and x < 70: return -th
    return ''

CARD_EDGE = {}; MYCARD = {}
def check_card(loc, c, kind, s, grade, lenses, L):
    a, tf = s['a'], s['tf']; chart = f'{a} {tf}'
    mv = MYCARD.setdefault(c['signal_id'] if kind != 'example' else 'example', {})
    class _R:
        def add(self, loc_, label, shown, mine, cause=''):
            mv[label] = mine; return C0.add(loc_, label, shown, mine, cause)
    C = _R()
    C.add(loc, 'label says computed / entry quality only', label_ok(c['label']), 'yes')
    C.add(loc, 'signal_id', c['signal_id'], f"{a}-{tf}-{s['d0']}")
    C.add(loc, 'chart', c['chart'], chart); C.add(loc, 'asset', c['asset'], a); C.add(loc, 'timeframe', c['timeframe'], tf)
    C.add(loc, 'low_date (trough bar date)', c['low_date'], str(s['tdate']))
    C.add(loc, 'low_day (day the low printed)', c['low_day'], low_day(a, tf, s['tdate']))
    C.add(loc, 'confirms_on (confirmation close date)', c['confirms_on'], str(s['d0']))
    if kind == 'forming':
        C.add(loc, 'bars_to_confirm', c['bars_to_confirm'], s['need'])
        C.add(loc, 'must_close_above', c['must_close_above'], s['kill'])
        C.add(loc, 'price_now (latest price)', c['price_now'], rhu(s['price'], 2))
        C.add(loc, 'entry_close (empty while forming)', c['entry_close'], None)
    else:
        C.add(loc, 'bars_to_confirm (empty)', c['bars_to_confirm'], None)
        C.add(loc, 'must_close_above (empty)', c['must_close_above'], None)
        C.add(loc, 'price_now', c['price_now'], None if kind == 'example' else rhu(W.day[a].c[-1], 2))
        C.add(loc, 'entry_close', c['entry_close'], rhu(s['entry'], 2))
    C.add(loc, 'grade (as given) matches the lens count', c['grade'], gof(len(lenses)))
    C.add(loc, 'grade equals the given grade', c['grade'], grade)
    C.add(loc, 'confirmations (plain words of the given lenses)', c['confirmations'], '; '.join(PLAIN[k] for k in lenses) or 'none')
    ex = [r for r in L if r['chart'] == chart and lset(r) == frozenset(lenses)]
    sg = [r for r in L if r['chart'] == chart and r['grade'] == grade]
    ag = [r for r in L if r['asset'] == a and r['grade'] == grade]
    tail = ' whose 60 days had closed by then' if kind == 'example' else ''
    if kind == 'example':
        if len(ex) >= 15: basis, G = f'all {len(ex)} {a} {tf} signals with exactly the same confirmations{tail}', ex
        elif len(sg) >= 15: basis, G = f'all {len(sg)} {a} {tf} signals of {gp(grade)}{tail} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
        else: basis, G = f'all {len(ag)} signals of {gp(grade)} across all {a} charts{tail} ({a} {tf} alone had only {len(sg)}, too few to use)', ag
    else:
        if len(ex) >= 15: basis, G = f'all {len(ex)} past {a} {tf} signals with exactly the same confirmations', ex
        elif len(sg) >= 15: basis, G = f'all {len(sg)} past {a} {tf} signals of {gp(grade)} (' + ('none' if not ex else f'only {len(ex)}') + ' had exactly the same confirmations, too few to use)', sg
        else: basis, G = f'all {len(ag)} past signals of {gp(grade)} across all {a} charts ({a} {tf} alone has only {len(sg)}, too few to use)', ag
    n = len(G); Gs = [SG(r) for r in G]
    C.add(loc, 'sample (rule and counts)', c['sample'], basis)
    C.add(loc, 'past_trades', c['past_trades'], n); C.add(loc, 'past_signals', c['past_signals'], n)
    sv = lambda X: share(X, lambda r: M(r)['r10'] and not M(r)['liq'])
    C.add(loc, 'rose10_within60d_pct', c['rose10_within60d_pct'], share(G, lambda r: M(r)['r10']))
    C.add(loc, 'rose10_never_fell25_within60d_pct', c['rose10_never_fell25_within60d_pct'], sv(G))
    scs = [x for x in (W.scaled20(x) for x in Gs) if x is not None]
    C.add(loc, 'beat_normal_move_pct', c['beat_normal_move_pct'], rhu(Fr(100 * sum(scs), len(scs))) if scs else '')
    C.add(loc, 'rose20_within60d_pct', c['rose20_within60d_pct'], share(G, lambda r: M(r)['r20']))
    C.add(loc, 'fell30_within60d_pct', c['fell30_within60d_pct'], share(G, lambda r: M(r)['t30']))
    for fld, key in (('typical_biggest_rise', 'up'), ('typical_dip_before_rise', 'ddpk'), ('typical_deepest_dip', 'dd')):
        med = median([M(r)[key] for r in G]); ex6 = rhu(med, 6)
        C.add(loc, f'{fld}_exact_pct (median, 6 places)', c[f'{fld}_exact_pct'], ex6)
        C.add(loc, f'{fld}_pct (1 place, rounded once from the exact value)', c[f'{fld}_pct'], rhu(ex6, 1))
        C.add(loc, f'{fld}_pct (1 place, rounded from full precision)', c[f'{fld}_pct'], rhu(med, 1))
    old = [r for r in G if r['entry'] < '2022-01-01']; new = [r for r in G if r['entry'] >= '2022-01-01']
    C.add(loc, 'before_2022 n', c['before_2022']['past_trades'], len(old)); C.add(loc, 'before_2022 n (signals twin)', c['before_2022']['past_signals'], len(old))
    C.add(loc, 'before_2022 rose10 never fell 25.3%', c['before_2022']['rose10_never_fell25_within60d_pct'], sv(old))
    C.add(loc, 'since_2022 n', c['since_2022']['past_trades'], len(new)); C.add(loc, 'since_2022 n (signals twin)', c['since_2022']['past_signals'], len(new))
    C.add(loc, 'since_2022 rose10 never fell 25.3%', c['since_2022']['rose10_never_fell25_within60d_pct'], sv(new))
    C.add(loc, 'eras add up to n', c['before_2022']['past_trades'] + c['since_2022']['past_trades'], n)
    med0 = lambda xs: rhu(median(xs)) if xs else ''
    C.add(loc, 'typical_day_first_rose10', c['typical_day_first_rose10'], med0([M(r)['t10'] for r in G if M(r)['t10'] is not None]))
    C.add(loc, 'typical_day_first_rose20', c['typical_day_first_rose20'], med0([M(r)['t20'] for r in G if M(r)['t20'] is not None]))
    C.add(loc, 'typical_day_of_60d_high', c['typical_day_of_60d_high'], med0([M(r)['dpk'] for r in G]))
    C.add(loc, 'typical_day_of_deepest_dip', c['typical_day_of_deepest_dip'], med0([M(r)['ddday'] for r in G]))
    ok, liq, nn = W.from_entry(Gs); fe = c['from_entry']
    C.add(loc, 'from_entry n', fe['past_trades'], nn); C.add(loc, 'from_entry n (signals twin)', fe['past_signals'], nn)
    C.add(loc, 'from_entry still_rose10_pct', fe['still_rose10_pct'], rhu(Fr(100 * ok, nn)) if nn else '')
    C.add(loc, 'from_entry went_on_to_fall25_pct', fe['went_on_to_fall25_pct'], rhu(Fr(100 * liq, nn)) if nn else '')
    fex = eshare(ok, nn); C.add(loc, 'from_entry still_rose10_exact_pct', fe['still_rose10_exact_pct'], fex)
    lex = []
    C.add(loc, 'ladder levels', ','.join(str(x['fell_pct']) for x in c['if_it_falls_first']), '5,10,15,20')
    for row in c['if_it_falls_first']:
        th = row['fell_pct']; hit, ok, liq = W.falls_first(Gs, th)
        C.add(loc, f'falls {th}% first: n', row['past_trades'], hit); C.add(loc, f'falls {th}% first: n (signals twin)', row['past_signals'], hit)
        C.add(loc, f'falls {th}% first: still_rose10_pct', row['still_rose10_pct'], rhu(Fr(100 * ok, hit)) if hit else '')
        C.add(loc, f'falls {th}% first: went_on_to_fall25_pct', row['went_on_to_fall25_pct'], rhu(Fr(100 * liq, hit)) if hit else '')
        x = eshare(ok, hit); lex.append(x)
        C.add(loc, f'falls {th}% first: still_rose10_exact_pct', row['still_rose10_exact_pct'], x)
    # the edge, on the FEED's exact shares and on mine (must agree)
    f_edge = my_edge('' if fe['still_rose10_exact_pct'] is None else Fr(Decimal(repr(fe['still_rose10_exact_pct']))),
                     ['' if r['still_rose10_exact_pct'] is None else Fr(Decimal(repr(r['still_rose10_exact_pct']))) for r in c['if_it_falls_first']])
    C.add(loc, 'edge level (first exact share under 70%), from the feed card vs mine', f_edge, my_edge(fex, lex))
    CARD_EDGE[c['signal_id'] if kind != 'example' else 'example'] = my_edge(fex, lex)
    mv.update(_kind=kind, _edge=my_edge(fex, lex), _entry=None if kind == 'forming' else s['entry'], _price=s.get('price'), _n=n, _basis=basis, _grade=grade, _a=a, _tf=tf, _d0=s['d0'], _tdate=s['tdate'], _need=s.get('need'), _kill=s.get('kill'),
              _med={k: rhu(median([M(r)[k] for r in G]), 6) for k in ('up', 'ddpk', 'dd')}, _medfull={k: median([M(r)[k] for r in G]) for k in ('up', 'ddpk', 'dd')})
    for ac in c.get('active_confluences', []):
        ca, ctf = ac['after'].split()[:2]
        ok_d = any(str(x['d0']) == ac['after_confirmed'] for x in W.sig[(ca, ctf)])
        C.add(loc, f"active confluence after {ac['after']}: its confirmer is one of my signals, 0-10 days before", yn(ok_d and 0 <= (s['d0'] - dt.date.fromisoformat(ac['after_confirmed'])).days <= 10), 'yes')
        C.add(loc, f"active confluence after {ac['after']}: window closes 10 days after", ac['window_closes'], str(dt.date.fromisoformat(ac['after_confirmed']) + dt.timedelta(days=10)))
        C.add(loc, f"active confluence after {ac['after']}: past_signals twin", ac['past_signals'], ac['past_trades'])
    return G

# forming cards
forming = {k: forming_low(ch) for k, ch in W.ch.items()}
forming = {k: v for k, v in forming.items() if v}
want_cards = sorted(f"{v['a']}-{v['tf']}-{v['d0']}" for v in forming.values() if v['tf'] in GRADED and v['gate'])
C.add('feed cards', 'forming cards exist exactly for my forming lows on graded charts with the gate on at the trough date',
      ' '.join(sorted(c['signal_id'] for c in feed['cards'])), ' '.join(want_cards))
for c in feed['cards']:
    f = forming.get((c['asset'], c['timeframe']))
    if not f: continue
    lenses = [] if c['confirmations'] == 'none' else [RPLAIN.get(x, x) for x in c['confirmations'].split('; ')]
    check_card(f"feed cards {c['signal_id']} (forming)", c, 'forming', f, c['grade'], lenses, led)
    C.add(f"feed cards {c['signal_id']} (forming)", 'gate on at the trough date', 'yes', yn(f['gate']))
    C.add(f"feed cards {c['signal_id']} (forming)", 'graded chart (1D-5D)', 'yes', yn(f['tf'] in GRADED))
# example card
exs = ALL.get(('ETH 2D', '2024-09-22')); xc = feed['example_card']
HAVE_EX = ('ETH 2D', '2024-09-22') in lk          # false only when replaying a date before the example's 60 days closed
if HAVE_EX:
    C.add('feed example_card', 'ETH 2D 2024-09-22 is one of my signals', 'yes', yn(exs is not None))
    exl = lk[('ETH 2D', '2024-09-22')]
    C.add('feed example_card', 'example flag', xc.get('example'), True)
    Gex = check_card('feed example_card', xc, 'example', exs, exl['grade'], [x for x in exl['lenses'].split(' + ') if x != '-'], known)
    C.add('feed example_card', 'every sample signal had its 60th day closed by 2024-09-22', yn(all(dt.date.fromisoformat(r['entry']) + D60 <= EXD for r in Gex)), 'yes')
else:
    C.add('feed example_card', 'absent before the example exists', xc, None)
print('5 cards (forming + example)', len(C.rows))

# ============================================================ 6. open signals
opens = sorted([s for k, v in W.sig.items() if k[1] in GRADED for s in v if 0 <= (today - s['d0']).days <= 60 and s['m'] is None], key=lambda s: (str(s['d0']), s['chart']))
fo = feed['open_signals']
C.add('feed open_signals', 'list (ids, in order)', ' '.join(o['signal_id'] for o in fo), ' '.join(f"{s['a']}-{s['tf']}-{s['d0']}" for s in opens))
om = {f"{s['a']}-{s['tf']}-{s['d0']}": s for s in opens}
MYOPEN = {}
for o in fo:
    s = om.get(o['signal_id']); loc = f"feed open_signals {o['signal_id']}"
    if s is None: continue
    a = s['a']; D = W.day[a]; e = s['entry']; d0 = s['d0']
    ks = W.window(a, d0)       # closed daily bars only
    pc = lambda x: (x / e - 1) * 100
    mark = lambda n: next((rhu(pc(D.c[k]), 1) for k in ks if (D.date[k] - d0).days == n), None)
    C.add(loc, 'label says computed / entry quality only', label_ok(o['label']), 'yes')
    C.add(loc, 'chart', o['chart'], s['chart']); C.add(loc, 'entry_date (confirmation close date)', o['entry_date'], str(d0))
    C.add(loc, 'entry_close', o['entry_close'], rhu(e, 2)); C.add(loc, 'tags', o['tags'], s['tags'])
    C.add(loc, 'days_elapsed (day in progress)', o['days_elapsed'], (today - d0).days)
    C.add(loc, 'day10_pct (closed bar only)', o['day10_pct'], mark(10)); C.add(loc, 'day30_pct (closed bar only)', o['day30_pct'], mark(30))
    C.add(loc, 'day60_pct (always empty)', o['day60_pct'], None)
    C.add(loc, 'best_so_far_pct', o['best_so_far_pct'], rhu(pc(max(D.h[k] for k in ks)), 1) if ks else None)
    C.add(loc, 'worst_so_far_pct', o['worst_so_far_pct'], rhu(pc(min(D.l[k] for k in ks)), 1) if ks else None)
    lenses = [x for x in o['confirmations'].split(' + ') if x != '-']
    C.add(loc, 'grade letter matches the lens count', o['grade'], gof(len(lenses)))
    if o['card'] is None:
        C.add(loc, 'has its own card', 'no', 'yes'); continue
    check_card(loc + ' card', o['card'], 'open', s, o['grade'], lenses, led)
    lvl = CARD_EDGE[o['signal_id']]
    C.add(loc, 'edge_level_pct', o['edge_level_pct'], None if lvl == '' else lvl)
    if lvl == 0: st = 'lost'
    elif lvl == '': st = 'intact'
    else:
        st = 'intact'
        for k in ks:
            if D.l[k] <= e * Fr(100 + lvl, 100): st = 'lost'; break
            if D.h[k] >= e * Fr(110, 100): st = 'intact'; break
    C.add(loc, 'edge_status', o['edge_status'], st)
    MYOPEN[o['signal_id']] = dict(chart=s['chart'], a=a, tf=s['tf'], d0=d0, entry=e, grade=o['grade'], elapsed=(today - d0).days, d10=mark(10), d30=mark(30),
        best=rhu(pc(max(D.h[k] for k in ks)), 1) if ks else None, worst=rhu(pc(min(D.l[k] for k in ks)), 1) if ks else None, edge=None if lvl == '' else lvl, status=st)
print('6 open signals', len(C.rows))

# prints
exp = []
for a in ASSETS:
    for tf in TFS:
        for s in W.sig[(a, tf)][-3:]:
            exp.append(dict(signal_id=f"{a}-{tf}-{s['d0']}", chart=f'{a} {tf}', state='confirmed', provisional=False, low_date=str(s['tdate']),
                            confirms_on=str(s['d0']), entry_close=rhu(s['entry'], 2), tags=s['tags'], note='regime on' if W.gate(s['tdate']) else 'regime off'))
        f = forming.get((a, tf))
        if f:
            exp.append(dict(signal_id=f"{a}-{tf}-{f['d0']}", chart=f'{a} {tf}', state='forming', provisional=True, low_date=str(f['tdate']),
                            confirms_on=str(f['d0']), entry_close=rhu(f['price'], 2), tags=f['tags'],
                            note=('regime on' if f['gate'] else 'regime off') + f"; {f['need']} bar(s) to confirm"))
fp = feed['prints']
C.add('feed prints', 'list (ids and states, in order)', ' '.join(f"{p['signal_id']}:{p['state']}" for p in fp), ' '.join(f"{p['signal_id']}:{p['state']}" for p in exp))
em = {(p['signal_id'], p['state']): p for p in exp}
for p in fp:
    x = em.get((p['signal_id'], p['state'])); loc = f"feed prints {p['signal_id']} ({p['state']})"
    if x is None: continue
    C.add(loc, 'label says computed / entry quality only', label_ok(p['label']), 'yes')
    for k in ('chart', 'provisional', 'low_date', 'confirms_on', 'entry_close', 'tags', 'note'):
        C.add(loc, k, p[k], x[k])
# next_buy_date (status.csv, refresh.ds_buy): the earliest confirmation-bar OPEN date among forming ETH lows that carry
# a tier tag (the forming low's bucket / any trough / prime dot / zone-exit B; refresh does not tag a forming diamond)
nb = []
for tf in TFS:
    f = forming.get(('ETH', tf))
    if not f: continue
    ch = W.ch[('ETH', tf)]; zm = zmin_series(ch.ct); ti = f['ti']
    tg = {f['bk'], 'any trough'} | ({'prime dot'} if f['prime'] else set()) | ({'zone-exit B'} if f['bk'] == 'B' and ch.ct[ti] < 60 and zm[ti] is not None and zm[ti] >= 50 else set())
    if not any(k[0] == tf and k[1] in tg for k in keep): continue
    # a kept setup needs at least 4 scored past signals to have stats (refresh.ds_setups); every tier pair has 8+
    conf_open = bucket_span(f['d0'], ch.tfd)[0]
    if conf_open > today: nb.append(str(conf_open))
C.add('feed top level', 'next_buy_date (tier dashboard: earliest forming ETH low carrying a tier tag, by its confirmation bar open date)', feed['next_buy_date'], min(nb) if nb else 'none ahead')
# confluence windows: dates only (the cells themselves are lens logic)
for w in feed['confluence_windows']:
    if 'DIVH' in w['applies_to']: continue
    a_, tf_ = w['opened_by'].split()
    okw = any(str(x['d0']) == w['confirmed'] for x in W.sig[(a_, tf_)]) and 0 <= (today - dt.date.fromisoformat(w['confirmed'])).days <= 10
    C.add(f"feed confluence_windows {w['opened_by']} {w['confirmed']}", f"opened by one of my signals in the last 10 days; closes 10 days after ({w['applies_to'][:50]})",
          w['closes'] if okw else 'not my signal', str(dt.date.fromisoformat(w['confirmed']) + dt.timedelta(days=10)))
print('6 prints', len(C.rows))

# ============================================================ 7. past paths
def quant(v, f):
    s = sorted(v); k = Fr(len(s) - 1) * f; lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)
def path_check(loc, pp, G):
    C.add(loc, 'signals (n)', pp['signals'], len(G)); C.add(loc, 'grade', pp['grade'], 'A+')
    C.add(loc, 'label says computed / entry quality only', label_ok(pp['label']), 'yes')
    C.add(loc, 'days listed', len(pp['days']), 61)
    P = []
    for r in G:
        s = SG(r); D = W.day[s['a']]; ks = s['m']['ks']
        assert [(D.date[k] - s['d0']).days for k in ks] == list(range(1, 61))
        P.append([Fr(0)] + [(D.c[k] / s['entry'] - 1) * 100 for k in ks])
    for d in pp['days']:
        k = d['day']; col = [p[k] for p in P]
        C.add(loc, f'day {k} q25_pct', d['q25_pct'], rhu(quant(col, Fr(1, 4)), 1))
        C.add(loc, f'day {k} median_pct', d['median_pct'], rhu(quant(col, Fr(1, 2)), 1))
        C.add(loc, f'day {k} q75_pct', d['q75_pct'], rhu(quant(col, Fr(3, 4)), 1))
C.add('feed past_paths', 'assets', ' '.join(p['asset'] for p in feed['past_paths']), 'ETH BTC')
for pp in feed['past_paths']:
    path_check(f"feed past_paths {pp['asset']}", pp, G_by[(pp['asset'], 'A+')])
if feed['example_past_paths']:
    path_check('feed example_past_paths', feed['example_past_paths'], ex_ap)
    C.add('feed example_past_paths', 'asset', feed['example_past_paths']['asset'], 'ETH')
print('7 paths', len(C.rows))

bad = [x for x in C.rows if x[5] == 'NO']
print('TOTAL', len(C.rows), 'disagreements', len(bad))
for x in bad: print('  ', x[1:])
csv.writer(open(f'checks_data_{NAME}.csv', 'w', newline='')).writerows(C.rows)
# hand my values to the page audit
def gstat(G):
    return dict(n=len(G), r10=share(G, lambda r: M(r)['r10']), surv=share(G, lambda r: M(r)['r10'] and not M(r)['liq']), r20=share(G, lambda r: M(r)['r20']),
                meddip=rhu(median([M(r)['dd'] for r in G]), 1))
def my_paths(G):
    P = []
    for r in G:
        s = SG(r); D = W.day[s['a']]
        P.append([Fr(0)] + [(D.c[k] / s['entry'] - 1) * 100 for k in s['m']['ks']])
    return dict(n=len(G), days=[dict(q25=rhu(quant([p[k] for p in P], Fr(1, 4)), 1), med=rhu(quant([p[k] for p in P], Fr(1, 2)), 1), q75=rhu(quant([p[k] for p in P], Fr(3, 4)), 1)) for k in range(61)])
aplus = []
for r in led:
    if r['grade'] != 'A+': continue
    s = SG(r); m = s['m']
    aplus.append(dict(asset=s['a'], chart=s['chart'], entry=str(s['d0']), price=rhu(s['entry'], 2), r10=m['r10'], r20=m['r20'], best=rhu(m['up'], 6), dd=rhu(m['dd'], 6),
                      ret=rhu(m['ret'], 6), dpk=m['dpk']))
exm = ALL.get(('ETH 2D', '2024-09-22')) if HAVE_EX else None
pickle.dump(dict(cards=MYCARD, opens=MYOPEN, open_order=[f"{s['a']}-{s['tf']}-{s['d0']}" for s in opens],
                 forming={f"{v['a']}-{v['tf']}-{v['d0']}": v for v in forming.values()},
                 misses={k: miss_stats(G) for k, G in G_by.items()}, ex_misses=miss_stats(ex_ap) if ex_ap else None,
                 gstat={k: gstat(G) for k, G in G_by.items()}, paths={a: my_paths(G_by[(a, 'A+')]) for a in ASSETS}, ex_paths=my_paths(ex_ap) if ex_ap else None,
                 aplus=aplus, today=today, gate_today=W.gate(today), last_closed=max(d for d in W.day['ETH'].date if d < today),
                 example=dict(entry=exm['entry'], d0=exm['d0'], m={k: v for k, v in exm['m'].items() if k != 'ks'}, tdate=exm['tdate']) if exm else None,
                 lowday={k: low_day(v['a'], v['tf'], v['tdate']) for k, v in forming.items()}),
            open(f'mine_{NAME}.pkl', 'wb'))
