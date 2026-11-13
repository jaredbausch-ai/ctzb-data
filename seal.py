"""The run seal (13 Nov 2026, after audit #21): nothing in datasets/ may change between pipeline steps.

Each scoring step (refresh, grade, extras, stack, cards) checks, as it starts, that every file the previous
step left in datasets/ is exactly as that step left it, and records, as it finishes, its own name and a
SHA-256 of every file. feed_live.py checks the seal before it builds the feed: every required step must
have finished, in order, and every file must still match. A file deleted, emptied, cut, edited or swapped
for an older copy between steps, a step that never finished, or steps run out of order all fail the run
closed instead of being published. refresh.py is the first scoring step and starts a new seal, so the
outputs of an earlier run can never carry this run's seal.

The seal is datasets/manifest.json: {"steps": [...], "files": {name: sha256}}. Standard library only
(refresh.py must run before numpy is installed).
"""
import hashlib, json, os

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
    return {n: _sha(os.path.join(out, n)) for n in sorted(os.listdir(out))
            if n != NAME and os.path.isfile(os.path.join(out, n))}


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
    _write(out, {'steps': [], 'files': {}})


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
