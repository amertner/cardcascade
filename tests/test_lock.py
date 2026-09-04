"""The lock catalogue's three copies, held to each other.

`automation/LOCK_STANDARD.md` is the document. It is transcribed three times:
`cad/lock.CLASSES` (the standard, as constants), `derive.calTabCentreDistance`
(the Onshape variable-studio expression, a ladder on `calPusherTotalDepth`)
and `automation/verify.LOCK_CLASSES` (the audit's own copy, with the minimum
depth as a formula rather than a number). Any one of them can drift on its own
and nothing else would notice — `calTabCentreDistance` is read by no code at
all, only by this test — so this holds all three to one table, and then walks
every pusher in parts.csv through all three.

Pure arithmetic: no build123d, so system python is fine.

    python3 tests/test_lock.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "automation"))

from cad import lock, params, derive as D          # noqa: E402
import verify                                       # noqa: E402

fails = []


def check(label, got, want, tol=0.0):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok ' if ok else 'FAIL'}  {label:60s} {got} vs {want}")
    if not ok:
        fails.append(label)


print("=== the three tables ===")
check("five classes in lock.CLASSES", len(lock.CLASSES), 5)
check("five classes in verify.LOCK_CLASSES", len(verify.LOCK_CLASSES), 5)
for (name, s, min_d), (vname, vs) in zip(lock.CLASSES, verify.LOCK_CLASSES):
    check(f"{name}: verify names it the same", vname, name)
    check(f"{name}: verify's s is the standard's", vs, s, 1e-9)
    check(f"{name}: verify's minimum depth is the standard's",
          verify.class_min_depth(s), min_d, 1e-9)
    # 1e-9: 17.4 - 3.9 is 13.499999999999998 in binary, and the floor IS 13.5
    check(f"{name}: the standard's own edge rule agrees with its floor",
          lock.check_edge(min_d + 1e-9, s), True)
    check(f"{name}: has_notch agrees with verify",
          lock.has_notch(s), verify.lock_class(min_d)[2])

print("\n=== every pusher in parts.csv, through all three ===")
seen = set()
for row in params.load_rows(ROOT / "automation" / "parts.csv"):
    for sleeved in (0, 1):
        p = params.from_row(row, sleeved)
        d = D.derive(p)
        depth = d.calPusherTotalDepth
        key = (p.GameName, round(depth, 3))
        if key in seen:
            continue
        seen.add(key)
        name, s = lock.lock_class(depth)
        check(f"{p.GameName} D={depth:.2f}: derive's s is {name}'s",
              d.calTabCentreDistance, s, 1e-9)
        check(f"{p.GameName} D={depth:.2f}: verify picks {name} too",
              verify.lock_class(depth)[0], name)
print(f"  {len(seen)} distinct pusher depths")

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
