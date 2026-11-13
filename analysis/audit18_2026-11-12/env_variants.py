"""The same full page check under other browser settings: time zone, locale, phone and large screens."""
import datetime as dt, sys, csv
import run_page as RP
out=[]
for name, kw in (('tz Pacific/Kiritimati (UTC+14), locale de-DE', dict(tz='Pacific/Kiritimati', locale='de-DE')),
                 ('tz America/Los_Angeles, locale en-US', dict(tz='America/Los_Angeles', locale='en-US')),
                 ('phone 390x844', dict(viewport=(390, 844))), ('large 2560x1440', dict(viewport=(2560, 1440)))):
    for st, root, today in (('REPLAY', '../a18/replay_0414', dt.date(2026, 11, 12)), ('CURRENT', '../a18/current', dt.date(2026, 11, 13))):
        C, ctx, _ = RP.run(f'{st} [{name}]', root, today, site_kw=kw)
        page = [r for r in C.rows if r[1].startswith('page')]
        bad = [r for r in page if r[5] != 'ok']
        print(st, name, 'page comparisons', len(page), 'disagreements', len(bad), flush=True)
        for r in bad[:8]: print('   ', r[1], '|', r[2], '|', str(r[3])[:90], '|', str(r[4])[:90])
        out += page
csv.writer(open('env_checks.csv', 'w', newline='')).writerows(out)
