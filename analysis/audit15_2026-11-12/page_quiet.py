"""Audit 15 -- a state that occurs in neither frozen state: filter on, nothing live or forming at the top grade.
Made by serving the CURRENT feed without its cards and without its top-grade open signal (page test only)."""
import sys, csv, json, pickle
from fractions import Fraction as Fr
from harness import Site, norm_ws
from core import Checks, rhu
S, NAME = sys.argv[1], sys.argv[2]; C = Checks(NAME + ' (synthetic quiet)')
M = pickle.load(open(f'mine_{NAME}.pkl', 'rb'))
feed = json.load(open(f'{S}/feed/ctzb_feed.json'))
feed['cards'] = []; feed['open_signals'] = [o for o in feed['open_signals'] if o['grade'] != 'A+']
st = Site(S, feed_override=feed)
C.add('page quiet state', 'opens on the example', st.page.evaluate("document.querySelector('#previewSwitch').checked"), True)
st.page.evaluate("document.querySelector('#previewSwitch').click()"); st.page.wait_for_timeout(300)
n = sum(1 for r in M['aplus'] if '2020-01-01' <= r['entry'] <= '2025-12-31')
got = [norm_ws(x) for x in st.text('#card').split('\n') if norm_ws(x)]
exp = ["BTC · ETH", "No setup right now", "Waiting for the next one",
       f"The market filter is on. Nothing at the top grade is forming or confirmed today. Top-grade setups come about {int(rhu(Fr(n, 6)))} times a year (2020 to 2025 average).",
       "You'll get a push alert the moment one confirms.", "Statistics from past signal history. Entry quality only: no exit, not a trade or a track record."]
for i, (a, b) in enumerate(zip(got, exp)): C.add('page quiet state', f'line {i + 1}', a.lower(), b.lower())
C.add('page quiet state', 'lines', len(got), len(exp))
C.add('page quiet state', 'picker: no live setups', norm_ws(st.text('#picker .prow .pnone')), 'No live top-grade setups right now.')
pv = [norm_ws(x) for x in st.text('.prev').split('\n') if norm_ws(x)]
C.add('page quiet state', 'previous signals: none intact', pv[3], 'No open top-grade setup with its edge intact.')
print(n, [x[2:6] for x in C.rows]); st.close()
csv.writer(open(f'checks_pageq_{NAME}.csv', 'w', newline='')).writerows(C.rows)
