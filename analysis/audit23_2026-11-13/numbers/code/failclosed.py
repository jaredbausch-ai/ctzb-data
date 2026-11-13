"""Clock on day D+1, candles end on day D: must fail closed (cards withheld, page 'held back')."""
import json, os, subprocess, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pagerun
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
res = []
for d, clk in (('2024-03-10', '2024-03-11T00:00:30Z'), ('2025-12-31', '2026-01-01T00:00:30Z'), ('2026-11-10', '2026-11-11T00:19:00Z')):
    w = os.path.join(OUT, 'work', 'fc_' + d)
    r = subprocess.run(['bash', os.path.join(OUT, 'base', 'tests', 'replay_at.sh'), d, w, clk, '--keep-going'], capture_output=True, text=True)
    f = json.load(open(os.path.join(w, 'feed', 'ctzb_feed.json')))
    st = open(os.path.join(w, 'datasets', 'stack_status.txt')).read().strip()
    h = pagerun.run(w, os.path.join(w, 'h.json'))
    card = h['initial']['card']
    res.append(dict(date=d, clock=clk, withheld=f['cards_withheld'], failed_steps=f['checks']['failed_steps'], cards=len(f['cards']),
                    open=len(f['open_signals']), regime=f.get('market_regime'), stack=st[:160], page_state=card.split('\n')[:3]))
    shutil.rmtree(w, ignore_errors=True)
    print(res[-1])
json.dump(res, open(os.path.join(OUT, 'failclosed.json'), 'w'), indent=1)
