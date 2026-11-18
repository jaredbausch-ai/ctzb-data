"""Write one round's audit prompts from the briefs in docs/audit/briefs/, and refuse if anything is left unfilled.

Round 40's docs prompt kept round 39's frozen commit because the prompt was copied from the round before and edited by
hand. This fills every placeholder from the briefs themselves and checks the result.

  python3 docs/audit/make_prompts.py --round 41 --parts damage,docs --scratchpad <dir> \
      --today "18 Nov 2026" --built 2026-11-18T19:06Z --forming "2 forming setups in it: ETH 2D and ETH 3D"

The frozen commit is the repo's HEAD (the states must be built from it). Writes <scratchpad>/audit<round><c|d|n>_prompt.txt.
"""
import argparse, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PARTS = {"numbers": ("numbers.txt", "n"), "damage": ("damage.txt", "c"), "docs": ("docs.txt", "d")}
KEYS = ("round", "commit", "scratchpad", "today", "built", "forming", "others")
OTHERS = {"numbers": "auditors (numbers on real data)", "damage": "an auditor (damage)", "docs": "an auditor (docs against code)"}

ap = argparse.ArgumentParser()
ap.add_argument("--round", required=True)
ap.add_argument("--parts", required=True)
ap.add_argument("--scratchpad", required=True)
ap.add_argument("--today", required=True)
ap.add_argument("--built", required=True)
ap.add_argument("--forming", required=True)
a = ap.parse_args()

commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short=7", "HEAD"], capture_output=True, text=True,
                        check=True).stdout.strip()
dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--untracked-files=no"], capture_output=True,
                       text=True, check=True).stdout.strip()
if dirty:
    sys.exit("the repo has uncommitted changes: commit them first, so the frozen commit is the code the auditors read")
parts = [p.strip() for p in a.parts.split(",") if p.strip()]
bad = [p for p in parts if p not in PARTS]
if bad:
    sys.exit(f"unknown part(s): {bad}")
problems = []
for p in parts:
    others = [OTHERS[q] for q in parts if q != p]
    vals = {"round": a.round, "commit": commit, "scratchpad": a.scratchpad.rstrip("/"), "today": a.today,
            "built": a.built, "forming": a.forming,
            "others": ("One other auditor (" + others[0].split("(", 1)[1] + " is") if len(others) == 1 else
                      ("Other auditors are" if others else "No other auditor is")}
    text = open(os.path.join(ROOT, "docs/audit/briefs", PARTS[p][0])).read()
    for k in KEYS:
        text = text.replace(f"<{k}>", vals[k])
    left = [k for k in KEYS if f"<{k}>" in text]
    stale = sorted(set(re.findall(r"\b[0-9a-f]{7}\b", text)) - {commit})
    stale = [h for h in stale if subprocess.run(["git", "-C", ROOT, "cat-file", "-e", h + "^{commit}"],
                                                capture_output=True).returncode == 0]
    rnd = sorted(set(re.findall(r"AUDIT(\d+)_", text)) - {a.round})
    if left or stale or rnd:
        problems.append(f"{p}: unfilled {left}, other commits {stale}, other rounds {rnd}")
        continue
    out = os.path.join(a.scratchpad, f"audit{a.round}{PARTS[p][1]}_prompt.txt")
    open(out, "w").write(text)
    os.makedirs(os.path.join(a.scratchpad, f"audit{a.round}{PARTS[p][1]}"), exist_ok=True)
    open(os.path.join(a.scratchpad, f"audit{a.round}{PARTS[p][1]}", "progress.log"), "a").close()
    print(f"{out}  (commit {commit})")
if problems:
    sys.exit("refused:\n  " + "\n  ".join(problems))
