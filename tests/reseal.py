"""Test helper, not part of the pipeline: re-record the run seal (seal.py) after a test has written fixture
files into a datasets folder, standing in for the scoring steps that would have written them in a real run.

    from reseal import reseal; reseal('/path/to/datasets')
    python3 tests/reseal.py /path/to/datasets
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import seal  # noqa: E402


def reseal(out, steps=seal.ORDER, started_at=None):
    """started_at: the run's start time to record; default the one already in the seal, else now (CTZB_NOW honoured)."""
    old = seal._read(out) or {}
    s = started_at or old.get('started_at') or seal.now_utc().strftime('%Y-%m-%dT%H:%M:%SZ')
    seal._write(out, {'steps': list(steps), 'files': seal._files(out), 'started_at': s})


if __name__ == '__main__':
    reseal(sys.argv[1])
