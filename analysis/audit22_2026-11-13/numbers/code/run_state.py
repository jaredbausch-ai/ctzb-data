"""Check one state (data + page). Usage: python3 run_state.py <state dir> <name> <out csv[.gz]> [--no-page] [--clock ISO]"""
import sys, os, json, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check, page, pagecheck

if __name__ == '__main__':
    sdir, name, out = sys.argv[1:4]
    clock = sys.argv[sys.argv.index('--clock') + 1] if '--clock' in sys.argv else None
    ck, S, X, feed = check.run(sdir, name, clock)
    if '--no-page' not in sys.argv and not feed.get('cards_withheld'):
        dpath = out.replace('.csv', '').replace('.gz', '') + '_page.json'
        dump = page.dump(sdir, dpath)
        pagecheck.run(ck, sdir, dump, S, X, feed)
        if out.endswith('.gz'):
            with open(dpath, 'rb') as f, gzip.open(dpath + '.gz', 'wb') as g:
                g.write(f.read())
            os.remove(dpath)
    check.write(ck.rows, out)
    bad = [r for r in ck.rows if r['ok'] != 'yes']
    print(f'{name}: {len(ck.rows)} comparisons, {len(bad)} disagreements')
    for r in bad[:60]:
        print('  ', r['location'], '|', r['label'], '| shown', repr(r['shown'])[:160], '| mine', repr(r['yours'])[:160])
