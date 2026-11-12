"""Check 8 (labels vs meaning) figures, check 4 against the documented definition, check 10 open_signals,
and definitional counts."""
import pickle, json, statistics as st
from mine import *
from checks import rec, dump, ROWS

M = '−'
NOTES = {}
for state in ('REPLAY', 'CURRENT'):
    root = STATES[state]; now = NOWS[state]
    feed = json.load(open(f'{root}/feed/ctzb_feed.json'))
    U = pickle.load(open(f'{S}/audit3/universe_{state}.pkl', 'rb'))
    Lg = pickle.load(open(f'{S}/audit3/ledger_{state}.pkl', 'rb'))
    led = list(csv.DictReader(open(f'{root}/datasets/ledger.csv')))
    mine = Lg['mine_led']
    fade = pickle.load(open(f'{S}/audit3/fade.pkl', 'rb'))[state]
    # ---- 4 vs the documented definition: "+10% share counts highs from day 10 to day 60"
    R = fade['variants'][('R', False, True)]
    for x in R[1]:
        f = [y for y in feed['odds_fade']['day10'] if y['check'] == x['check']][0]
        rec(state, '4', f"feed odds_fade day10 {x['check']}", 'rose10_within60d_pct vs feed sample text (highs from day 10 to day 60)',
            f['rose10_within60d_pct'], round(x['r10_after10'], 2), f['rose10_within60d_pct'] == rhaz(x['r10_after10']),
            'holdcheck counts highs from day 1; the feed sample text says day 10 to day 60')
        edge = 'intact' if rhaz(x['r10_after10']) >= 70 else 'gone'
        rec(state, '4', f"feed odds_fade day10 {x['check']}", 'edge vs documented definition', f['edge'], edge, f['edge'] == edge, 'edge')
    D = fade['variants'][('D',)]
    for kind, rows, key in (('early_dip', D[0], 'band'), ('day10', D[1], 'check')):
        for x in rows:
            f = [y for y in feed['odds_fade'][kind] if y[key] == x[key]][0]
            for lab, kk in (('past_trades', 'n'), ('rose10_within60d_pct', 'r10'), ('rose20_within60d_pct', 'r20')):
                v = x[kk]; ok = f[lab] == (v if kk == 'n' else rhaz(v))
                rec(state, '4', f'feed odds_fade {kind} {x[key]} (stated clock: daily candles from the entry date)', lab, f[lab], v if kk == 'n' else round(v, 2), ok,
                    'odds_fade is measured on chart bars counted from the confirmation bar OPEN date, not daily candles from the entry close' + (' and day-10 +10% counts from day 1' if kind == 'day10' else ''))
    # ---- 8a: "never fell 25%" labels vs the 25.3% line
    def surv(G, line):
        return 100 * sum(s['m']['r10'] and s['m']['dd'] > -line for s in G) / len(G)
    shown = []
    for a in ('ETH', 'BTC'):
        G = [mine[(r['chart'], r['entry'])] for r in led if r['asset'] == a and r['grade'] == 'A+']
        shown.append((f'A+ {a} (Record summary / example card)', G))
        if a == 'ETH':
            shown.append(('A+ ETH before 2022 (example era)', [s for s in G if s['d0'].year < 2022]))
            shown.append(('A+ ETH since 2022 (example era)', [s for s in G if s['d0'].year >= 2022]))
    if state == 'REPLAY':
        part5 = list(csv.DictReader(open(f'{S}/audit3/part5.csv')))
        for c in feed['cards']:
            chart_rows = [r for r in led if r['chart'] == c['chart']]
            # sample = the rows c5 matched: rebuild from the card text
            if 'exactly the same' in c['sample']:
                lens = {'funding at or above its 90-day median': 'FUND', 'an ETH 2D signal in the 10 days before': 'BTCX', 'none': '-'}[c['confirmations']]
                G_ = [r for r in chart_rows if r['lenses'] == lens]
            else:
                G_ = [r for r in chart_rows if r['grade'] == c['grade']]
            G = [mine[(r['chart'], r['entry'])] for r in G_]
            shown.append((f"card {c['signal_id']}", G))
            shown.append((f"card {c['signal_id']} before 2022", [s for s in G if s['d0'].year < 2022]))
            shown.append((f"card {c['signal_id']} since 2022", [s for s in G if s['d0'].year >= 2022]))
    for lab, G in shown:
        v253, v25 = surv(G, 25.3), surv(G, 25.0)
        k = sum(1 for s in G if s['m']['r10'] and -25.3 < s['m']['dd'] <= -25.0)
        rec(state, '8', lab, '"did it without ever falling 25%" (line actually used: 25.3%)', f'{rhaz(v253)}%', f'{rhaz(v25)}% at a 25% line',
            rhaz(v253) == rhaz(v25), f'{k} signal(s) fell between 25% and 25.3% and are counted as never falling 25%')
    # ---- 8d: ladder "still rose 10% after first falling that far" vs code (+10% before -25.3%)
    if state == 'REPLAY':
        day = Daily(U['day']['ETH']); dayb = Daily(U['day']['BTC'])
        for c in feed['cards']:
            chart_rows = [r for r in led if r['chart'] == c['chart']]
            if 'exactly the same' in c['sample']:
                lens = {'funding at or above its 90-day median': 'FUND', 'an ETH 2D signal in the 10 days before': 'BTCX', 'none': '-'}[c['confirmations']]
                G_ = [r for r in chart_rows if r['lenses'] == lens]
            else:
                G_ = [r for r in chart_rows if r['grade'] == c['grade']]
            G = [mine[(r['chart'], r['entry'])] for r in G_]
            dd_ = day if c['asset'] == 'ETH' else dayb
            for row in c['if_it_falls_first']:
                th = row['fell_pct']; hit = rose = 0
                for s in G:
                    e = s['entry']; w = [dd_.b[dd_.pos[s['d0'] + dt.timedelta(days=k)]] for k in range(1, 61)]
                    first = None
                    for j, b in enumerate(w):
                        if b['h'] >= e * 1.1: break
                        if b['l'] <= e * (1 - th / 100): first = j; break
                    if first is None: continue
                    hit += 1; rose += any(b['h'] >= e * 1.1 for b in w[first:])
                v = 100 * rose / hit if hit else None
                rec(state, '8', f"card {c['signal_id']} falls {th}% first", 'page: "still rose 10% after first falling that far"',
                    row['still_rose10_pct'], None if v is None else round(v, 2), v is None or row['still_rose10_pct'] == rhaz(v),
                    'shown share excludes signals that rose 10% only after falling 25.3%; the page text does not say so')
    # ---- check 10: open_signals (feed; none is A+, so none is on the page)
    for o in feed['open_signals']:
        a, tf = o['chart'].split()
        sig = [s for s in U['sig'][(a, tf)] if s['gated'] and s['d0'] is not None and (str(s['cdate']) == o['entry_date'] or str(s['d0']) == o['entry_date'])]
        loc = f"feed open_signals {o['signal_id']}"
        if not sig:
            rec(state, '10', loc, 'signal exists', 'present', 'not found', False, 'no such gated signal'); continue
        s = sig[0]; e = s['entry']; d0 = s['d0']
        rec(state, '10', loc, 'entry_date = confirmation (entry close) date', o['entry_date'], str(d0), o['entry_date'] == str(d0),
            'open signals are dated by the confirmation bar OPEN date (forward.csv), not the entry-close date used by the ledger, prints and cards')
        sid = f'{a}-{tf}-{d0}'
        rec(state, '10', loc, 'signal_id (same as its print / card id)', o['signal_id'], sid, o['signal_id'] == sid,
            'id built from the bar open date; the print of the same signal carries the close date')
        rec(state, '10', loc, 'entry_close', o['entry_close'], e, abs(o['entry_close'] - round(e, 2)) < 1e-9, 'differs')
        days = (now.date() - d0).days
        rec(state, '10', loc, 'days_elapsed (days since the entry close, UTC)', o['days_elapsed'], days, o['days_elapsed'] == days,
            'counted between chart bar open dates (lags the calendar on multi-day charts)')
        db = Daily(U['day'][a])
        cl = [db.b[db.pos[d]] for d in sorted(db.pos) if d0 < d]
        closed = [b for b in cl if dt.datetime.combine(b['d'] + dt.timedelta(days=1), dt.time(), dt.timezone.utc) <= now]
        for mk in (10, 30):
            bb = [b for b in closed if (b['d'] - d0).days == mk]
            v = (bb[0]['c'] / e - 1) * 100 if bb else None
            shown = o[f'day{mk}_pct']
            ok = (shown is None and v is None) or (shown is not None and v is not None and abs(shown - rhaz(v, 1)) < 1e-9)
            cause = 'differs'
            if not ok:
                fb = [b for b in cl if (b['d'] - d0).days == mk]
                if fb and shown is not None and abs(shown - rhaz((fb[0]['c'] / e - 1) * 100, 1)) < 1e-9 and not bb: cause = 'day-10 figure taken from a daily bar that had not closed'
                elif shown is not None and v is not None: cause = 'mark taken from chart bars counted from the bar open date, not the daily close on that day'
            rec(state, '10', loc, f'day{mk}_pct', shown, None if v is None else round(v, 3), ok, cause)
        upto = [b for b in cl if (b['d'] - d0).days <= 60]
        best = (max(b['h'] for b in upto) / e - 1) * 100; worst = (min(b['l'] for b in upto) / e - 1) * 100
        for lab, v in (('best_so_far_pct', best), ('worst_so_far_pct', worst)):
            rec(state, '10', loc, lab, o[lab], round(v, 3), abs(o[lab] - rhaz(v, 1)) < 1e-9, 'differs')
    # ---- definitional counts
    elig = [s for s in mine.values()]
    allg = [s for (a, tf), v in U['sig'].items() if tf != '8D' for s in v if s.get('d0') and s.get('m') and (s['funded'])]
    NOTES[state] = dict(
        gate_trough_vs_conf=sum(1 for s in allg if s['gated'] != s['gated_conf']),
        gate_conf_would_add=sum(1 for s in allg if s['gated_conf'] and not s['gated']),
        gate_conf_would_drop=sum(1 for s in allg if s['gated'] and not s['gated_conf']),
        liq_band=sum(1 for s in elig if -25.3 < s['m']['dd'] <= -25.0),
    )
    # diamond variants on ledger rows
    var = {'gated chain': 0, 'price low vs K': 0, 'no EPS guard': 0}
    for (a, tf), sig in U['sig'].items():
        if tf == '8D': continue
        prevg = None
        for s in sig:
            if s['prev'] is not None:
                raw = (s['dct'] > 0 and s['dk'] < 0) or (s['dct'] < 0 and s['dk'] > 0)
                if (s['chart'], str(s['d0'])) in mine and raw != s['dis']: var['no EPS guard'] += 1
            if s['gated']:
                if (s['chart'], str(s['d0'])) in mine:
                    if prevg is not None:
                        dct = s['ct'] - prevg['ct']; dk = s['k'] - prevg['k']
                        dg = (dct > EPS and dk < -EPS) or (dct < -EPS and dk > EPS)
                        dp_ = s['tlow'] - prevg['tlow']
                        dpr = (dp_ > 0 and dk < -EPS) or (dp_ < 0 and dk > EPS)
                    else:
                        dg = dpr = False
                    var['gated chain'] += dg != s['dis']; var['price low vs K'] += dpr != s['dis']
                prevg = s
    NOTES[state]['diamond'] = var
    NOTES[state]['exact_half_cases'] = None
dump('part8.csv')
json.dump(NOTES, open(f'{S}/audit3/notes.json', 'w'), indent=1, default=str)
print(json.dumps(NOTES, indent=1, default=str))
for r in ROWS:
    if r['ok'] == 'no': print(r)
print(len(ROWS))
