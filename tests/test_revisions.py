#!/usr/bin/env python3
"""What each release changes, asserted from both ends.

    .venv/bin/python tests/test_revisions.py

`cad/revisions.py` says a release changed something; this says WHAT, by
building the release before it and the release itself and measuring the
difference. Both ends, as every deliberate difference in this repo is asserted:
the older release must still have the OLD behaviour and the newer one the NEW
one, so re-converging — or forgetting to gate a change on its flag — fails here
rather than passing quietly.

Every reference STEP and every cached mesh in `individual/` is 7.0, and the
corpus tests hold a 7.0 build to them (`tests/reference.py`). That is the other
half of the claim: a release change must not disturb the release it was
introduced after.

## Adding the next change

One field in `revisions.Rev` with its `since` and `spec`, one `if d.rev.<flag>`
in the part, and one case below. If a change lands with no case here, the
"every change is asserted" check at the end fails and names it.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from cad import derive as D, lock as L, params, revisions as R   # noqa: E402
from cad.refuse import Refused                                   # noqa: E402
from cad.parts import box as box_part, lid                       # noqa: E402
import reference as REF                                          # noqa: E402

CSV = ROOT / "automation" / "parts.csv"
fails = []
asserted = set()


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:62s} {got!r} vs {want!r}")
    if not ok:
        fails.append(f"{label}: {got!r} vs {want!r}")
    return ok


def rows():
    return params.load_rows(CSV)


def at(row, sleeved, version):
    return D.derive(params.from_row(row, sleeved, version))


# --- the line itself --------------------------------------------------------
print("=== the release line ===")
check("RELEASES is ordered oldest first",
      list(R.RELEASES), sorted(R.RELEASES, key=R.key))
check("CURRENT is in RELEASES", R.CURRENT in R.RELEASES, True)
check("the reference release is one cad/ can build", REF.VERSION in R.RELEASES, True)
# Every release must declare its LOCK, because `pusher.build` refuses one that
# has not. Leaving a new release out of SAME_LOCK is the loud failure; leaving
# it out silently would stamp a new version on 7.0 tabs.
for v in R.RELEASES:
    check(f"{v}: the lock generation is declared", L.lock_generation(v), L.GENERATION)
for v in R.RELEASES:
    rev = R.of(v)
    for f in R.flags():
        if R.at_least(v, f.metadata["since"]):
            check(f"{v}: {f.name} is on", getattr(rev, f.name), True)
        else:
            check(f"{v}: {f.name} is off", getattr(rev, f.name), False)
try:
    R.of("7.15")
    refused = False
except Refused:
    refused = True
check("an unknown release is refused, not silently built", refused, True)


# --- 7.1: the Lid cuts one socket per pusher --------------------------------
print("\n=== 7.1  lid_socket_per_pusher ===")
asserted.add("lid_socket_per_pusher")
# The four Innovation M lids, named. Any other row in the catalogue must be
# IDENTICAL across the two releases: the flag changes these and nothing else.
CHANGED = {"M5.15.15.45.Un", "M5.15.15.62.Sl", "M5.10.10.32.Un", "M5.10.10.45.Sl"}
moved, same = set(), 0
for row in rows():
    for sleeved in (0, 1):
        d70, d71 = at(row, sleeved, "7.0"), at(row, sleeved, "7.1")
        n70, n71 = lid.socket_count(d70), lid.socket_count(d71)
        if n70 == n71:
            same += 1
            # and the sockets are in the same places, not merely as many
            if [round(x, 6) for x in lid.socket_centres(d70)] != \
               [round(x, 6) for x in lid.socket_centres(d71)]:
                fails.append(f"{d70.calModelName}: centres moved with no count change")
            continue
        moved.add(d70.calModelName)
        check(f"{d70.calModelName}: 7.0 has 3 sockets, 7.1 has 2", [n70, n71], [3, 2])
        # 7.0 is Onshape's size rule; 7.1 is the box's pusher count.
        check(f"{d70.calModelName}: 7.0 = the size rule",
              n70, 2 if d70.HorizontalSlots <= 3 else 3)
        check(f"{d70.calModelName}: 7.1 = one per pusher",
              n71, box_part.pusher_slot_count(d71))
        # The OUTER PAIR does not move: that is what makes the change free.
        c70, c71 = lid.socket_centres(d70), lid.socket_centres(d71)
        check(f"{d70.calModelName}: the outer pair is where it was",
              [round(x, 6) for x in c71], [round(c70[0], 6), round(c70[-1], 6)])
        check(f"{d70.calModelName}: and 7.0's middle one is their midpoint",
              round(c70[1], 6), round((c70[0] + c70[-1]) / 2, 6))

check("exactly the four Innovation M lids change", sorted(moved), sorted(CHANGED))
print(f"  ({same} lids identical across the two releases)")

# The size of the change, from the solid. A release moves TWO things at once —
# the geometry its flags gate, and the `CC <v>` engraved on every part — so
# they are separated here rather than lumped into one tolerance.
#
# The FLAG alone: a 7.0 Derived carrying 7.1's Rev. Everything else, the
# engraved `CC 7.0` included, is identical, so the difference can only be the
# socket. This is the number that says the flag changed exactly one thing.
row = next(r for r in rows() if (r.get("Short name") or "").strip() == "4 Ages 5 Expansions")
d70, d71 = at(row, 0, "7.0"), at(row, 0, "7.1")


def body(part):
    return max(part.solids(), key=lambda s: s.volume).volume


block = lid.socket(d70, lid.socket_centres(d70)[1]).volume
v70, v71 = body(lid.build(d70)), body(lid.build(d71))
v_flag = body(lid.build(D.Derived(dict(d70.items()), R.of("7.1"))))
print(f"  (one socket block = {block:.2f} mm3)")
check("the flag alone removes exactly one socket block",
      round(v70 - v_flag - block, 3), 0.0, 0.02)
# The STAMP is the rest of it: `CC 7.0` and `CC 7.1` are the same six
# characters but not the same ink, and that difference is the only other thing
# between the two builds.
digits = (v_flag - v71)
print(f"  (the version digits = {digits:+.2f} mm3)")
check("and the whole 7.0 -> 7.1 difference is that block plus the digits",
      round(v70 - v71 - block - digits, 3), 0.0, 0.02)
check("the digits are ink, not geometry (under 2 mm3)", abs(digits) < 2.0, True)
check("the two releases write the same number of solids",
      len(lid.build(d70).solids()), len(lid.build(d71).solids()))


# --- every change has a case here ------------------------------------------
print("\n=== coverage ===")
check("every flag in revisions.Rev is asserted above",
      sorted(f.name for f in R.flags()), sorted(asserted))

print(f"\n{'FAILED: ' + '; '.join(fails) if fails else 'all checks passed'}")
sys.exit(1 if fails else 0)
