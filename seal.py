"""The run seal (13 Nov 2026, after audit #21): nothing in datasets/ may change between pipeline steps.

refresh.py starts a new seal; each later scoring step (grade, extras, stack, cards) checks, as it starts, that every file the previous
step left in datasets/ is exactly as that step left it, and records, as it finishes, its own name and a
SHA-256 of every file. feed_live.py checks the seal before it builds the feed: every required step must
have finished, in order, and every file must still match. A file deleted, emptied, cut, edited or swapped
for an older copy between steps, a step that never finished, or steps run out of order all fail the run
closed instead of being published. refresh.py is the first scoring step and starts a new seal, so the
outputs of an earlier run can never carry this run's seal.

The seal also covers the scoring inputs (since 13 Nov 2026): the candle files in data/, the funding, long/short and
open-interest series in data/derivs/ and the BTC put/call series in data/options/. It guards against accidents and partial runs, not against someone with write access to
the repo: anyone who can rewrite a dataset can rewrite the manifest beside it, or the code itself.

The seal also names its run (13 Nov 2026, audit #25): `started_at`, the time refresh.py started it. feed_live.py
refuses a seal started more than MAX_RUN_HOURS before it runs, or after it: running feed_live.py again on its own
later must not publish the last run's scoring as fresh.

The seal is datasets/manifest.json: {"steps": [...], "files": {name: sha256}, "started_at": ISO time}. Standard library only
(refresh.py must run before numpy is installed).
"""
import datetime as dt, hashlib, json, os

from clock import now_utc  # CTZB_NOW replays a past run (tests)

MAX_RUN_HOURS = 2   # a whole run takes about 3 minutes

NAME = 'manifest.json'
ORDER = ('refresh', 'grade', 'extras', 'stack', 'cards')
# What extras_live.py writes. The extras step is not a gating step: if it fails part-way, its files are left out
# of the later steps' seal checks, and feed_live.py withholds just the extras fields.
EXTRAS_FILES = ('missstats.csv', 'missstats_example.csv', 'pastpaths.csv', 'pastpaths_example.csv', 'oddsfade.csv') + tuple(
    f'candles_{a}_{t}.csv' for a in ('eth', 'btc') for t in ('1d', '2d', '3d', '5d', '8d'))


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _files(out):
    """Every file in datasets/, plus the inputs the steps score from (13 Nov 2026 audit #22): the candle files
    in data/, the funding, long/short and open-interest series in data/derivs/ and the BTC put/call series in
    data/options/, keyed "data/<path>". data/ is the folder beside datasets/."""
    got = {n: _sha(os.path.join(out, n)) for n in sorted(os.listdir(out))
           if n != NAME and os.path.isfile(os.path.join(out, n))}
    data = os.path.join(os.path.dirname(os.path.abspath(out)), 'data')
    if os.path.isdir(data):
        for n in sorted(os.listdir(data)):
            if n.endswith('.csv') and os.path.isfile(os.path.join(data, n)):
                got['data/' + n] = _sha(os.path.join(data, n))
        der = os.path.join(data, 'derivs')
        if os.path.isdir(der):
            for n in sorted(os.listdir(der)):
                if n.endswith(('_funding_daily.csv', '_lsratio_daily.csv', '_oi_daily.csv')):
                    got['data/derivs/' + n] = _sha(os.path.join(der, n))
        pcr = os.path.join(data, 'options', 'BTC_pcr_daily.csv')
        if os.path.exists(pcr):
            got['data/options/BTC_pcr_daily.csv'] = _sha(pcr)
    return got


def _read(out):
    try:
        with open(os.path.join(out, NAME)) as f:
            m = json.load(f)
        if not (isinstance(m, dict) and isinstance(m.get('steps'), list) and isinstance(m.get('files'), dict)):
            return None
        return m
    except (OSError, ValueError):
        return None


def _write(out, m):
    tmp = os.path.join(out, NAME + '.tmp')
    with open(tmp, 'w') as f:
        json.dump(m, f, indent=0, sort_keys=True)
    os.replace(tmp, os.path.join(out, NAME))


def start(out):
    """A new run: the first scoring step calls this before it writes anything."""
    os.makedirs(out, exist_ok=True)
    _write(out, {'steps': [], 'files': {}, 'started_at': now_utc().strftime('%Y-%m-%dT%H:%M:%SZ')})


def age_problem(out, now=None):
    """None if the seal was started by a run at most MAX_RUN_HOURS before `now` (default: the clock), else why not."""
    m = _read(out)
    s = m.get('started_at') if m else None
    try:
        t = dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return 'the seal does not say when its run started'
    now = now or now_utc()
    if t > now:
        return f'the seal was started in the future ({s})'
    if now - t > dt.timedelta(hours=MAX_RUN_HOURS):
        return f'the seal is from an earlier run (started {s}, more than {MAX_RUN_HOURS} h ago)'
    return None


def problems(out, need=(), ignore=()):
    """What is wrong with the seal, as a list (empty = intact). `need`: steps that must have finished, in
    ORDER. `ignore`: file names whose state does not matter to the caller."""
    m = _read(out)
    if m is None:
        return ['no readable seal (datasets/manifest.json): the scoring steps did not run in this folder']
    bad = []
    done = [s for s in m['steps'] if s in ORDER]
    if done != [s for s in ORDER if s in done] or len(set(done)) != len(done):
        bad.append('steps ran out of order or twice: ' + ', '.join(m['steps']))
    for s in need:
        if s not in done:
            bad.append(f'step "{s}" did not finish')
    now = _files(out)
    for n, h in m['files'].items():
        if n in ignore:
            continue
        if n not in now:
            bad.append(f'{n} is missing')
        elif now[n] != h:
            bad.append(f'{n} changed after the step that wrote it')
    for n in now:
        if n not in m['files'] and n not in ignore and not n.endswith('.tmp'):
            bad.append(f'{n} appeared between steps')
    return bad


def check(out, step):
    """A step calls this as it starts: the steps before it finished in order and their files are untouched."""
    need = ORDER[:ORDER.index(step)]
    need = tuple(s for s in need if s != 'extras')   # extras is not a gating step: a later step may run without it
    m = _read(out) or {}
    extras_ok = 'extras' in m.get('steps', [])
    bad = problems(out, need=need, ignore=() if extras_ok or step in ('refresh', 'grade', 'extras') else EXTRAS_FILES)
    if step in m.get('steps', []):
        bad.append(f'step "{step}" already ran in this run')
    if bad:
        raise SystemExit(f'{step}: the run seal is broken: ' + '; '.join(bad[:6]))


def done(out, step):
    """A step calls this as it finishes."""
    m = _read(out) or {'steps': [], 'files': {}}
    m['steps'] = list(m['steps']) + [step]
    m['files'] = _files(out)
    _write(out, m)
