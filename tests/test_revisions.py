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
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from build123d import Box as _Box, Location as _Loc              # noqa: E402
from cad import build as B, cascade as CC, derive as D, lock as L  # noqa: E402
from cad import layout as LY, params, project as PJ, revisions as R  # noqa: E402
from cad import tables as TB                                     # noqa: E402
from cad.refuse import Refused                                   # noqa: E402
from cad import assembly as A                                    # noqa: E402
from cad.parts import box as box_part, holder as holder_part, lid  # noqa: E402
import reference as REF                                          # noqa: E402

CSV = ROOT / "automation" / "parts.csv"
fails = []
asserted = set()

# The release under test. NOT pinned the way `tests/reference.py` pins 7.0:
# nothing here compares against a stored reference, and every assertion below
# is 7.0 against the NEWEST release, which stays true as an iteration letter
# moves because the line is monotonic — a flag introduced at 7.1a is still on
# at 7.1b. `cad/revisions.py`, "An unreleased release is iterated by LETTER".
NEW = R.RELEASES[-1]


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:62s} {got!r} vs {want!r}")
    if not ok:
        fails.append(f"{label}: {got!r} vs {want!r}")
    return ok


def since(flag):
    """The release a flag ships in, taken from the flag itself."""
    return next(f.metadata["since"] for f in R.flags() if f.name == flag)


def before(flag):
    """The release just before a flag ships — the OLD end of its comparison.

    From the flag's own `since` and NEVER from `RELEASES[-1]`: the newest
    release is the flag's own only while the flag is the latest change, and
    the next iteration letter would otherwise have a flag compared with a
    release that already carries it — a check that cannot fail and says
    nothing. `7.1d` is what found that: `stout_lattice` shipped at `7.1c` and
    its OLD end became `7.1c` itself.
    """
    return R.previous(since(flag))


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


# --- the Lid cuts one socket per pusher -------------------------------------
print(f"\n=== {since('lid_socket_per_pusher')}  lid_socket_per_pusher ===")
asserted.add("lid_socket_per_pusher")
# The Innovation M lids, named: the four in the 7.0 catalogue and, from
# 2026-09-11, the two of the `Three Expansions` row, which is an Innovation M
# too and so gets Onshape's three sockets at 7.0. Any other row in the
# catalogue must be IDENTICAL across the two releases: the flag changes these
# and nothing else.
CHANGED = {"M5.15.15.45.Un", "M5.15.15.62.Sl", "M5.10.10.32.Un", "M5.10.10.45.Sl",
           "M8.16.10-16.45.Un", "M8.16.10-16.62.Sl"}


def only_lid_flag(d):
    """`d` with THIS flag on and every other release change off.

    The release carries four changes and two of them reach the Lid:
    `two_pushers` drops the box to two, and the socket count follows it.
    Comparing 7.0 with it therefore shows 28 lids changing and says nothing
    about which flag did what. Turning on one flag at a time is what isolates
    them, and it is the same technique that prices the socket block below.
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
        check(f"{d70.calModelName}: 7.0 has 3 sockets, {NEW} has 2",
              [n70, n71], [3, 2])
        # 7.0 is Onshape's size rule; 7.1 is the box's pusher count.
        check(f"{d70.calModelName}: 7.0 = the size rule",
              n70, 2 if d70.HorizontalSlots <= 3 else 3)
        check(f"{d70.calModelName}: {NEW} = one per pusher",
              n71, box_part.pusher_slot_count(d71))
        # The OUTER PAIR does not move: that is what makes the change free.
        c70, c71 = lid.socket_centres(d70), lid.socket_centres(d71)
        check(f"{d70.calModelName}: the outer pair is where it was",
              [round(x, 6) for x in c71], [round(c70[0], 6), round(c70[-1], 6)])
        check(f"{d70.calModelName}: and 7.0's middle one is their midpoint",
              round(c70[1], 6), round((c70[0] + c70[-1]) / 2, 6))

check("exactly the Innovation M lids change", sorted(moved), sorted(CHANGED))
print(f"  ({same} lids identical across the two releases)")

# The size of the change, from the solid. A release moves TWO things at once —
# the geometry its flags gate, and the `CC <v>` engraved on every part — so
# they are separated here rather than lumped into one tolerance.
#
# The FLAG alone: a 7.0 Derived carrying THIS flag and no other. Everything
# else, the engraved `CC 7.0` included, is identical, so the difference can
# only be the socket. This is the number that says the flag changed exactly
# one thing.
row = next(r for r in rows() if (r.get("Short name") or "").strip() == "4 Ages 5 Expansions")
d70, d71 = at(row, 0, "7.0"), at(row, 0, NEW)


def body(part):
    return max(part.solids(), key=lambda s: s.volume).volume


block = lid.socket(d70, lid.socket_centres(d70)[1]).volume
v70, v71 = body(lid.build(d70)), body(lid.build(d71))
v_flag = body(lid.build(only_lid_flag(d70)))
print(f"  (one socket block = {block:.2f} mm3)")
check("the flag alone removes exactly one socket block",
      round(v70 - v_flag - block, 3), 0.0, 0.02)
# What the OTHER flags of the newest release do to this lid, on 7.0's ink:
# nothing until 7.2c, whose `larger_lid_text` scales the text block up.
v_all = body(lid.build(D.Derived(dict(d70.items()), R.of(NEW))))
grown = v_all - v_flag
print(f"  (the other flags of {NEW} add {grown:+.2f} mm3 — the text block's growth)")
# The STAMP is the rest of it: `CC 7.0` and `CC <the new release>` are not the
# same ink — and from an iteration letter they are not even the same number of
# glyphs — and that difference is the only other thing between the two builds.
digits = (v_all - v71)
print(f"  (the version digits = {digits:+.2f} mm3)")
check(f"and the whole 7.0 -> {NEW} difference is that block, the text's growth and the digits",
      round(v70 - v71 - block + grown - digits, 3), 0.0, 0.02)
check("the digits are ink, not geometry (under 2 mm3)", abs(digits) < 2.0, True)
check("the two releases write the same number of solids",
      len(lid.build(d70).solids()), len(lid.build(d71).solids()))


# --- 7.1: every cascade takes two pushers -----------------------------------
print(f"\n=== {since('two_pushers')}  two_pushers ===")
asserted.add("two_pushers")
# 24 of the 50 lose their third slot: 16 Dominion, 6 FCM, 2 Compile. Innovation
# and every S box were on two already, so the count is the assertion.
dropped, kept = [], 0
for row in rows():
    for sleeved in (0, 1):
        d70, d71 = at(row, sleeved, "7.0"), at(row, sleeved, NEW)
        n70, n71 = box_part.pusher_slot_count(d70), box_part.pusher_slot_count(d71)
        check_quiet = n71 == 2
        if not check_quiet:
            fails.append(f"{d71.calModelName}: 7.1 has {n71} pusher slots, not 2")
        if n70 == n71:
            kept += 1
        else:
            dropped.append((d70.calModelName, d70.GameName, n70, n71))
check(f"every cascade takes two pushers at {NEW}",
      sorted({box_part.pusher_slot_count(at(r, s, NEW))
              for r in rows() for s in (0, 1)}), [2])
check("24 of them had three at 7.0", len(dropped), 24)
check("and 7.0 still gives 3 to every M and L that is not Innovation",
      sorted({(g, n70) for _m, g, n70, _n71 in dropped}),
      [("Compile", 3), ("Dominion", 3), ("FCM", 3)])
print(f"  ({kept} cascades were on two already)")

# The Lid follows on its own — one socket per pusher — so nothing anywhere has
# three sockets at 7.1. That is the two flags agreeing, and it is the thing a
# future change could quietly break.
check(f"no lid has three sockets at {NEW}",
      sorted({lid.socket_count(at(r, s, NEW))
              for r in rows() for s in (0, 1)}), [2])

# The thumb cutout MOVES, because calFingerHoleOffset is written in terms of
# the slot count, and three things must stay true of it. Through the part's own
# `rear_thumb_x` — whose offset is measured from the SECOND cavity's left edge,
# not the left inner wall, and re-deriving it by hand invents collisions that
# are not there (spec/BOX.md). An invariant at both releases, not a snapshot.
def thumb_faults(d):
    left = -box_part.box_width(d) / 2 + box_part.WALL
    run, inner = box_part.rear_pocket(d)
    r = D.ThumbCutoutRadius
    out = []
    for t in box_part.rear_thumbs_x(d):
        if any(t - r < b and a < t + r for a, b in box_part.storage_dividers(d)):
            out.append("over a divider")
        if t - r < run:
            out.append("outside the empty run")
        if t + r > inner or t - r < left:
            out.append("past an end wall")
    return out

for v in R.RELEASES:
    bad = {at(r, s, v).calModelName: f for r in rows() for s in (0, 1)
           for f in [thumb_faults(at(r, s, v))] if f}
    check(f"{v}: every thumb is clear of the dividers, in the run, inside the walls",
          bad, {})


# --- 7.1: the floor is 2.000, and it grows UPWARD ---------------------------
print(f"\n=== {since('thick_floor')}  thick_floor ===")
asserted.add("thick_floor")
# The claim has two halves and they are asserted separately: the floor IS
# thicker, and NOTHING ELSE MOVED. The second half is the whole reason the
# change is cheap — the rim, the rim cutouts, `Top of back` and every other
# bed-referenced feature of the lock are where they were, and the 0.400 comes
# out of the cavity.
check("7.0: the floor is the wall's own 1.600",
      sorted({box_part.floor_top(at(r, s, "7.0"))
              for r in rows() for s in (0, 1)}), [1.6])
check(f"{NEW}: the floor is 2.000",
      sorted({box_part.floor_top(at(r, s, NEW))
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
check(f"{NEW}: the same face, the same area, 0.400 higher",
      [up_area(bfl, box_part.THICK_FLOOR),
       up_area(bfl, box_part.WALL - box_part.ENGRAVE)],
      [top70, 0.0])
check("and the engraving rides up with it, still 0.400 deep",
      up_area(bfl, box_part.THICK_FLOOR - box_part.ENGRAVE), ink70)
print(f"  (floor top {top70:.1f} mm2, engraved ink {ink70:.1f} mm2)")

# `bottom_slot` is a THROUGH cut and has to follow the floor: stopping it at
# 1.600 would leave a 0.400 membrane across the card area, which no test of
# volume alone would notice.
_w, _depth, slot_y = box_part.bottom_slot(dboxfl)
membrane = added & _Box(2.0, 2.0, 6.0).moved(_Loc((0.0, slot_y, 2.0)))
check("the card area is still cut clean through — no membrane",
      0.0 if membrane is None else round(membrane.volume, 6), 0.0)

# What it costs: everything standing on the floor rises 0.400, and the closed
# lid's inner face lands on the rim, so the holder's headroom is the budget.
rises, heads = set(), []
for row_ in rows():
    for sleeved in (0, 1):
        a70, a71 = at(row_, sleeved, "7.0"), at(row_, sleeved, NEW)
        rises.add(round(A.holder_closed(a71, 0)((0, 0, 0))[2]
                        - A.holder_closed(a70, 0)((0, 0, 0))[2], 6))
        heads.append(a71.BoxHeight - (box_part.floor_top(a71)
                                      + 2 * holder_part.half_height(a71)))
check("every holder rises by exactly the 0.400", sorted(rises), [0.4])
check("and every one of them still clears the rim", min(heads) > 0.4, True)
print(f"  (the tightest headroom left is {min(heads):.3f} mm)")


# --- 7.1b: a thumb cutout every 70 mm of back pocket ------------------------
print(f"\n=== {since('rear_thumbs_spread')}  rear_thumbs_spread ===")
asserted.add("rear_thumbs_spread")
# Before the flag the pocket has ONE cutout however wide it is, and it is
# `#calFingerHoleOffset` that places it. Both halves are asserted: the older
# releases keep Onshape's single cutout at Onshape's position, and nothing at
# them is placed by the pocket.
for v in ("7.0", "7.1a"):
    check(f"{v}: one cutout per pocket, wherever the pocket is",
          sorted({len(box_part.rear_thumbs_x(at(r, s, v)))
                  for r in rows() for s in (0, 1)}), [1])
    off = {at(r, s, v).calModelName for r in rows() for s in (0, 1)
           if box_part.rear_thumbs_x(at(r, s, v))
           != [box_part.rear_thumb_x(at(r, s, v))]}
    check(f"{v}: and `#calFingerHoleOffset` is what places it", off, set())

# From 7.1b the POCKET places them. Four rules, on all 50 boxes: the pitch is a
# ceiling and not a target, the outer pair keep REAR_THUMB_CLEAR of wall, two
# cutouts leave at least that much wall between them, and the row is centred —
# which is what says `#calFingerHoleOffset` has stopped being consulted.
P, C = box_part.REAR_THUMB_PITCH, box_part.REAR_THUMB_CLEAR
r_ = D.ThumbCutoutRadius
counts, gaps, ends, offs = {}, [], [], []
for row_ in rows():
    for sleeved in (0, 1):
        dd = at(row_, sleeved, NEW)
        xs = box_part.rear_thumbs_x(dd)
        x0, x1 = box_part.rear_pocket(dd)
        counts[len(xs)] = counts.get(len(xs), 0) + 1
        gaps += [b - a for a, b in zip(xs, xs[1:])]
        ends += [xs[0] - r_ - x0, x1 - (xs[-1] + r_)]
        offs.append(round((xs[0] + xs[-1]) / 2 - (x0 + x1) / 2, 9))
check(f"no two cutouts are more than {P:.0f} apart", max(gaps) <= P + 1e-9, True)
check("and none is closer than a cutout's width plus the clearance",
      min(gaps) >= 2 * r_ + C - 1e-9, True)
check(f"every pocket keeps {C:.0f} mm of wall at each end",
      min(ends) >= C - 1e-9, True)
check("the row is centred on the pocket, not on calFingerHoleOffset",
      sorted(set(offs)), [0.0])
check("and the wide pockets really did gain cutouts",
      max(counts), 5)
print(f"  (counts {dict(sorted(counts.items()))}, gaps "
      f"{min(gaps):.2f}..{max(gaps):.2f} mm)")

# One box, built with THIS flag alone: at 7.0 it has three pusher slots and a
# `CC 7.0` stamp, so the only difference is the cutouts. The widest pocket in
# the catalogue, which is where the change is for.
dth70 = next(at(r, s, "7.0") for r in rows() for s in (0, 1)
             if at(r, s, "7.0").calModelName == "L3.18.6.20.Sl")
dthum = D.Derived(dict(dth70.items()),
                  R.Rev(**{f.name: f.name == "rear_thumbs_spread"
                           for f in R.flags()}))
t70, tth = box_part.build(dth70), box_part.build(dthum)
check("the flag alone leaves 7.0's single cutout at one",
      len(box_part.rear_thumbs_x(dth70)), 1)
n_new = len(box_part.rear_thumbs_x(dthum))
check("and gives that pocket several", n_new > 1, True)
# It differs BOTH ways, and that is the row moving rather than growing: the
# 7.0 cutout is not one of the new five, so where it was is filled back in.
# Both differences must lie in the same place — the outer back wall, in the
# band between the top of the hanging holes and the cap. A cutout that reached
# the 1.300 inner wall or the lattice would not show up in a volume alone.
band = (box_part.slot_band(dthum)[1], box_part.HOLE_ROW_TOP, box_part.REAR_TOP)
for what, diff in (("removes", t70 - tth), ("fills back in", tth - t70)):
    bb = diff.bounding_box()
    check(f"what it {what} is all in the outer back wall",
          [round(bb.min.Y, 3) >= round(band[0], 3) - 1e-6,
           round(bb.min.Z, 3) >= band[1], round(bb.max.Z, 3)],
          [True, True, band[2]])
# And the net is what four more cutouts cost: a half-cylinder of the 1.600
# outer wall each, plus their flares.
half = 0.5 * math.pi * D.ThumbCutoutRadius ** 2 * box_part.WALL
net = t70.volume - tth.volume
check(f"the net is {n_new - 1} more half-cylinders of outer wall",
      net / half, float(n_new - 1), 0.05)
print(f"  ({n_new} cutouts on {dthum.calModelName}, {net:.1f} mm3 net, "
      f"{net / half:.3f} half-cylinders)")

# Several cutouts cost the outer back wall's ledge its place in `sharp_edges`
# — OCCT refuses that chain across a cutout (`box.sharp_edges`). It is a
# kernel limit and not a design change, so the ledge must still come out
# ROUNDED, on both faces, between two cutouts. Probed rather than reasoned
# about: a bar across the wall at 0.01 below the cap, where a 0.600 round has
# eaten 0.446 of each face, and the same bar 0.700 lower where it has not.
xs_new = box_part.rear_thumbs_x(dthum)
y_lo, y_hi = box_part.slot_band(dthum)[1], box_part.box_depth(dthum) / 2 + box_part.REAR_DEPTH
mid = (xs_new[1] + xs_new[2]) / 2       # solid wall between two cutouts


def wall_span(part, x, z):
    bar = _Box(0.02, 3 * (y_hi - y_lo), 0.02).moved(_Loc((x, (y_lo + y_hi) / 2, z)))
    hit = [q for q in (part & bar).solids()
           if q.bounding_box().min.Y > y_lo - 1e-6]
    return [round(hit[0].bounding_box().min.Y, 3),
            round(hit[0].bounding_box().max.Y, 3)] if len(hit) == 1 else hit


# The bar is 0.02 tall and the bounding box reads its LOWER face, where a
# SMOOTH_R round has eaten this much of each side.
dz = 0.02
eaten = box_part.SMOOTH_R - (2 * box_part.SMOOTH_R * dz - dz ** 2) ** 0.5
check("between two cutouts the wall's top is still rounded on BOTH faces",
      wall_span(tth, mid, box_part.REAR_TOP - dz / 2),
      [round(y_lo + eaten, 3), round(y_hi - eaten, 3)], 1e-3)
check("and it is the full 1.600 again below the round",
      wall_span(tth, mid, box_part.REAR_TOP - box_part.SMOOTH_R - 0.1),
      [round(y_lo, 3), round(y_hi, 3)], 1e-3)
check("which is what the single-cutout wall does at 7.0, to the micron",
      wall_span(t70, mid, box_part.REAR_TOP - dz / 2),
      wall_span(tth, mid, box_part.REAR_TOP - dz / 2), 1e-6)


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
# 7.1's is ("none", "none") and cannot be told from 7.2's — nor from 7.1a's,
# since an iteration letter is not a counter and does not change the pair.
# That is WHY the metadata exists, and it is asserted rather than left as a
# comment: the glyph narrows a part down to a release family, the metadata
# names the build.
check(f"{NEW}'s signature is the counterless pair",
      V.STAMP_SIGNATURES[NEW], ("none", "none"))
check("and it is the same pair 7.1 itself will read",
      V.STAMP_SIGNATURES.get("7.1"), ("none", "none"))

with tempfile.TemporaryDirectory() as tmp:
    written = {}
    for v, dd in (("7.0", d70), (NEW, d71)):
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
    for v, other in (("7.0", NEW), (NEW, "7.0")):
        fatal, _warn = V.check_stamp(written[v], other)
        check(f"a {v} part is refused as {other}", fatal is not None, True)

# --- 7.1c: a stouter lattice ------------------------------------------------
print(f"\n=== {since('stout_lattice')}  stout_lattice ===")
asserted.add("stout_lattice")
# Two halves, asserted separately because they answer different halves of the
# failure. The window is narrower, so the PILLAR between two of them is wider
# — that is bond area, and a pillar snaps across its layers. And there is one
# more ROW, so the pillar is tied back to a bridge sooner — that is free
# height, which is what lets the nozzle and the bridge above break it during
# the print. `spec/BOX.md` and `spec/HOLDER.md`, "A stouter lattice".
OLD = before("stout_lattice")


def mullions(d):
    """The gaps between the five windows of the holder's first window row."""
    row0 = sorted(holder_part.window_grid(d)[:holder_part.COLS])
    return [round(row0[c + 1][0] - row0[c][1], 6)
            for c in range(holder_part.COLS - 1)]


def only(d, flag):
    """`d` with THIS flag on and every other release change off."""
    return D.Derived(dict(d.items()),
                     R.Rev(**{f.name: f.name == flag for f in R.flags()}))


# --- the width. The pitch does not move, so every 1.000 the window gives up
# is 1.000 the pillar gains, and only a window's +X edge moves.
for v, want in ((OLD, 10.0), (NEW, 9.0)):
    check(f"{v}: every box hanging hole is {want:.3f} wide",
          sorted({round(b - a, 3) for r in rows() for s in (0, 1)
                  for a, b in box_part.hanging_holes(at(r, s, v))}), [want])
    check(f"{v}: every holder window is {want:.3f} wide",
          sorted({round(x1 - x0, 3) for r in rows() for s in (0, 1)
                  for x0, x1, _z0, _z1 in holder_part.window_grid(at(r, s, v))}),
          [want])

moved, gained = set(), set()
for row_ in rows():
    for sleeved in (0, 1):
        do, dn = at(row_, sleeved, OLD), at(row_, sleeved, NEW)
        if [round(a, 6) for a, _b in box_part.hanging_holes(do)] != \
           [round(a, 6) for a, _b in box_part.hanging_holes(dn)]:
            moved.add(f"{do.calModelName} box")
        if sorted({round(x0, 6) for x0, _x1, _z0, _z1
                   in holder_part.window_grid(do)}) != \
           sorted({round(x0, 6) for x0, _x1, _z0, _z1
                   in holder_part.window_grid(dn)}):
            moved.add(f"{do.calModelName} holder")
        ho, hn = box_part.hanging_holes(do), box_part.hanging_holes(dn)
        gained.add(round((hn[1][0] - hn[0][1]) - (ho[1][0] - ho[0][1]), 6))
        gained.add(round(mullions(dn)[0] - mullions(do)[0], 6))
check("no window's -X edge moves — the pitch is untouched", sorted(moved), [])
check("so the pillar gains exactly what the window gave up, both parts",
      sorted(gained), [1.0])

# --- the rows. The BAND does not move either: four rows divide
# HOLE_ROW_BOTTOM..HOLE_ROW_TOP where three did.
for v, n, tall in ((OLD, 3, 20.833), (NEW, 4, 15.125)):
    check(f"{v}: the box lattice has {n} rows",
          sorted({len(box_part.hole_rows(at(r, s, v)))
                  for r in rows() for s in (0, 1)}), [n])
    check(f"{v}: and a box pier runs {tall} free",
          sorted({round(b - a, 3) for r in rows() for s in (0, 1)
                  for a, b in box_part.hole_rows(at(r, s, v))}), [tall])
    check(f"{v}: the rows still fill HOLE_ROW_BOTTOM..HOLE_ROW_TOP",
          sorted({(round(box_part.hole_rows(at(r, s, v))[0][0], 6),
                   round(box_part.hole_rows(at(r, s, v))[-1][1], 6))
                  for r in rows() for s in (0, 1)}),
          [(box_part.HOLE_ROW_BOTTOM, box_part.HOLE_ROW_TOP)])
    check(f"{v}: the holder has {n} window rows",
          sorted({len(holder_part.window_grid(at(r, s, v))) // holder_part.COLS
                  for r in rows() for s in (0, 1)}), [n])

unfilled = set()
for row_ in rows():
    for sleeved in (0, 1):
        for v in (OLD, NEW):
            dd = at(row_, sleeved, v)
            _w, hh, z0 = holder_part.outline(dd)
            top = max(z1 for _a, _b, _c, z1 in holder_part.window_grid(dd))
            if round(top + holder_part.RAIL - (z0 + hh), 6) != 0.0:
                unfilled.add((dd.calModelName, v))
check("the windows and their rails still fill the outline exactly",
      sorted(unfilled), [])

# --- the worst case in the catalogue, named: FCM at calSlotwidth 63, whose
# mullion is the thinnest thing either part has.
worst = next((r, s) for r in rows() for s in (0, 1)
             if at(r, s, OLD).calSlotwidth == 63.0)
dwo, dwn = at(*worst, OLD), at(*worst, NEW)
check(f"the narrowest holder mullion: {OLD} 1.800 -> {NEW} 2.800",
      [mullions(dwo)[0], mullions(dwn)[0]], [1.8, 2.8])
gwo, gwn = holder_part.window_grid(dwo)[0], holder_part.window_grid(dwn)[0]
check(f"and its free run: {OLD} 18.167 -> {NEW} 13.125",
      [round(gwo[3] - gwo[2], 3), round(gwn[3] - gwn[2], 3)], [18.167, 13.125])
# The decoupling. 7.0's window width IS `#LipLength`, reused; the rear lip is
# the same variable doing its real job and it does NOT follow the window.
check("the rear lip keeps #LipLength — the window has parted from it",
      [holder_part.LIP_LEN, holder_part.window_w(dwn)], [10.0, 9.0])

# --- built, with THIS flag alone against 7.0: the engraved `CC 7.0`, the
# pusher count and the floor are then identical, so every difference is the
# lattice's. It differs BOTH ways — a row boundary moves, so an old rail's
# material goes and a new one's arrives — and the sharp claim is that all of
# it lies inside the lattice band and nothing else on the part moves at all.
for label, part_mod, d70, band in (
        ("holder", holder_part, at(*worst, "7.0"), None),
        ("box", box_part, at(*worst, "7.0"),
         (box_part.HOLE_ROW_BOTTOM, box_part.HOLE_ROW_TOP))):
    dst = only(d70, "stout_lattice")
    if band is None:
        _w, hh, z0 = holder_part.outline(d70)
        band = (z0, z0 + hh)
    a, b = part_mod.build(d70), part_mod.build(dst)
    ba, bb_ = a.bounding_box(), b.bounding_box()
    check(f"{label}: the part does not grow — same bounding box",
          [round(v, 4) for v in (bb_.min.X, bb_.min.Y, bb_.min.Z,
                                 bb_.max.X, bb_.max.Y, bb_.max.Z)],
          [round(v, 4) for v in (ba.min.X, ba.min.Y, ba.min.Z,
                                 ba.max.X, ba.max.Y, ba.max.Z)])
    for way, diff in (("gains", b - a), ("loses", a - b)):
        check(f"{label}: it {way} material — the lattice is restated, not nudged",
              diff is not None and diff.volume > 1e-6, True)
        if diff is None:
            continue
        dbb = diff.bounding_box()
        check(f"{label}: and what it {way} lies inside the lattice band "
              f"{band[0]:.3f}..{band[1]:.3f}",
              [dbb.min.Z >= band[0] - 1e-4, dbb.max.Z <= band[1] + 1e-4],
              [True, True])


# --- 7.1d: both editions of a mark ship, on a plate each --------------------
print(f"\n=== {since('both_lid_editions')}  both_lid_editions ===")
asserted.add("both_lid_editions")
# Nothing about a lid's SHAPE changes here: what changes is how many lids a
# project holds. So the assertions are of three kinds — which cascades gain
# one (named, and no others), what the second one carries, and that the two
# go on a plate each — and the geometry claim is the negative one: the two
# lids differ in the mark and in nothing else at all.
LID_OLD, LID_NEW = before("both_lid_editions"), since("both_lid_editions")
# The two single-set Innovation cascades, both sleevings: four projects.
BOTH = {"S3.15.10.20.Un", "S3.15.10.32.Sl",
        "XS5.15.10.32.Un", "XS5.15.10.45.Sl"}


def lids_of(row, sleeved, version):
    """The Lid objects `cad.cascade` puts in a project, (name, file) each."""
    d = at(row, sleeved, version)
    return [(n, fn) for n, fn in CC.parts(row, d) if n.startswith("Lid")]


gained, kept, wrong = set(), 0, []
for r in rows():
    for sleeved in (0, 1):
        old_lids = lids_of(r, sleeved, LID_OLD)
        new_lids = lids_of(r, sleeved, LID_NEW)
        model = at(r, sleeved, LID_OLD).calModelName
        if len(old_lids) != 1:
            wrong.append(f"{model}: {len(old_lids)} lids at {LID_OLD}")
        if len(new_lids) == 2:
            gained.add(model)
        elif new_lids == old_lids:
            kept += 1
        else:
            wrong.append(f"{model}: {len(new_lids)} lids at {LID_NEW}")
check(f"{LID_OLD}: every cascade in the catalogue ships ONE lid, and every "
      f"other cascade still does at {LID_NEW}", wrong, [])
check(f"{LID_NEW}: the cascades that ship two are the single-set ones",
      sorted(gained), sorted(BOTH))
print(f"  ({kept} cascades ship one lid at both releases)")

# What the second one IS. The cascade keeps the mark it carried — the plain
# `Innovation` — and the alternate is the game's DEFAULT edition, which is the
# one that says Ultimate. Named from both ends so a swap of the two would fail
# here rather than print a shelf full of the wrong word.
row_ss = next(r for r in rows() if at(r, 0, LID_NEW).calModelName == "S3.15.10.20.Un")
dss = at(row_ss, 0, LID_NEW)
check("the cascade's own lid carries the plain mark",
      lid.logo_choice(dss, TB.LID_OWN)[0], "@innovation-plain")
check("the alternate carries the game's default (Ultimate) mark",
      lid.logo_choice(dss, TB.LID_ALTERNATE)[0].startswith("@innovation-ultimate"), True)
check("the alternate's FILE says which edition it is",
      B.lid_file(dss, TB.LID_ALTERNATE), "Lid S3.15.10.20-Un Ultimate.3mf")
check("and the cascade's own keeps the name it always had",
      B.lid_file(dss, TB.LID_OWN), "Lid S3.15.10.20-Un.3mf")
check("the OBJECT in the project says it too",
      [PJ.object_name("Lid", dss, TB.LID_OWN), PJ.object_name("Lid", dss, TB.LID_ALTERNATE)],
      ["Lid 135U", "Lid 135U Ultimate"])
# A cascade that already carries its game's default has no alternate to ask
# for, and asking is a caller's bug rather than a lid to build.
dult = at(next(r for r in rows()
               if at(r, 0, LID_NEW).calModelName == "S5.15.15.45.Un"), 0, LID_NEW)
try:
    lid.logo_choice(dult, TB.LID_ALTERNATE)
    refused = False
except Refused:
    refused = True
check("a cascade with one edition refuses to build an alternate", refused, True)


# A plate each, and named by the object so the owner can tell which is which
# in Studio. `plate_groups` reads a name and a footprint off each object and
# nothing else, so a stub is the whole of what it needs.
class _Stub:
    def __init__(self, name, size):
        self.name, self.size = name, size


def plates_for(names):
    objs = [_Stub(n, (200.0, 40.0, 20.0) if n.startswith("Lid")
                  else (150.0, 60.0, 30.0)) for n in names]
    return [nm for nm, _idxs in LY.plate_groups(objs, "p1")]


check("two editions go on a plate each, named by the object",
      plates_for(["Box", "Lid 135U", "Lid 135U Ultimate"]),
      ["Box + pushers", "Lid 135U", "Lid 135U Ultimate"])
check("and one lid still takes the scheme's own plate name",
      plates_for(["Box", "Lid 135U"]), ["Box + pushers", "Lid"])

# The geometry: the two lids are the SAME lid. Everything that is not the mark
# — the shell, the sockets, the closing grooves, the floor's engraving, the
# outer rounds — has to be identical, so the whole of the difference lies in
# the pattern's own Z band. The XS lid is the catalogue's smallest and so the
# cheapest to build twice.
dxs = at(next(r for r in rows()
              if at(r, 0, LID_NEW).calModelName == "XS5.15.10.32.Un"), 0, LID_NEW)
own, other = lid.build(dxs, TB.LID_OWN), lid.build(dxs, TB.LID_ALTERNATE)
bo, bt = own.bounding_box(), other.bounding_box()
check("the two editions are the same lid: same bounding box",
      [round(v, 4) for v in (bt.min.X, bt.min.Y, bt.min.Z, bt.max.X, bt.max.Y, bt.max.Z)],
      [round(v, 4) for v in (bo.min.X, bo.min.Y, bo.min.Z, bo.max.X, bo.max.Y, bo.max.Z)])
for way, diff in (("gains", other - own), ("loses", own - other)):
    check(f"the alternate {way} material — it is a different mark, not the same one",
          diff is not None and diff.volume > 1e-6, True)
    if diff is None:
        continue
    dbb = diff.bounding_box()
    check(f"and what it {way} lies inside the pattern's band "
          f"0.000..{lid.PATTERN_DEPTH:.3f}",
          [dbb.min.Z >= -1e-4, dbb.max.Z <= lid.PATTERN_DEPTH + 1e-4],
          [True, True])


# --- 7.2a: the rearmost holder is a RearHolder, without rear lips ----------
print(f"\n=== {since('rear_holder')}  rear_holder ===")
asserted.add("rear_holder")
# Every holder's rear lips hook the holder behind it; the rearmost has only
# the box's back wall behind it, 0.950 away, which a shallow slant's lips
# reach past. So from 7.2a riser 0 is built as a RearHolder — the same holder
# without the lips — and the change is asserted three ways: what a project
# CONTAINS, what the flag alone REMOVES from the part, and that the deep
# holder at the back takes the RearHolder name rather than FirstHolder.
RH_OLD, RH_NEW = before("rear_holder"), since("rear_holder")


HOLDER_ROLES = ("Holder", "FirstHolder", "RearHolder")


def roles_of(row, sleeved, version):
    d = at(row, sleeved, version)
    return sorted(n for n, _fn in CC.parts(row, d) if n in HOLDER_ROLES)


def want_roles(d):
    n = d.RisingSliders
    if d.isDeepSlotAtBack:
        return sorted(["RearHolder"] + ["Holder"] * (n - 1))
    if d.isFirstSlidingSlotOverride:
        return sorted(["RearHolder", "FirstHolder"] + ["Holder"] * (n - 2))
    return sorted(["RearHolder"] + ["Holder"] * (n - 1))


bad_old, bad_new, bad_rear = [], [], []
for r in rows():
    for sleeved in (0, 1):
        do, dn = at(r, sleeved, RH_OLD), at(r, sleeved, RH_NEW)
        old, new = roles_of(r, sleeved, RH_OLD), roles_of(r, sleeved, RH_NEW)
        if "RearHolder" in old or len(old) != do.RisingSliders:
            bad_old.append(do.calModelName)
        if new != want_roles(dn):
            bad_new.append((dn.calModelName, new, want_roles(dn)))
        if ([A.rear_of(dn, j) for j, _f in A.holders(dn)] != [True] + [False] * (dn.RisingSliders - 1)
                or any(A.rear_of(do, j) for j, _f in A.holders(do))):
            bad_rear.append(dn.calModelName)
check(f"{RH_OLD}: no cascade ships a RearHolder, and every one ships RisingSliders holders", bad_old, [])
check(f"{RH_NEW}: every cascade ships exactly one RearHolder in a Holder's place", bad_new, [])
check(f"{RH_NEW}: riser 0 is the rear holder and no other is; at {RH_OLD} none is", bad_rear, [])

# The deep holder at the back is the RearHolder, under that name, with the
# deep depth; a deep holder at the front stays a FirstHolder beside a plain
# RearHolder.
d8 = next(at(r, 0, RH_NEW) for r in rows() if at(r, 0, RH_NEW).calModelName == "M8.16.10-16.45.Un")
check("Three Expansions: RearHolder is the deep one and there is no FirstHolder",
      [k for k, _js in A.holder_kinds(d8)], [(True, True), (False, False)])
check("... and its file says so", B.holder_file(d8, True, True), "RearHolder M8.16.10-16.45-Un.3mf")
d_front = next(at(r, 1, RH_NEW) for r in rows()
               if at(r, 1, RH_NEW).isFirstSlidingSlotOverride and not at(r, 1, RH_NEW).isDeepSlotAtBack
               and at(r, 1, RH_NEW).RisingSliders > 2)
check(f"{d_front.calModelName}: a plain RearHolder at the back and the FirstHolder at the front",
      [k for k, _js in A.holder_kinds(d_front)], [(False, True), (False, False), (True, False)])

# Built, with THIS flag alone against the release before it: the RearHolder
# is the plain holder less its lips and nothing else — it loses material, all
# of it behind the rear face (Y > 0), and gains none. On the deepest plain
# holder in the catalogue.
d_rh = at(box_row, 0, "7.0")
plain = holder_part.build(d_rh, False)
rear = holder_part.build(d_rh, False, rear=True)
gone = plain - rear
check("the RearHolder gains nothing", (rear - plain) is None or round((rear - plain).volume, 6) == 0.0, True)
check("and what it loses is the lips: all behind the rear face",
      [gone is not None and gone.volume > 1.0, gone is not None and round(gone.bounding_box().min.Y, 3) >= 0.0],
      [True, True])
print(f"  (the lips are {0.0 if gone is None else gone.volume:.2f} mm3 on {d_rh.calModelName})")


# --- 7.2b: every cascade ships an unmarked lid, on a plate of its own -------
print(f"\n=== {since('unmarked_lid')}  unmarked_lid ===")
asserted.add("unmarked_lid")
# Like `both_lid_editions`, a change to what a project CONTAINS: every
# cascade gains one more lid, with no mark in its underside and `(C) Mertner`
# where the game's name is. Asserted four ways: the lids a project holds at
# both ends; the names; that the credit line clears everything beside it on
# every lid (the measurement that chose the short form — see `lid.CREDIT`);
# and, built, that the unmarked lid differs from the cascade's own in the
# pattern band and the middle line's ink and nowhere else.
UL_OLD, UL_NEW = before("unmarked_lid"), since("unmarked_lid")
SUFFIX = " " + TB.LID_UNMARKED_NAME
from fontTools.ttLib import TTFont                               # noqa: E402
from cad import text as T                                        # noqa: E402
_cmap = TTFont(T.LOGO_FONT).getBestCmap()

wrong = []
for r in rows():
    for sleeved in (0, 1):
        old_lids, new_lids = lids_of(r, sleeved, UL_OLD), lids_of(r, sleeved, UL_NEW)
        model = at(r, sleeved, UL_NEW).calModelName
        if any(n.endswith(SUFFIX) for n, _fn in old_lids):
            wrong.append(f"{model}: an unmarked lid at {UL_OLD}")
        if new_lids[:-1] != old_lids or not new_lids[-1][0].endswith(SUFFIX) \
                or not new_lids[-1][1].endswith(SUFFIX + ".3mf"):
            wrong.append(f"{model}: {UL_NEW} lids {new_lids} vs {UL_OLD} {old_lids}")
check(f"{UL_OLD}: no cascade ships an unmarked lid; {UL_NEW}: every cascade "
      f"ships the lids it did plus one, last, named by the suffix", wrong, [])
check(f"{UL_NEW}: the single-set Innovation cascades ship three lids",
      sorted(at(r, s, UL_NEW).calModelName for r in rows() for s in (0, 1)
             if len(lids_of(r, s, UL_NEW)) == 3), sorted(BOTH))
check(f"{UL_NEW}: and every other cascade ships two",
      sorted({len(lids_of(r, s, UL_NEW)) for r in rows() for s in (0, 1)
              if at(r, s, UL_NEW).calModelName not in BOTH}), [2])

d168 = at(next(r for r in rows() if at(r, 0, UL_NEW).calModelName == "S4.16.10.32.Un"), 0, UL_NEW)
check("the unmarked lid's FILE says so", B.lid_file(d168, TB.LID_UNMARKED),
      "Lid S4.16.10.32-Un Unmarked.3mf")
check("and its OBJECT in the project", PJ.object_name("Lid", d168, TB.LID_UNMARKED),
      "Lid 168U Unmarked")
check("and the two lids go on a plate each, named by the object",
      plates_for(["Box", "Lid 168U", "Lid 168U Unmarked"]),
      ["Box + pushers", "Lid 168U", "Lid 168U Unmarked"])
check("the credit is what Allan asked for, and the font has its glyphs",
      [lid.CREDIT, lid.middle_line(d168, TB.LID_UNMARKED), lid.middle_line(d168),
       all(ord(c) in _cmap for c in lid.CREDIT)],
      ["(C) Mertner", "(C) Mertner", "Dominion", True])
try:
    lid.logo_choice(d168, "blank")
    refused = False
except Refused:
    refused = True
check("an unknown variant is refused, not built as one of the three", refused, True)

# The credit line clears the logo block and every pusher socket on every lid,
# at full CAP_LINE and the game line's own right edge: on an XS lid the text
# block sits beside the sockets, and on a 3-slot S lid the staircase's top
# step reaches into the middle line's band — which is where the long form
# collided. Text solids only, no lid build. The clearance is reported.
clear, overlap = None, []
for r in rows():
    for sleeved in (0, 1):
        dd = at(r, sleeved, UL_NEW)
        line = lid.text_block(dd, TB.LID_UNMARKED)[1]     # the middle line
        beside = lid.logo_block(dd) + [lid.socket(dd, x) for x in lid.socket_centres(dd)]
        hit = sum((line & o).volume for o in beside if (line & o) is not None)
        if hit > 1e-9:
            overlap.append((dd.calModelName, round(hit, 3)))
        bb = line.bounding_box()
        for o in beside:
            ob = o.bounding_box()
            if ob.max.Y > bb.min.Y and ob.min.Y < bb.max.Y and ob.max.X <= bb.min.X:
                gap = bb.min.X - ob.max.X
                if clear is None or gap < clear[0]:
                    clear = (gap, dd.calModelName)
check("the credit line meets nothing beside it on any lid", overlap, [])
check("and keeps more than a line gap clear of the nearest thing",
      clear[0] > lid.LINE_GAP, True)
print(f"  (tightest: {clear[0]:.2f} mm on {clear[1]})")

# Built, on the XS lid: one body and no inlays; the same envelope as the
# cascade's own lid; and the whole difference lies in two bands — the mark's
# pocket, filled back in (0.000..PATTERN_DEPTH), and the middle line's ink
# (WALL..WALL + TEXT_PROUD), both ways.
body_u, inlays_u = lid.build_all(dxs, TB.LID_UNMARKED)
check("the unmarked lid has no inlays and one solid",
      [len(inlays_u), len(body_u.solids())], [0, 1])
bu = body_u.bounding_box()
check("and the same envelope as the cascade's own lid",
      [round(v, 4) for v in (bu.min.X, bu.min.Y, bu.min.Z, bu.max.X, bu.max.Y, bu.max.Z)],
      [round(v, 4) for v in (bo.min.X, bo.min.Y, bo.min.Z, bo.max.X, bo.max.Y, bo.max.Z)])
bands = ((0.0, lid.PATTERN_DEPTH), (lid.WALL, lid.WALL + lid.TEXT_PROUD))


def in_a_band(solid):
    b = solid.bounding_box()
    return any(b.min.Z >= lo - 1e-4 and b.max.Z <= hi + 1e-4 for lo, hi in bands)


for way, diff in (("gains", body_u - own), ("loses", own - body_u)):
    check(f"the unmarked lid {way} material", diff is not None and diff.volume > 1e-6, True)
    if diff is None:
        continue
    check(f"and every piece it {way} is in the pattern band or the text band",
          [s.bounding_box().max.Z for s in diff.solids() if not in_a_band(s)], [])
gained = body_u - own
check("what it gains in the pattern band is the mark's pocket, exactly",
      round(sum(s.volume for s in gained.solids()
                if s.bounding_box().max.Z <= lid.PATTERN_DEPTH + 1e-4), 3),
      round(sum(q.volume for q in lid.inlays(dxs)), 3), 0.05)


# --- 7.2c: the text block grows with the lid, up to 1.5x -------------------
print(f"\n=== {since('larger_lid_text')}  larger_lid_text ===")
asserted.add("larger_lid_text")
# The +X block is the same ~35 x 14 on every lid before the flag; from it,
# one factor per cascade scales every cap and gap, anchored at the block's
# cap top and right edge, until the block is LINE_GAP from what is to its
# left or keeps at the front what it keeps at the back — and never past
# TEXT_SCALE_MAX (Allan: larger where space permits, not filling the space).
# Asserted from the built text solids, not the formula: where the ink lands.
LT_OLD, LT_NEW = before("larger_lid_text"), since("larger_lid_text")


def block_box(d, variant=TB.LID_OWN):
    bbs = [s.bounding_box() for s in lid.text_block(d, variant)]
    return (min(b.min.X for b in bbs), min(b.min.Y for b in bbs),
            max(b.max.X for b in bbs), max(b.max.Y for b in bbs))


def left_bound(d):
    if d.HorizontalSlots > 2:
        return -(lid.lid_width(d) / 2 - lid.WALL) + lid.logo_offset(d) + lid.logo_width(d)
    return lid.socket_centres(d)[0] + d.calFootTotalWidth / 2


old_scales, scales, moved, tight, shared, sizes = set(), {}, [], [], [], {}
for r in rows():
    for sleeved in (0, 1):
        do, dn = at(r, sleeved, LT_OLD), at(r, sleeved, LT_NEW)
        old_scales.add(lid.text_scale(do))
        s = lid.text_scale(dn)
        scales[dn.calModelName] = (dn.calSizeLetter, round(s, 3))
        bo, bn = block_box(do), block_box(dn)
        # the anchors: the block is scaled ABOUT its right edge and its cap
        # top, so every extent of the ink sits `s` times as far from them as
        # it did — the ink's own top and right included, which overshoot the
        # pen's by a glyph's bearing and grow with it
        right, top = lid.text_anchor(dn)
        if any(abs((a - n) - s * (a - o)) > 1e-6
               for a, o, n in ((right, bo[0], bn[0]), (right, bo[2], bn[2]),
                               (top, bo[1], bn[1]), (top, bo[3], bn[3]))):
            moved.append(dn.calModelName)
        # the clearances, off the ink — wherever the block GREW. Where it did
        # not it is where the sketch put it, which on the two S2 rows is 0.3
        # from the staircase and on the shallowest L lid inside the front
        # margin; the rule never makes either worse.
        front = -lid.lid_depth(dn) / 2 + lid.WALL + D.FootDistanceFromWall + 2.0
        if s > 1.0 and (bn[0] - left_bound(dn) < lid.LINE_GAP - 1e-6 or bn[1] - front < -1e-6):
            tight.append((dn.calModelName, round(bn[0] - left_bound(dn), 3), round(bn[1] - front, 3)))
        # and the cascade's own and unmarked lids share the scale (it is per
        # cascade, not per lid): the lines they have in common land on the
        # same ink, whichever of their middle lines is the wider
        own_lines, unm_lines = lid.text_block(dn), lid.text_block(dn, TB.LID_UNMARKED)
        for i in (0, 2):
            a, b = own_lines[i].bounding_box(), unm_lines[i].bounding_box()
            if any(abs(x - y) > 1e-6 for x, y in ((a.min.X, b.min.X), (a.min.Y, b.min.Y),
                                                  (a.max.X, b.max.X), (a.max.Y, b.max.Y))):
                shared.append(dn.calModelName)
        sizes[dn.calSizeLetter] = sizes.get(dn.calSizeLetter, []) + [round(s, 3)]

check(f"{LT_OLD}: every lid's block is at scale 1.0", sorted(old_scales), [1.0])
check(f"{LT_NEW}: every scale is within 1.0 .. {lid.TEXT_SCALE_MAX}",
      all(1.0 <= s <= lid.TEXT_SCALE_MAX for _l, s in scales.values()), True)
check("the block is scaled about its cap top and right edge, every extent by s", moved, [])
check("wherever it grew, the ink keeps LINE_GAP from the left bound and the back's margin from the front", tight, [])
check("a cascade's own and unmarked lids share one scale", shared, [])
# The M and L lids that do not reach the cap are the four SHALLOW ones, held
# by the front wall and not by anything beside them; the shallowest of all
# has no depth to grow into and stays where it was.
SHALLOW = ["L3.18.6.20.Sl", "L3.18.6.20.Un", "L5.7.7.20.Un", "M5.6.6.20.Un"]
check("every M and L lid reaches the cap but the four shallowest",
      sorted(m for m, (l, s) in scales.items() if l in ("M", "L") and s < lid.TEXT_SCALE_MAX),
      SHALLOW)
check("and those are depth-bound: their width room alone would allow the cap",
      all(lid.text_room(at(r, s_, LT_NEW))[0] / lid.text_block_size(at(r, s_, LT_NEW))[0] > lid.TEXT_SCALE_MAX
          for r in rows() for s_ in (0, 1) if at(r, s_, LT_NEW).calModelName in SHALLOW),
      True)
check("the shallowest lid, 35 mm deep, stays at 1.0", scales["L3.18.6.20.Un"][1], 1.0)
check("and no XS or S lid gets past 1.4 — the Card Cascade block bounds them",
      max(s for l, s in scales.values() if l in ("XS", "S")) < 1.4, True)
check("but every S lid but the two long-model S2 rows does grow",
      sorted(m for m, (l, s) in scales.items() if l == "S" and s < 1.1),
      ["S2.40.12-30.32.Un", "S2.40.12-30.45.Sl"])
for letter in ("XS", "S", "M", "L"):
    print(f"  ({letter}: {min(sizes[letter])} .. {max(sizes[letter])})")

# The whole block still clears the sockets and the Card Cascade block on
# every lid, ink against ink: the credit-line check of 7.2b, on all three
# lines at the new size.
overlap = []
for r in rows():
    for sleeved in (0, 1):
        dd = at(r, sleeved, LT_NEW)
        beside = lid.logo_block(dd) + [lid.socket(dd, x) for x in lid.socket_centres(dd)]
        for variant in (TB.LID_OWN, TB.LID_UNMARKED):
            hit = sum((ln & o).volume for ln in lid.text_block(dd, variant)
                      for o in beside if (ln & o) is not None)
            if hit > 1e-9:
                overlap.append((dd.calModelName, variant, round(hit, 3)))
check("the scaled block meets nothing beside it on any lid, either variant", overlap, [])

# Built with THIS flag alone against 7.0 on an M lid, which reaches the cap:
# same envelope, and every piece of the difference is in the text band and on
# the +X side — the Card Cascade block at -X does not scale.
d_m70 = at(box_row, 0, "7.0")                      # M5.15.15.45.Un
lt = only(d_m70, "larger_lid_text")
check("the M lid takes the full 1.5 with the flag alone", lid.text_scale(lt), 1.5)
m70, mlt = lid.build(d_m70), lid.build(lt)
b70, blt = m70.bounding_box(), mlt.bounding_box()
check("the lid does not grow: same bounding box",
      [round(v, 4) for v in (blt.min.X, blt.min.Y, blt.min.Z, blt.max.X, blt.max.Y, blt.max.Z)],
      [round(v, 4) for v in (b70.min.X, b70.min.Y, b70.min.Z, b70.max.X, b70.max.Y, b70.max.Z)])
for way, diff in (("gains", mlt - m70), ("loses", m70 - mlt)):
    check(f"the flag {way} material", diff is not None and diff.volume > 1e-6, True)
    if diff is None:
        continue
    check(f"and what it {way} is in the text band, on the +X side",
          [round(s_.bounding_box().min.Z, 3) for s_ in diff.solids()
           if not (s_.bounding_box().min.Z >= lid.WALL - 1e-4
                   and s_.bounding_box().max.Z <= lid.WALL + lid.TEXT_PROUD + 1e-4
                   and s_.bounding_box().min.X > 0)], [])
print(f"  (the block gains {(mlt - m70).volume:.2f} mm3 of ink on {d_m70.calModelName})")


# --- 7.2d: a plain box, without label holders, on a plate of its own ------
print(f"\n=== {since('plain_box_plate')}  plain_box_plate ===")
asserted.add("plain_box_plate")
# Like `unmarked_lid`, a change to what a project CONTAINS: a cascade whose
# row sets `Plain box` ships a second box, LAST, built without its label
# holders — the `Label holders` option's geometry (`tests/test_box.py` holds
# that to a reference STEP), so nothing is built here. Asserted at both ends
# over every row: no PlainBox before the flag; from it, exactly the rows with
# the column, one each, last, named apart on disk, the rest of the project
# untouched; the twin's Derived; the refusal; and the plate it lands on.
PB_OLD, PB_NEW = before("plain_box_plate"), since("plain_box_plate")
PB_FILE = " no label holders.3mf"


def plain_of(row, sleeved, version):
    return [(n, fn) for n, fn in CC.parts(row, at(row, sleeved, version)) if n == "PlainBox"]


wrong, shipping = [], set()
for r in rows():
    asks = (r.get("Plain box") or "").strip().upper() == "TRUE"
    for sleeved in (0, 1):
        old, new = plain_of(r, sleeved, PB_OLD), plain_of(r, sleeved, PB_NEW)
        model = at(r, sleeved, PB_NEW).calModelName
        if old:
            wrong.append(f"{model}: a PlainBox at {PB_OLD}")
        if asks:
            shipping.add(model)
            parts_new = CC.parts(r, at(r, sleeved, PB_NEW))
            if (len(new) != 1 or parts_new[-1][0] != "PlainBox"
                    or parts_new[-1][1] != B.box_file(at(r, sleeved, PB_NEW)).replace(".3mf", PB_FILE)
                    or parts_new[:-1] != CC.parts(r, at(r, sleeved, PB_OLD))):
                wrong.append(f"{model}: {PB_NEW} parts end {parts_new[-2:]}")
        elif new:
            wrong.append(f"{model}: a PlainBox without the column")
check(f"{PB_OLD}: no cascade ships a PlainBox; {PB_NEW}: every row with `Plain box` "
      f"ships exactly one, last, named apart, and nothing else moves", wrong, [])
check(f"{PB_NEW}: Compile's six cascades are the ones, and only they",
      sorted(shipping), sorted(at(r, s, PB_NEW).calModelName for r in rows() for s in (0, 1)
                               if (r.get("Game") or "").strip() == "Compile"))
check("... and the column is asked through ships_plain_box, which is off at the old end",
      [B.ships_plain_box(r, at(r, 0, v)) for r in rows() for v in (PB_OLD, PB_NEW)
       if (r.get("Game") or "").strip() == "Compile"], [False, True] * 3)

d105 = at(next(r for r in rows() if at(r, 0, PB_NEW).calModelName == "S4.7.7.20.Un"), 0, PB_NEW)
twin = B.plain_box_twin(d105)
check("the twin is the same cascade without its label holders",
      [twin.isLabelHoldersOnBox, d105.isLabelHoldersOnBox, twin.calModelName, twin.Version,
       twin.rev == d105.rev],
      [0, 1, d105.calModelName, d105.Version, True])
check("and everything else on it is the cascade's own",
      sorted(k for (k, a), (_k, b) in zip(twin.items(), d105.items()) if a != b),
      ["LabelHolders", "isLabelHoldersOnBox"])
check("its FILE is the box's, named apart", B.box_file(twin), "Box S4.7.7.20-Un no label holders.3mf")
check("and the catalogue builds both boxes for the row",
      sorted(fn for _g, fn, _p in B.box_catalogue(game="Compile", model="S4.7.7.20-Un")),
      ["Box S4.7.7.20-Un no label holders.3mf", "Box S4.7.7.20-Un.3mf"])
try:
    B.plain_box_twin(twin)
    refused = False
except Refused:
    refused = True
check("a box already without holders has no twin: refused, not shipped twice", refused, True)
check("the plain box goes LAST, on a plate of its own, named for what it lacks",
      plates_for(["Box", "Pusher", "Lid 105U", "Lid 105U Unmarked", "Holder", "PlainBox"]),
      ["Box + pushers", "Lid 105U", "Lid 105U Unmarked", "Holders", "Box without label holders"])
check("and its role is its own, not the Box's", LY.role("PlainBox"), "PlainBox")


# --- every change has a case here ------------------------------------------
print("\n=== coverage ===")
check("every flag in revisions.Rev is asserted above",
      sorted(f.name for f in R.flags()), sorted(asserted))

print(f"\n{'FAILED: ' + '; '.join(fails) if fails else 'all checks passed'}")
sys.exit(1 if fails else 0)
