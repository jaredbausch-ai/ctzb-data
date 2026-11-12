import sys, csv, json, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import *
OUT = os.path.dirname(os.path.abspath(__file__))
def run(name):
    S = State(name); ck = Checker(name)
    E, L = check_ledger(S, ck)
    ledger_extra(S, ck, E, L)
    check_grade_odds(S, ck, E, L)
    check_misses(S, ck, E, L)
    check_odds_fade(S, ck)
    check_cards(S, ck, E, L)
    check_open(S, ck, E, L)
    check_paths(S, ck, E, L)
    return S, ck, E, L
if __name__ == '__main__':
    allrows = []
    for nm in sys.argv[1:] or ['REPLAY', 'CURRENT']:
        S, ck, E, L = run(nm)
        allrows += ck.rows
        bad = [r for r in ck.rows if r['ok'] != 'yes']
        print(nm, len(ck.rows), 'checks', len(bad), 'disagreements')
        for r in bad[:80]: print('  ', r)
    with open(os.path.join(OUT, 'feed_checks.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['state', 'location', 'label', 'shown', 'yours', 'ok', 'cause']); w.writeheader(); w.writerows(allrows)
