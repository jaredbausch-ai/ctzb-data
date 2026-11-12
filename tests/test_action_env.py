"""The GitHub Action installs numpy only at the grade step, after refresh.py (and fetch / check
steps) have run. Run those steps here with numpy blocked, so a numpy import in them fails locally
too (12 Nov 2026: refresh.py imported analysis/tagstats.py, which needs numpy, and every Action
run failed its refresh step for hours while every local test passed).

Runs on a copy of the repo so the real datasets are untouched.
    python3 tests/test_action_env.py
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCK = "import sys; sys.modules['numpy'] = None; sys.argv = sys.argv[1:]; import runpy; runpy.run_path(sys.argv[0], run_name='__main__')"
STEPS = [["refresh.py", "--data", "data", "--out", "datasets"]]

def main():
    tmp = tempfile.mkdtemp(prefix="actenv_")
    try:
        dst = os.path.join(tmp, "repo")
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "analysis/audit*", "__pycache__"))
        ok = 0
        for st in STEPS:
            r = subprocess.run([sys.executable, "-c", BLOCK] + st, cwd=dst, capture_output=True, text=True, timeout=900)
            good = r.returncode == 0
            ok += good
            print(f"  {'PASS' if good else '*** FAIL ***'}  {st[0]} runs without numpy" + ("" if good else "  -- " + (r.stderr.strip().splitlines() or ["?"])[-1]))
        print(f"\n{ok}/{len(STEPS)} passed")
        sys.exit(0 if ok == len(STEPS) else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
