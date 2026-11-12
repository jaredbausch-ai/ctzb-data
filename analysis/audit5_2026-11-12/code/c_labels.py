"""Checks 9 and 10: labels against what the numbers measure; nothing reads as a return, a trade taken or a track record."""
import json, re, datetime as dt
from fractions import Fraction as Fr
import core as K
from rec import chk
from c_page import misses, norm

S = '/tmp/claude-0/-home-claude/64265722-7367-5383-a30a-6078f46fd10f/scratchpad'


def check(st, C):
    feed, pairs, W = C['feed'], C['pairs'], C['W']
    now = W['now']; today = now.date()
    P = json.load(open(f'{S}/audit5/work/page_{st}.json')); snaps = {s['tag']: s for s in P['snaps']}
    L = f'page {st} labels'
    # "If it misses: up first" = above entry on some day before the deepest-low day
    for (a, g, kb) in (('BTC', 'A+', None), ('ETH', 'A+', dt.date(2024, 9, 22)), ('ETH', 'C', None), ('BTC', 'C', None)):
        rows = [s for r, s in pairs if r['asset'] == a and r['grade'] == g and (kb is None or s['d0'] + dt.timedelta(days=60) <= kb) and not s['m']['r10']]
        first = sum(1 for s in rows if any(h > s['entry'] for k, h, l, c in s['w'] if k < s['m']['ddday']))
        chk(st, L, f'"up first" ({a} {g}{" known by 2024-09-22" if kb else ""}): count of misses above entry before their deepest low',
            misses(pairs, a, g, kb)['up_first'], first, 'up-first wording')
    # the ladder's "From entry" row vs the rows under it
    for sid, v in C['cardfig'].items():
        G = v['G']; n = len(G); r10 = sum(s['m']['r10'] for _, s in G); r10b = 0
        for _, s in G:
            e = s['entry']
            for k, h, l, c in s['w']:
                if l <= e * (1 - K.LIQ): break
                if h >= e * Fr(11, 10): r10b += 1; break
        shown_on_page = v['kind'] == 'example' or v['kind'] == 'forming' or (v['kind'] == 'open' and v['o']['grade'] == 'A+')
        if not shown_on_page:
            continue
        chk(st, L, f'[{sid}] ladder row "From entry" measured like the rows under it (rose 10% before ever falling 25.3%)',
            K.share(r10, n), K.share(r10b, n), 'mixed measures in one ladder: "From entry" counts any +10% in 60 days, the fall rows only +10% before -25.3%')
    # forming chart side note
    for tag, s_ in snaps.items():
        if tag.startswith('chart:') and tag.endswith(':alert') and "Prices use today's close as a stand-in for the entry." in norm(s_['side']):
            chk(st, L, f'[{tag}] "Prices use today\'s close as a stand-in for the entry"', "today's close",
                f"latest price of the still-open bar at {feed['generated_at'][11:16]} UTC (that bar closes later)", 'wording: the price used is not a close')
    # footer / banner date
    chk(st, L, 'footer "Data through 12 Nov 2026"', 'Data through 12 Nov 2026',
        f'last CLOSED daily bar {today - dt.timedelta(days=1)}; {today} in progress at {feed["generated_at"][11:16]} UTC', 'wording: data through a day still in progress')
    # How to read: where the odds fade
    rt = norm(snaps['read']['readTab'])
    chk(st, L, 'How to read "Where the odds fade" states the measure the rows use', 'still rose 10%' if 'still rose 10%.' in rt else '?',
        'still rose 10% before ever falling 25.3%', 'wording omits "before ever falling 25.3%" (the card note and CARD_SPEC include it)')
    for t in ('The median best price within 60 days, from the entry close', 'The median deepest dip within 60 days',
              'how many were above entry at some point first', 'The first fall at which this setup\'s odds drop below our 70% bar'):
        chk(st, L, f'How to read "{t[:50]}..." matches the measure', t in rt, True, 'wording')
    # chart toggle on live / forming charts
    for tag, s_ in snaps.items():
        if tag.startswith('chart:') and tag.endswith(':alert') and not tag.startswith('chart:example'):
            shown = ('visible' if s_.get('toggleDisplay') != 'none' and (s_.get('toggleRect') or 0) > 0 else 'hidden') + (', "At the alert" pressed' if s_.get('altPressed') == 'true' else '')
            chk(st, L, f'[{tag}] "At the alert / What happened" toggle', shown, 'hidden (live/forming chart shows the path after the alert)',
                'the toggle is meant hidden but CSS display:flex overrides [hidden]; "What happened" does nothing here')
    # 10. nothing reads as a strategy return, a trade taken or a track record
    blob = []
    for s_ in P['snaps']:
        blob += [str(s_.get(k) or '') for k in ('review', 'card', 'prevClosed', 'prevIntact', 'side', 'chSub', 'chTitle', 'cloudNote', 'readTab', 'recordTab', 'recordFine', 'footer', 'picker')]
        blob += [t.get('text', '') for t in s_['chart'] if t['tag'] == 'text']
    sents = set()
    for b in blob:
        for sent in re.split(r'(?<=[.!?\n])\s+', b):
            if re.search(r'\b(trade|trades|traded|trading|return|returns|profit|gain|win|wins|track record|performance)\b', sent, re.I):
                sents.add(norm(sent)[:160])
    ok_pat = re.compile(r'not a trade|not a trading result|not trades|never traded|not a return|lead trader|His real trades|leveraged trading can lose', re.I)
    for sent in sorted(sents):
        chk(st, L, f'entry-quality wording: "{sent[:90]}"', 'negated or about the lead trader' if ok_pat.search(sent) else 'reads as a result',
            'negated or about the lead trader', 'wording reads as a strategy result')
    chk(st, L, 'feed label on every record', all(x.get('label') == feed['label'] for x in feed['cards'] + feed['open_signals'] + feed['grade_odds'] + feed['if_it_misses'] + feed['past_paths']), True, 'label')
    chk(st, L, 'feed label text says entry quality only / not a track record', 'not a strategy return or a track record' in feed['label'] and 'No trade was taken' in feed['label'], True, 'label')
