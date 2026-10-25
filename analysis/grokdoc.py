"""Turn analysis/grokpack.json into the document and CSV for Joe's AI.

Output-level names only: nothing here describes how a tag is computed.
  python3 -I analysis/grokdoc.py
    -> docs/joe/grokpack/ETHKROS_signal_capabilities.md
    -> docs/joe/grokpack/ETHKROS_signal_capabilities.csv
"""
import json, csv, os

J = json.load(open('analysis/grokpack.json'))
OUT = 'docs/joe/grokpack'
os.makedirs(OUT, exist_ok=True)

NAME = {  # internal name -> name the reader sees
    'A': 'bucket A', 'B': 'bucket B', 'C': 'bucket C', 'D': 'bucket D', 'all': 'any signal', 'any': 'any signal',
    'diamond': 'diamond', 'filled diamond': 'filled diamond', 'hollow diamond': 'hollow diamond',
    'A+diamond': 'bucket A + diamond', 'B+diamond': 'bucket B + diamond', 'prime': 'prime dot',
    'prime+diamond': 'prime dot + diamond',
    'CT>Signal by 5+': 'momentum well above its signal line', 'CT>Signal + prime': 'momentum above its signal line + prime dot',
    'CT>Signal + diamond': 'momentum above its signal line + diamond', 'higher entry': 'higher low',
    '2+ own charts before': 'same-asset agreement', '8D rising': 'higher timeframe rising',
    '8D rising + higher entry': 'higher timeframe rising + higher low',
    '8D rising + CT>Signal': 'higher timeframe rising + momentum above its signal line',
    '8D rising + prime': 'higher timeframe rising + prime dot',
    '8D rising + diamond': 'higher timeframe rising + diamond',
}
pooled = lambda g: g.replace('pooled', '(all charts)')


def p(x):
    return '–' if x[0] is None else f'{x[0]:.0f}% ({x[1]})'


def both_ok(r, lo=60):
    a, b = r['16-21'], r['22-26']
    return a[0] is not None and b[0] is not None and a[1] >= 5 and b[1] >= 5 and a[0] >= lo and b[0] >= lo


L = []
w = L.append
w('# ETHKROS signal capabilities')
w('')
w('Prepared 24 Oct 2026 by Jared Bausch for Mauro Group\'s AI. Every figure was recomputed on 24 Oct from the full price history with the rules below. Earlier figures in emails and in the October odds pages are superseded by this document.')
w('')
w('## How to read every number here')
w('')
w('- **Entry quality only.** These are historical results of computed signals. No position has been taken on any of them, and there is no exit in the data, so nothing here is a return, a track record, or a member win rate. Live results will come from Jared\'s own logged trades.')
w('- **Win** = price traded at least **+20% above the entry** at some point in the **60 days** after entry (daily highs). Entry is the close of the bar where the signal confirms, which is when the alert fires. Nothing is counted before it was visible.')
w('- **Regime on.** A Bitcoin-driven filter switches signals on and off. Every figure is measured with it on.')
w('- **Two periods, always.** 2016–21 and 2022–26 are shown separately. 2022–26 rates are lower mainly because the market moves less (ETH\'s daily volatility fell from 5.7% to 3.6%), so a fixed +20% is a higher bar.')
w('- **Drawdown** = the worst dip below entry before the 60-day high (median). **Touched −30%** = share that dipped 30% or more below entry within 60 days.')
w('- **n** = number of past signals. Under about 20 is a small sample. Many setups were tested, so some high figures will not repeat.')
w('')
w('## 1. Base signal by chart')
w('')
w('| Chart | Win | 2016–21 | 2022–26 | Drawdown | Touched −30% | n |')
w('|---|---|---|---|---|---|---|')
for r in J['layer1']:
    w(f"| {r['chart']} | {r['win']:.0f}% | {p(r['16-21'])} | {p(r['22-26'])} | {r['ddpk']:.1f}% | {r['t30']:.0f}% | {r['n']} |")
w('')
w('## 2. Best tagged and filtered setups')
w('')
w('Tags place a signal in a group; filters are conditions at the moment of entry. Shown: 75%+ win, 60%+ in both periods, 15+ signals. Lift = points above the same chart without the setup.')
w('')
w('| Chart | Setup | Win | 2016–21 | 2022–26 | Lift | Drawdown | Touched −30% | n |')
w('|---|---|---|---|---|---|---|---|---|')
rows = [(r['chart'], r['tag'], r) for r in J['layer2']] + [(r['group'], r['filter'], r) for r in J['layer3']]
for g, name, r in sorted(rows, key=lambda x: (-x[2]['win'], -x[2]['n'])):
    if r['n'] >= 15 and r['win'] >= 75 and both_ok(r):
        w(f"| {pooled(g)} | {NAME[name]} | {r['win']:.0f}% | {p(r['16-21'])} | {p(r['22-26'])} | {r['lift']:+d} | {r['ddpk']:.1f}% | {r['t30']:.0f}% | {r['n']} |")
w('')
w('## 3. Confluence: another chart already signalled')
w('')
w(f"The confirming chart must have confirmed its own signal in the 10 days **before** this entry, so it is knowable when the alert fires. {J['layer4_cells_tested']} combinations were tested. Shown: those with 15+ signals, a 10+ point lift, and a lift in both periods, ranked by win. \"Without\" = the same signal with no such confirmation. \"Years ahead\" = years in which the setup beat its \"without\" group.")
w('')
w('| Signal | Already confirmed before it | Win | Without | 2016–21 | 2022–26 | Years ahead | Drawdown | n |')
w('|---|---|---|---|---|---|---|---|---|')
for c in J['layer4']:
    if c['win'] < 70:
        continue
    w(f"| {c['trade']} {NAME[c['tag']]} | {c['confirm']} {NAME[c['ctag']]} | {c['win']:.0f}% | {c['without']}% | {p(c['16-21'])} | {p(c['22-26'])} | {c['years_ahead']} | {c['ddpk']:.1f}% | {c['n']} |")
w('')
w('### Small-sample highs')
w('')
w('8 to 14 past signals, 75%+ win, 15+ point lift. Strong on the record so far but too few cases to rely on.')
w('')
w('| Signal | Already confirmed before it | Win | Without | Drawdown | n |')
w('|---|---|---|---|---|---|')
for c in J['layer4_small']:
    if c['win'] < 85:
        continue
    w(f"| {c['trade']} {NAME[c['tag']]} | {c['confirm']} {NAME[c['ctag']]} | {c['win']:.0f}% | {c['without']}% | {c['ddpk']:.1f}% | {c['n']} |")
w('')
w('## 4. How the odds change as a trade matures')
w('')
w('After entry, a few observable reads sharpen the picture. Measured on trades that had not already reached +20% by the check day. These are information for Jared\'s exit decisions and for members holding a position; they are not entry rules (waiting for them costs part of the move).')
w('')
w('| Read | Asset | Win if yes | Win if no | Touched −30%, yes / no |')
w('|---|---|---|---|---|')
RN = {'CT above Signal on day 10': 'momentum above its signal line on day 10',
      'undercut trough low by day 10': 'price broke the signal bar\'s low by day 10'}
for r in J['layer5']:
    w(f"| {RN.get(r['read'], r['read'])} | {r['asset']} | {r['yes']['win']:.0f}% | {r['no']['win']:.0f}% | {r['yes']['t30']:.0f}% / {r['no']['t30']:.0f}% |")
w('')
w('## 5. What each live alert can carry')
w('')
w('- Chart, tags, entry price and time.')
w('- The matching rows above: win rate, both periods, drawdown, touch rates, n.')
w('- Which other charts or the other asset already confirmed in the previous 10 days.')
w('- Whether the higher timeframe is rising, and whether the regime is on.')
w('- After entry: the day-5 and day-10 reads in section 4.')
w('- Jared\'s own buy and sell calls, with his leverage, by membership tier. Members choose their own leverage; the leverage tool shows where their liquidation would sit against the drawdowns above.')
w('')
w('## 6. Superseded figures')
w('')
w('- The evidence slide in the ETHKROS package (prime dot 70%→64%, diamond 68%→60%, untagged 58%→44%, "12 in a row") predates this recomputation. Use sections 1–3 instead.')
w('- The October odds pages counted "win" as closing above entry on day 60, and counted a confirming chart that signalled up to 10 days **after** the entry. Recomputed with only confirmations visible at entry, most of their confluence rows fall below 8 cases; 8 of 44 keep a 10+ point lift. Some rows score higher than before even on the stricter +20% test, for example ETH 3D diamond after a BTC 2D bucket B signal, 86% (7 cases).')
w('')
w('The attached CSV holds every row behind these tables (all tags, filters and confluence combinations that met the minimum sample), with the same columns.')
open(f'{OUT}/ETHKROS_signal_capabilities.md', 'w').write('\n'.join(L) + '\n')

with open(f'{OUT}/ETHKROS_signal_capabilities.csv', 'w', newline='') as f:
    cw = csv.writer(f)
    cw.writerow(['section', 'chart', 'setup', 'confirmed_before_by', 'win_pct', 'win_2016_21_pct', 'n_2016_21',
                 'win_2022_26_pct', 'n_2022_26', 'without_pct', 'lift_pts', 'years_ahead', 'drawdown_before_high_median_pct',
                 'touched_minus20_pct', 'touched_minus30_pct', 'closed_green_day60_pct', 'n', 'evidence'])
    def row(sec, ch, setup, conf, r, without=None, lift=None, ya=None, ev=''):
        a, b = r['16-21'], r['22-26']
        cw.writerow([sec, ch, setup, conf, round(r['win']), None if a[0] is None else round(a[0]), a[1],
                     None if b[0] is None else round(b[0]), b[1], without, lift, ya, round(r['ddpk'], 1),
                     round(r['t20']), round(r['t30']), round(r['green']), r['n'], ev])
    ev = lambda r: 'small sample' if r['n'] < 20 else ('both periods 60%+' if both_ok(r) else '')
    for r in J['layer1']:
        row('base', r['chart'], 'any signal', '', r, ev=ev(r))
    for r in J['layer2']:
        row('tag', r['chart'], NAME[r['tag']], '', r, lift=r['lift'], ev=ev(r))
    for r in J['layer3']:
        row('filter', pooled(r['group']), NAME[r['filter']], '', r, without=r['without'], lift=r['lift'], ya=r['years_ahead'], ev=ev(r))
    for c in J['layer4']:
        row('confluence', c['trade'], NAME[c['tag']], f"{c['confirm']} {NAME[c['ctag']]}", c, without=c['without'], lift=c['lift'],
            ya=c['years_ahead'], ev='passed confluence checks' + ('; small sample' if c['n'] < 20 else ''))
    for c in J['layer4_small']:
        row('confluence', c['trade'], NAME[c['tag']], f"{c['confirm']} {NAME[c['ctag']]}", c, without=c['without'], lift=c['lift'],
            ya=c['years_ahead'], ev='small sample (8-14)')
print('written')
