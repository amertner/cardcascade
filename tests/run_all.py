"""Run every suite in tests/, in order, and say which failed.

Each suite is a script of its own — it prints `ok`/`FAIL` lines and exits
non-zero on any failure — and until this file there was nothing that ran
them all, so "the tests pass" was never a checkable statement. This runs
them under the venv's python in the order below, one line per suite with its
wall time, and exits non-zero if any did.

    .venv/bin/python tests/run_all.py            # everything, ~15 minutes
    .venv/bin/python tests/run_all.py --quick    # skip the slow STEP suites
    .venv/bin/python tests/run_all.py --only holder,lock

The regression suites read `build/` — run `python -m cad.build --part all`
first, or `run_all.py --build` to have it done here. `test_pusher_regression`
and `test_holder_corpus` are the two that need it; `test_build_meshes` scans
whatever is there.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# (name, needs build/, slow). Order: arithmetic first, then source vs STEP,
# then the corpus and regression suites that read build/ or individual/.
SUITES = [
    ("test_derive", False, False),
    ("test_lock", False, False),
    ("test_text_floors", False, False),
    ("test_pusher", False, False),
    ("test_box", False, True),
    ("test_lid", False, True),
    ("test_token_holder", False, False),
    ("test_topper", False, False),
    ("test_holder", False, True),
    ("test_assembly", False, False),
    ("test_pusher_regression", True, False),
    ("test_lid_corpus", False, False),
    ("test_box_corpus", True, False),
    ("test_token_holder_corpus", False, False),
    ("test_topper_corpus", False, True),
    ("test_build_meshes", True, False),
    ("test_holder_corpus", True, False),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true",
                    help="skip the slow suites (box, lid, holder, topper "
                         "corpus, holder corpus)")
    ap.add_argument("--only", help="comma-separated suite names, with or "
                                   "without the test_ prefix")
    ap.add_argument("--build", action="store_true",
                    help="run `cad.build --part all` first")
    args = ap.parse_args()

    if args.build:
        print("● building the catalogue first")
        rc = subprocess.call([PY, "-m", "cad.build", "--part", "all"], cwd=ROOT)
        if rc:
            sys.exit(f"cad.build failed ({rc})")

    only = None
    if args.only:
        only = {("test_" + n.strip()) if not n.strip().startswith("test_")
                else n.strip() for n in args.only.split(",")}
    chosen = [(n, b, s) for n, b, s in SUITES
              if (only is None or n in only) and not (args.quick and s)]
    if not chosen:
        sys.exit("nothing selected")

    results = []
    for name, needs_build, _slow in chosen:
        if needs_build and not (ROOT / "build").exists():
            results.append((name, "NO BUILD", 0.0))
            print(f"  {name:28s} NO BUILD  (run cad.build --part all)")
            continue
        t0 = time.time()
        proc = subprocess.run([PY, str(ROOT / "tests" / f"{name}.py")],
                              cwd=ROOT, capture_output=True, text=True)
        dt = time.time() - t0
        status = "PASS" if proc.returncode == 0 else "FAIL"
        results.append((name, status, dt))
        print(f"  {name:28s} {status:8s} {dt:7.1f} s")
        if proc.returncode:
            tail = (proc.stdout + proc.stderr).strip().splitlines()
            for line in tail[-12:]:
                print(f"      {line}")
        sys.stdout.flush()

    failed = [n for n, s, _ in results if s != "PASS"]
    total = sum(t for _, _, t in results)
    print(f"\n{len(results) - len(failed)} of {len(results)} suites passed "
          f"in {total / 60:.1f} min" + (f"; FAILED: {', '.join(failed)}"
                                          if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
