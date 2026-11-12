"""Audit 15 -- page wording in states the frozen feeds do not contain, by altering ONE live card in a copy of the
feed (page test only; the altered numbers are mine, to see what the page prints for them)."""
import sys, csv, json, copy
from harness import Site, norm_ws
from core import Checks
S, NAME = sys.argv[1], sys.argv[2]; C = Checks(NAME + ' (synthetic)')
base = json.load(open(f'{S}/feed/ctzb_feed.json'))
def run(tag, mut, expect):
    feed = copy.deepcopy(base); o = next(x for x in feed['open_signals'] if x['grade'] == 'A+'); mut(o)
    st = Site(S, feed_override=feed); st.click(f'#picker button[data-sel="{o["signal_id"]}"]')
    card = [norm_ws(x) for x in st.text('#card').split('\n') if norm_ws(x)]
    st.click('#tab-chart'); st.page.wait_for_timeout(350)
    side = [norm_ws(x) for x in st.text('#chartSide').split('\n') if norm_ws(x)]
    svgt = [e['text'] for e in st.svg('#chartSvg') if e['tag'] == 'text']
    st.click('#tab-now'); prev = [norm_ws(x) for x in st.text('.prev').split('\n') if norm_ws(x)]
    for what, pred, want in expect:
        src = {'card': card, 'side': side, 'svg': svgt, 'prev': prev}[what]
        got = next((x for x in src if pred(x)), '(missing)')
        C.add(f'page synthetic: {tag}', f'{what}: {want[:70]}', got.lower(), want.lower())
    st.close()
def edge0(o):
    o['card']['from_entry'].update(still_rose10_pct=60, still_rose10_exact_pct=60.0); o['edge_level_pct'] = 0; o['edge_status'] = 'lost'
run('from-entry share under the bar', edge0, [
    ('card', lambda x: x.startswith('Edge lost'), 'Edge lost. Its odds were below the bar from the entry. The odds below are as of the entry close, not from today.'),
    ('card', lambda x: 'bar from entry' in x, 'Below the 70% bar from entry'),
    ('side', lambda x: 'below the bar' in x, 'below the bar already'),
    ('svg', lambda x: x.startswith('Edge gone'), '(missing)'),
    ('prev', lambda x: x in ('Edge lost', 'On track'), 'Edge lost')])
def noedge(o):
    o['card']['from_entry'].update(still_rose10_pct=90, still_rose10_exact_pct=90.0)
    for r in o['card']['if_it_falls_first']: r.update(still_rose10_pct=80, still_rose10_exact_pct=80.0)
    o['edge_level_pct'] = None; o['edge_status'] = 'intact'
run('every ladder row at or above the bar', noedge, [
    ('card', lambda x: x.startswith('On track'), 'On track. It has not fallen to its edge level. The odds below are as of the entry close, not from today.'),
    ('card', lambda x: x.startswith('Holds'), 'Holds at every level'),
    ('side', lambda x: x.startswith('holds'), 'holds at every level'),
    ('svg', lambda x: x.startswith('Edge gone'), '(missing)'),
    ('prev', lambda x: x in ('Edge lost', 'On track'), 'On track')])
def tie(o):   # a share shown as 70% whose exact value is 69.6: the bar is tested on the exact share
    r = o['card']['if_it_falls_first'][0]; r.update(still_rose10_pct=70, still_rose10_exact_pct=69.6)
    o['card']['from_entry'].update(still_rose10_pct=90, still_rose10_exact_pct=90.0); o['edge_level_pct'] = -5
run('a share shown as 70% but 69.6 exactly', tie, [('card', lambda x: 'before it rises 10%' in x, '−5% before it rises 10%')])
def empty_row(o):
    r = o['card']['if_it_falls_first'][3]; r.update(past_trades=0, past_signals=0, still_rose10_pct=None, went_on_to_fall25_pct=None, still_rose10_exact_pct=None)
run('a ladder row with no signals', empty_row, [('card', lambda x: x == 'n/a' or x == 'n/a%', 'n/a')])
def era0(o):
    o['card']['before_2022'].update(past_trades=0, past_signals=0, rose10_never_fell25_within60d_pct=None)
run('an era with no signals', era0, [('card', lambda x: x.startswith('n/a'), 'n/a')])
print([x[1:6] for x in C.rows if x[5] == 'NO']); print(len(C.rows))
csv.writer(open(f'checks_pages_{NAME}.csv', 'w', newline='')).writerows(C.rows)
