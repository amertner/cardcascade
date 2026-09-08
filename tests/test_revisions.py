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
from cad import assembly as A                                    # noqa: E402
from cad.parts import box as box_part, holder as holder_part, lid  # noqa: E402
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
# A version is an opaque STRING (7.1.1, 7.1B, ...), so the line's order is the
# tuple's order and nothing can check it against arithmetic. What CAN be
# checked is that the tuple is a well-formed line and that nothing is on it
# twice or in two places at once.
check("no release is listed twice", len(set(R.RELEASES)), len(R.RELEASES))
check("no version is both a release and a historical one",
      sorted(set(R.RELEASES) & set(R.HISTORICAL)), [])
check("position is the tuple's own order",
      [R.position(v) for v in R.RELEASES], list(range(len(R.RELEASES))))
check("a version off the line has no position", R.position("6.6"), None)
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


def only_lid_flag(d):
    """`d` with THIS flag on and every other release change off.

    7.1 carries two changes and they both reach the Lid: `two_pushers` drops
    the box to two, and the socket count follows it. Comparing 7.0 with 7.1
    therefore shows 28 lids changing and says nothing about which flag did
    what. Turning on one flag at a time is what isolates them, and it is the
    same technique that prices the socket block below.
    """
    return D.Derived(dict(d.items()),
                     R.Rev(**{f.name: f.name == "lid_socket_per_pusher"
                              for f in R.flags()}))


moved, same = set(), 0
for row in rows():
    for sleeved in (0, 1):
        d70 = at(row, sleeved, "7.0")
        d71 = only_lid_flag(d70)
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


# --- 7.1: every cascade takes two pushers -----------------------------------
print("\n=== 7.1  two_pushers ===")
asserted.add("two_pushers")
# 24 of the 50 lose their third slot: 16 Dominion, 6 FCM, 2 Compile. Innovation
# and every S box were on two already, so the count is the assertion.
dropped, kept = [], 0
for row in rows():
    for sleeved in (0, 1):
        d70, d71 = at(row, sleeved, "7.0"), at(row, sleeved, "7.1")
        n70, n71 = box_part.pusher_slot_count(d70), box_part.pusher_slot_count(d71)
        check_quiet = n71 == 2
        if not check_quiet:
            fails.append(f"{d71.calModelName}: 7.1 has {n71} pusher slots, not 2")
        if n70 == n71:
            kept += 1
        else:
            dropped.append((d70.calModelName, d70.GameName, n70, n71))
check("every cascade takes two pushers at 7.1",
      sorted({box_part.pusher_slot_count(at(r, s, "7.1"))
              for r in rows() for s in (0, 1)}), [2])
check("24 of them had three at 7.0", len(dropped), 24)
check("and 7.0 still gives 3 to every M and L that is not Innovation",
      sorted({(g, n70) for _m, g, n70, _n71 in dropped}),
      [("Compile", 3), ("Dominion", 3), ("FCM", 3)])
print(f"  ({kept} cascades were on two already)")

# The Lid follows on its own — one socket per pusher — so nothing anywhere has
# three sockets at 7.1. That is the two flags agreeing, and it is the thing a
# future change could quietly break.
check("no lid has three sockets at 7.1",
      sorted({lid.socket_count(at(r, s, "7.1")) for r in rows() for s in (0, 1)}), [2])

# The thumb cutout MOVES, because calFingerHoleOffset is written in terms of
# the slot count, and three things must stay true of it. Through the part's own
# `rear_thumb_x` — whose offset is measured from the SECOND cavity's left edge,
# not the left inner wall, and re-deriving it by hand invents collisions that
# are not there (spec/BOX.md). An invariant at both releases, not a snapshot.
def thumb_faults(d):
    left = -box_part.box_width(d) / 2 + box_part.WALL
    inner = box_part.box_width(d) / 2 - box_part.WALL
    run = left + box_part.pusher_slot_count(d) * D.back_slot_pitch(d) + box_part.DIVIDER_W
    t, r = box_part.rear_thumb_x(d), D.ThumbCutoutRadius
    out = []
    if any(t - r < b and a < t + r for a, b in box_part.storage_dividers(d)):
        out.append("over a divider")
    if t - r < run:
        out.append("outside the empty run")
    if t + r > inner or t - r < left:
        out.append("past an end wall")
    return out

for v in ("7.0", "7.1"):
    bad = {at(r, s, v).calModelName: f for r in rows() for s in (0, 1)
           for f in [thumb_faults(at(r, s, v))] if f}
    check(f"{v}: the thumb is clear of every divider, in the run, inside the walls",
          bad, {})


# --- 7.1: the floor is 2.000, and it grows UPWARD ---------------------------
print("\n=== 7.1  thick_floor ===")
asserted.add("thick_floor")
# The claim has two halves and they are asserted separately: the floor IS
# thicker, and NOTHING ELSE MOVED. The second half is the whole reason the
# change is cheap — the rim, the rim cutouts, `Top of back` and every other
# bed-referenced feature of the lock are where they were, and the 0.400 comes
# out of the cavity.
check("7.0: the floor is the wall's own 1.600",
      sorted({box_part.floor_top(at(r, s, "7.0"))
              for r in rows() for s in (0, 1)}), [1.6])
check("7.1: the floor is 2.000",
      sorted({box_part.floor_top(at(r, s, "7.1"))
              for r in rows() for s in (0, 1)}), [2.0])
check("the WALL is 1.600 at both — this is the FLOOR alone",
      [D.WallThickness, box_part.WALL], [1.6, 1.6])

# One box, built with THIS flag alone against the release before it: the
# engraved `CC 7.0` and the three pusher slots are then identical, so every
# difference below is the floor's.
box_row = next(r for r in rows()
               if (r.get("Short name") or "").strip() == "4 Ages 5 Expansions")
dbox70 = at(box_row, 0, "7.0")
dboxfl = D.Derived(dict(dbox70.items()),
                   R.Rev(**{f.name: f.name == "thick_floor" for f in R.flags()}))
b70, bfl = box_part.build(dbox70), box_part.build(dboxfl)
bb70, bbfl = b70.bounding_box(), bfl.bounding_box()
check("the box does not grow: same bounding box, rim included",
      [round(v, 4) for v in (bbfl.min.X, bbfl.min.Y, bbfl.min.Z,
                             bbfl.max.X, bbfl.max.Y, bbfl.max.Z)],
      [round(v, 4) for v in (bb70.min.X, bb70.min.Y, bb70.min.Z,
                             bb70.max.X, bb70.max.Y, bb70.max.Z)])
removed = b70 - bfl
check("nothing is taken away — the floor only grows",
      0.0 if removed is None else round(removed.volume, 6), 0.0)
added = bfl - b70
check("and what it grows by lies between the old engraving and the new floor",
      [round(added.bounding_box().min.Z, 4),
       round(added.bounding_box().max.Z, 4)], [1.2, 2.0])

# The floor's top face, and the bottoms of the glyphs cut into it, move up
# together by exactly 0.400 with the same area: the engraving is carried, not
# re-fitted, and it is still ENGRAVE deep.


def up_area(part, z, tol=1e-4):
    """Total area of the horizontal faces whose centre sits at `z`."""
    return round(sum(f.area for f in part.faces()
                     if abs(f.center().Z - z) < tol
                     and abs(abs(f.normal_at(f.center()).Z) - 1) < 1e-6), 3)


top70, ink70 = up_area(b70, box_part.WALL), up_area(b70, box_part.WALL - box_part.ENGRAVE)
check("7.0: the floor's top face is at 1.600 and none is at 2.000",
      [top70 > 0, up_area(b70, box_part.THICK_FLOOR)], [True, 0.0])
check("7.1: the same face, the same area, 0.400 higher",
      [up_area(bfl, box_part.THICK_FLOOR), up_area(bfl, box_part.WALL - box_part.ENGRAVE)],
      [top70, 0.0])
check("and the engraving rides up with it, still 0.400 deep",
      up_area(bfl, box_part.THICK_FLOOR - box_part.ENGRAVE), ink70)
print(f"  (floor top {top70:.1f} mm2, engraved ink {ink70:.1f} mm2)")

# `bottom_slot` is a THROUGH cut and has to follow the floor: stopping it at
# 1.600 would leave a 0.400 membrane across the card area, which no test of
# volume alone would notice.
from build123d import Box as _Box, Location as _Loc                # noqa: E402
_w, _depth, slot_y = box_part.bottom_slot(dboxfl)
membrane = added & _Box(2.0, 2.0, 6.0).moved(_Loc((0.0, slot_y, 2.0)))
check("the card area is still cut clean through — no membrane",
      0.0 if membrane is None else round(membrane.volume, 6), 0.0)

# What it costs: everything standing on the floor rises 0.400, and the closed
# lid's inner face lands on the rim, so the holder's headroom is the budget.
rises, heads = set(), []
for row_ in rows():
    for sleeved in (0, 1):
        a70, a71 = at(row_, sleeved, "7.0"), at(row_, sleeved, "7.1")
        rises.add(round(A.holder_closed(a71, 0)((0, 0, 0))[2]
                        - A.holder_closed(a70, 0)((0, 0, 0))[2], 6))
        heads.append(a71.BoxHeight - (box_part.floor_top(a71)
                                      + 2 * holder_part.half_height(a71)))
check("every holder rises by exactly the 0.400", sorted(rises), [0.4])
check("and every one of them still clears the rim", min(heads) > 0.4, True)
print(f"  (the tightest headroom left is {min(heads):.3f} mm)")


# --- the two witnesses, at every release ------------------------------------
# A release is claimed twice by a written part: engraved on the plastic, and
# stated in the file's metadata. Nothing else in the suite reads either, and a
# stamp signature that has not been recorded for a new release fails silently —
# `check_stamp` only warns — so it is asserted here, where the release line is.
print("\n=== the release is readable off a written part ===")
import tempfile                                                  # noqa: E402
from cad import build as B, mesh3mf                              # noqa: E402

sys.path.insert(0, str(ROOT / "automation"))
import verify as V                                               # noqa: E402

check("every release has a stamp signature recorded",
      sorted(v for v in R.RELEASES if v in V.STAMP_SIGNATURES),
      sorted(R.RELEASES))
# 7.1's is ("none", "none") and cannot be told from 7.2's; that is WHY the
# metadata exists, and it is asserted rather than left as a comment.
check("7.1's signature is the counterless pair",
      V.STAMP_SIGNATURES["7.1"], ("none", "none"))

with tempfile.TemporaryDirectory() as tmp:
    written = {}
    for v, dd in (("7.0", d70), ("7.1", d71)):
        path = Path(tmp) / f"Lid {dd.calModelName}.3mf"
        body_shape = max(lid.build(dd).solids(), key=lambda s: s.volume)
        mesh3mf.write(path, [("Lid", body_shape)],
                      metadata=B.component_metadata(dd, path))
        written[v] = path.read_bytes()

    for v, data in written.items():
        check(f"{v}: the metadata states it", V.version_metadata(data), v)
        check(f"{v}: the engraving reads it",
              v in (V.version_stamp(data) or "").split("/"), True)
        check(f"{v}: both witnesses agree with the release",
              V.check_stamp(data, v), (None, None))
    # And a part from one release is REFUSED against the other, which is the
    # whole point: 7.0's glyph differs, and 7.1's metadata is exact.
    for v, other in (("7.0", "7.1"), ("7.1", "7.0")):
        fatal, _warn = V.check_stamp(written[v], other)
        check(f"a {v} part is refused as {other}", fatal is not None, True)

# --- every change has a case here ------------------------------------------
print("\n=== coverage ===")
check("every flag in revisions.Rev is asserted above",
      sorted(f.name for f in R.flags()), sorted(asserted))

print(f"\n{'FAILED: ' + '; '.join(fails) if fails else 'all checks passed'}")
sys.exit(1 if fails else 0)
