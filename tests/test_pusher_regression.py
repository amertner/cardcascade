#!/usr/bin/env python3
"""Every built pusher against the Onshape one it replaces.

    .venv/bin/python -m cad.build
    .venv/bin/python tests/test_pusher_regression.py

`tests/test_pusher.py` checks the SOURCE against two hand-exported STEPs. This
checks the 34 written 3MFs against the 32 in `individual/`, through the readers
the rest of the toolchain uses (`automation/verify.py`), so it covers the
meshing and the assembly placement as well as the geometry.

## What must match, and what must not

`individual/` is a mixed catalogue: 18 of its 32 pushers were exported at 7.0
and 14 are still 6.6, whose lock sits where the pre-7.0 formula put it — tabs
4.00 and 4.20 in from the ends, so their centres are D - 12.00 apart. The
rebuild is 7.0 throughout, so it must REPRODUCE the first 18 and MOVE the other
14 onto the catalogue. Both are reported; only the reproduction is asserted.

Text is the other deliberate difference. Onshape could constrain a sketch text
box in one dimension only, so `cad/text.py` sizes by rule instead (see
`spec/PUSHER.md`); the engraving is therefore not expected to match and is not
compared here.

Everything else is the same part and is asserted, per file:

  * the bounding box — height, depth, and 4.500 total thickness
  * the assembly position — X 3.000, Y max 0, Z min -calHeightIncrement
  * the rise, read off the staircase treads (`verify.pusher_rise`)
  * two tabs, 3.800 wide, fully backed with a full 5.00 mm of root
  * the lock exactly where `verify.target_lock` puts it

The last two are the point of the exercise: they are what the C1-C5 re-cut in
Onshape would have cost a slice of the API budget to deliver.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "automation"))

import verify as V                                   # noqa: E402
from cad import build as B, derive as D, lock as L, mesh3mf   # noqa: E402
import reference as REF                                        # noqa: E402
from cad.parts import pusher                         # noqa: E402

# The tree for the release this file asserts, not the current one
# (`tests/reference.py`): build `--version 7.0` before running it.
BUILD = REF.tree()
INDIV = ROOT / "individual"
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        fails.append(f"{label}: {got!r} vs {want!r}")
        print(f"    FAIL {label}: {got!r} vs {want!r}")
    return ok


def span(path):
    """(x span, y span, z span, x min, y max, z min) of a component 3MF, mm."""
    _name, verts, _tris = mesh3mf.read(path)[0]
    c = list(zip(*verts))
    return (max(c[0]) - min(c[0]), max(c[1]) - min(c[1]), max(c[2]) - min(c[2]),
            min(c[0]), max(c[1]), min(c[2]))


items = B.pusher_catalogue()
# Which built files the planner's key would collapse onto one name. Only
# Dominion 6x10 does: `324 Card` (no override) and `290 Card (Mat)` (first
# riser 12) differ by 1.20 mm sleeved and share `Pusher 6x10-*.3mf`.
by_legacy = {}
for folder, fn, p in items:
    by_legacy.setdefault((folder, B.pusher_file(D.derive(p), legacy=True)), []).append(fn)

print(f"  {'built file':38s} {'D':>6s} {'rise':>7s} {'cls':>4s} "
      f"{'tabs':>4s} {'root':>5s} {'notch':>6s}   in individual/")
for folder, fn, p in items:
    d = D.derive(p)
    path = BUILD / folder / fn
    tag = f"{folder}/{fn}"
    if not path.exists():
        fails.append(f"{tag} was not built")
        print(f"    FAIL {tag} was not built — run `python -m cad.build` first")
        continue
    data = path.read_bytes()
    h, dep, thk, x0, y1, z0 = span(path)

    # --- the box and where it sits ---------------------------------------
    check(f"{tag} height", round(h, 3), round(d.calPusherTotalHeight, 3), 1e-3)
    check(f"{tag} depth", round(dep, 3), round(d.calPusherTotalDepth, 3), 1e-3)
    check(f"{tag} thickness", round(thk, 3), round(L.PUSHER_TOTAL, 3), 1e-3)
    check(f"{tag} assembly X", round(x0, 3), pusher.ASSEMBLY_X, 1e-3)
    check(f"{tag} assembly Y", round(y1, 3), 0.0, 1e-3)
    check(f"{tag} assembly Z", round(z0, 3), round(-d.calHeightIncrement, 3), 1e-3)

    # --- the staircase ----------------------------------------------------
    # A tread is the gap between two interior step edges, so a 2-riser pusher
    # has one edge, no tread, and `pusher_rise` reports None — as it does on the
    # four Onshape 2-riser pushers too. Its rise is pinned anyway by the height
    # check above: height is rise x risers.
    rise, _treads = V.pusher_rise(data, p.RisingSliders)
    if rise is not None:
        check(f"{tag} rise", round(rise, 2), round(d.calHeightIncrement, 2), 0.02)

    # --- the lock, against the catalogue ----------------------------------
    got = V.pusher_lock(data)
    want = V.target_lock(got["depth"])
    cls, _s = L.lock_class(d.calPusherTotalDepth)
    # `pusher_lock` probes 1200 points along the depth to find the notch, so it
    # can lose up to a sample at each end — 0.126 mm on the 75.60 mm pusher.
    # The notch's true size is asserted exactly, against the STEP, by
    # tests/test_pusher.py; here it only has to be the right feature in place.
    probe = 2 * got["depth"] / 1200
    check(f"{tag} lock class", want["class"], cls)
    for i, (lo, hi) in enumerate(want["tabs"]):
        check(f"{tag} tab {i} position",
              round(got["tabs"][i][0], 2), round(lo, 2), 0.05)
        check(f"{tag} tab {i} width",
              round(got["tabs"][i][1] - got["tabs"][i][0], 2),
              round(hi - lo, 2), 0.05)
    check(f"{tag} notch", got["notch"] is not None, want["notch"] is not None)
    if want["notch"]:
        check(f"{tag} notch position", round(got["notch"][0], 2),
              round(want["notch"][0], 2), 0.05 + probe)
        check(f"{tag} notch width",
              round(got["notch"][1] - got["notch"][0], 2), round(L.NOTCH_W, 2),
              0.05 + probe)

    # --- the tabs are held ------------------------------------------------
    tabs = V.pusher_tabs(data)
    check(f"{tag} tab count", len(tabs), V.TABS_EXPECTED)
    worst_f = min((t["fraction"] for t in tabs), default=0.0)
    worst_a = min((t["anchor"] for t in tabs), default=0.0)
    check(f"{tag} tabs fully backed", round(worst_f, 3) >= 0.999, True)
    check(f"{tag} tab root", round(worst_a, 2) >= L.TAB_L - 0.05, True)
    for t in tabs:
        check(f"{tag} tab width", round(t["w"], 2), round(L.TAB_W, 2), 0.05)

    legacy = B.pusher_file(D.derive(p), legacy=True)
    ref = INDIV / folder / legacy
    if len(by_legacy[(folder, legacy)]) > 1:
        note = f"{legacy} — SHARED, see below"
    elif ref.exists():
        note = legacy
    else:
        note = "(none)"
    shown = f"{rise:7.3f}" if rise is not None else f"{'--':>7s}"
    print(f"  {tag:38s} {got['depth']:6.2f} {shown} {cls:>4s} "
          f"{len(tabs):4d} {worst_a:5.2f} "
          f"{'yes' if got['notch'] else 'no':>6s}   {note}")

# ---------------------------------------------------------------------------
# File against file: the built pusher beside the Onshape one it replaces.
# ---------------------------------------------------------------------------
print("\n  Against individual/, file by file. `same` is a pusher Onshape had "
      "already\n  re-cut to the 7.0 catalogue; `moved` is one still at 6.6:")
print(f"    {'individual/ file':32s} {'H':>7s} {'D':>7s} {'Z':>8s} "
      f"{'their base':>10s} {'ours':>7s}  lock")
same = moved = shared = 0
for folder, fn, p in items:
    legacy = B.pusher_file(D.derive(p), legacy=True)
    ref = INDIV / folder / legacy
    tag = f"{folder}/{fn}"
    if not ref.exists():
        print(f"    {folder + '/' + legacy:32s}  not in individual/ — new geometry")
        continue
    if len(by_legacy[(folder, legacy)]) > 1 and p.isFirstSlidingSlotOverride:
        shared += 1
        print(f"    {folder + '/' + legacy:32s}  holds the OTHER geometry "
              f"({fn} is 0.76-1.20 mm deeper)")
        continue
    rh, rd, rt, rx, ry, rz = span(ref)
    bh, bd, bt, bx, by_, bz = span(BUILD / folder / fn)
    check(f"{tag} height vs individual/", round(bh, 3), round(rh, 3), 1e-3)
    check(f"{tag} depth vs individual/", round(bd, 3), round(rd, 3), 1e-3)
    check(f"{tag} thickness vs individual/", round(bt, 3), round(rt, 3), 1e-3)
    for label, a, b in (("X", bx, rx), ("Y", by_, ry), ("Z", bz, rz)):
        check(f"{tag} assembly {label} vs individual/", round(a, 3),
              round(b, 3), 1e-3)
    old = V.pusher_lock(ref.read_bytes())
    want = V.target_lock(old["depth"])
    ob = old["tabs"][1][0] - old["tabs"][0][0]
    agrees = abs(ob - 2 * want["s"]) <= 0.05
    same += agrees
    moved += not agrees
    print(f"    {folder + '/' + legacy:32s} {rh:7.2f} {rd:7.2f} {rz:8.3f} "
          f"{ob:10.2f} {2 * want['s']:7.2f}  {'same' if agrees else 'moved'}")

built = len(list(BUILD.glob("*/Pusher*.3mf")))
canon = len(list(INDIV.glob("*/Pusher*.3mf")))
orphan = sorted(str(q.relative_to(INDIV)) for q in INDIV.glob("*/Pusher*.3mf")
                if (q.parent.name, q.name) not in by_legacy)
print(f"\n  {built} built, {canon} in individual/; {same} locks reproduced, "
      f"{moved} moved onto the catalogue,\n  {shared} geometries that the "
      f"planner's key cannot name apart, {len(orphan)} orphaned"
      + (": " + ", ".join(orphan) if orphan else "."))
print("\nPASS" if not fails else "\nFAIL:\n  " + "\n  ".join(fails))
sys.exit(1 if fails else 0)
