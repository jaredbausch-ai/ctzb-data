"""feedcheck.py rejects the five self-contradicting feeds of audit round 48's hardening list, and passes the real one.

    python3 tests/test_feed_contradictions.py      -> exit 1 if any case fails
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tests"))
import feedcheck as F
from forged_feeds import FORGED, forge

feed = json.load(open(os.path.join(ROOT, "feed/ctzb_feed.json")))
res = []
def check(name, ok, detail=""):
    res.append(bool(ok)); print(f"  {'PASS' if ok else '*** FAIL ***'}  {name}" + ("" if ok else f"  -- {detail}"))

check("the committed feed passes", F.problems(feed) == [], F.problems(feed)[:3])
for name in FORGED:
    p = F.problems(forge(feed, name))
    check(f"rejected: {name}", p, "accepted")
print(f"\n{sum(res)}/{len(res)} passed")
sys.exit(0 if all(res) else 1)
