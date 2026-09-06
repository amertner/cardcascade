"""Run every suite in tests/, several at a time, and say which failed.

Each suite is a script of its own — it prints `ok`/`FAIL` lines and exits
non-zero on any failure — and until this file there was nothing that ran
them all, so "the tests pass" was never a checkable statement. This runs
them under the venv's python, one line per suite with its wall time as each
finishes, and exits non-zero if any did.

The suites are independent processes and most of them use one core, so they
run CONCURRENTLY: each carries a weight — the cores it takes — and the
scheduler keeps the running weights within `--jobs` (every core by default),
starting the longest suites first so the run ends when the longest one does
rather than when they have all taken their turn. Serially the tree took about
35 minutes; concurrently it takes about as long as test_box. `--jobs 1` is
the old serial run, in table order.

    .venv/bin/python tests/run_all.py            # everything, ~5 minutes
    .venv/bin/python tests/run_all.py --quick    # skip the slow STEP suites
    .venv/bin/python tests/run_all.py --only holder,lock
    .venv/bin/python tests/run_all.py --jobs 1   # one at a time, in order

The regression suites read `build/` — run `python -m cad.build --part all`
first, or `run_all.py --build` to have it done here. `test_pusher_regression`,
`test_holder_corpus`, `test_smoke`, `test_project`, `test_layout` and
`test_parallel` need it; `test_build_meshes` scans whatever is there.
"""
import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# (name, needs build/, slow, weight in cores, typical seconds). Table order is
# the serial order: arithmetic first, then source vs STEP, then the corpus and
# regression suites that read build/ or individual/. The weight is what the
# suite occupies while it runs — 1 for a single-threaded script, more for one
# that pools (test_holder_corpus takes every core), slices in Studio (a
# multi-threaded minute per project) or renders in Blender.
SUITES = [
    ("test_derive", False, False, 1, 1),
    ("test_lock", False, False, 1, 1),
    ("test_names", False, False, 1, 1),
    ("test_revisions", False, False, 1, 30),
    ("test_text_floors", False, False, 1, 9),
    ("test_pusher", False, False, 1, 60),
    ("test_box", False, True, 1, 280),
    ("test_lid", False, True, 1, 90),
    ("test_lid_marks", False, False, 1, 40),
    ("test_token_holder", False, False, 1, 10),
    ("test_topper", False, False, 1, 90),
    ("test_holder", False, True, 1, 110),
    ("test_assembly", False, False, 1, 5),
    ("test_pusher_regression", True, False, 1, 45),
    ("test_lid_corpus", False, False, 1, 9),
    ("test_box_corpus", True, False, 1, 14),
    ("test_token_holder_corpus", False, False, 1, 5),
    ("test_topper_corpus", False, True, 1, 105),
    ("test_build_meshes", True, False, 1, 18),
    ("test_holder_corpus", True, False, 6, 60),
    ("test_smoke", True, True, 4, 60),
    ("test_project", True, True, 4, 60),
    ("test_layout", True, True, 4, 160),
    # test_parallel needs the 7.0 tree (build/v7.0), not the default one:
    # it regresses against what shipped. `cad.build --part all --version 7.0`.
    ("test_parallel", True, True, 2, 70),
]


def run_one(name):
    t0 = time.time()
    proc = subprocess.run([PY, str(ROOT / "tests" / f"{name}.py")],
                          cwd=ROOT, capture_output=True, text=True)
    return name, proc.returncode, time.time() - t0, proc.stdout + proc.stderr


def schedule(chosen, jobs):
    """Run `chosen` suites concurrently within a weight budget of `jobs`,
    longest first; yields (name, rc, seconds, output) as each finishes."""
    pending = sorted(chosen, key=lambda s: -s[4])          # longest first
    running, results, lock = {}, [], threading.Lock()
    done = threading.Condition(lock)

    def worker(suite):
        r = run_one(suite[0])
        with lock:
            results.append(r)
            del running[suite[0]]
            done.notify_all()

    budget = max(1, jobs)
    while pending or running:
        with lock:
            # start whatever fits; a suite heavier than the whole budget runs
            # alone rather than never
            used = sum(s[3] for s in running.values())
            for suite in list(pending):
                if used + suite[3] <= budget or (not running and suite[3] > budget):
                    pending.remove(suite)
                    running[suite[0]] = suite
                    used += suite[3]
                    threading.Thread(target=worker, args=(suite,), daemon=True).start()
            while not results and running:
                done.wait()
            while results:
                yield results.pop(0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quick", action="store_true",
                    help="skip the slow suites (box, lid, holder, topper "
                         "corpus, and the ones that slice)")
    ap.add_argument("--only", help="comma-separated suite names, with or "
                                   "without the test_ prefix")
    ap.add_argument("--build", action="store_true",
                    help="run `cad.build --part all` first")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1,
                    help="the core budget for concurrent suites (default: "
                         "every core); 1 runs them one at a time in table order")
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
        unknown = only - {s[0] for s in SUITES}
        if unknown:
            sys.exit(f"no such suite: {', '.join(sorted(unknown))}")
    chosen = [s for s in SUITES
              if (only is None or s[0] in only) and not (args.quick and s[2])]
    if not chosen:
        sys.exit("nothing selected")

    have_build = (ROOT / "build").exists()
    results = {}
    for s in chosen:
        if s[1] and not have_build:
            results[s[0]] = ("NO BUILD", 0.0, "")
            print(f"  {s[0]:28s} NO BUILD  (run cad.build --part all)")
    chosen = [s for s in chosen if s[0] not in results]

    t_all = time.time()
    if args.jobs <= 1:
        stream = (run_one(s[0]) for s in chosen)
    else:
        stream = schedule(chosen, args.jobs)
    for name, rc, dt, out in stream:
        status = "PASS" if rc == 0 else "FAIL"
        results[name] = (status, dt, out)
        print(f"  {name:28s} {status:8s} {dt:7.1f} s")
        if rc:
            for line in out.strip().splitlines()[-12:]:
                print(f"      {line}")
        sys.stdout.flush()

    failed = [s[0] for s in SUITES if s[0] in results and results[s[0]][0] != "PASS"]
    total = sum(r[1] for r in results.values())
    wall = time.time() - t_all
    print(f"\n{len(results) - len(failed)} of {len(results)} suites passed: "
          f"{total / 60:.1f} min of suite time in {wall / 60:.1f} min"
          + (f"; FAILED: {', '.join(failed)}" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
