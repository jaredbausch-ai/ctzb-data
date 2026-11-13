"""synthetic: a live signal whose card is missing from the feed (the page then builds figures itself)"""
import copy, json, sys, os, datetime as dt
sys.path.insert(0, '.')
import pagelib as PL
from playwright.sync_api import sync_playwright
CU = os.path.abspath('../a19/current'); feed = json.load(open(CU + '/feed/ctzb_feed.json'))
f = copy.deepcopy(feed); o = next(x for x in f['open_signals'] if x['signal_id'] == 'BTC-2D-2026-09-21'); o['card'] = None
at = (dt.datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00')) + dt.timedelta(minutes=6)).isoformat()
with sync_playwright() as pw:
    br = pw.chromium.launch(); page = PL.Site(CU, {'data/ctzb_feed.json': f}).open(br, at); n = page.evaluate(PL.JS_NOW)['card']
    print(n['state'], '|', n['smalls']); print(n['odds']); print(n['kv'], n['pool']); print(n['tiles']); print(n['ladderLbl'], [(x['label'], x['val'], x['gone']) for x in n['ladder']]); print(n['ladderNote'][:200]); print(n['eras'])
    br.close()
# ---- recorded as checks ----
import csv
import audit_data as AD
from pagelib import pct, pc
from lib import rha, med
R, info = AD.run(CU, feed['generated_at'], 'CURRENT')
G = info['byg'][('BTC', 'A+')]; nG = len(G); sh = lambda k: f"{rha(__import__('fractions').Fraction(100 * k, nG), 0)}%"
rows = []; L = 'synthetic: live signal whose card is missing from the feed'
def add(label, shown, mine, ok): rows.append(('SYNTH', L, label, str(shown)[:300], str(mine)[:300], 'ok' if ok else 'DISAGREE', '' if ok else 'page falls back to figures it computes itself'))
add('status line agrees with the feed (edge_status lost)', n['smalls'][1], 'Edge lost ...', n['smalls'][1].startswith('Edge lost'))
add("edge shown is this setup's own (or none)", n['kv'][2][1], "none: no card; the page shows the ETH pooled table's edge on a BTC signal", False)
add("ladder is this setup's own (or none)", n['ladderLbl'][0], 'no ladder without the card', 'eth tier' not in n['ladderLbl'][0].lower())
add('big number = share of BTC top-grade signals that rose 10%', n['odds'][0], sh(sum(m['r10'] for s, m in G)), n['odds'][0] == sh(sum(m['r10'] for s, m in G)))
add('typical high = median best move', n['kv'][0][1], pct(rha(med([m['up'] for s, m in G]), 6)), n['kv'][0][1] == pct(rha(med([m['up'] for s, m in G]), 6)))
add('typical drop = median deepest dip', n['kv'][1][1], pct(rha(med([m['dd'] for s, m in G]), 6)), n['kv'][1][1] == pct(rha(med([m['dd'] for s, m in G]), 6)))
add('typical change by day 60 (all signals) = median day-60 change', n['tiles'][7][1], pct(rha(med([m['ret'] for s, m in G]), 6)), n['tiles'][7][1] == pct(rha(med([m['ret'] for s, m in G]), 6)))
add('reached +20%', n['tiles'][2][1], sh(sum(m['r20'] for s, m in G)), n['tiles'][2][1] == sh(sum(m['r20'] for s, m in G)))
add('touched -30%', n['tiles'][3][1], sh(sum(m['t30'] for s, m in G)), n['tiles'][3][1] == sh(sum(m['t30'] for s, m in G)))
csv.writer(open('out_synth2.csv', 'w', newline='')).writerows([['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']] + rows)
print('synth2 rows', len(rows), 'defects', sum(r[5] != 'ok' for r in rows))
