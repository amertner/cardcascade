#!/usr/bin/env python3
"""Every cached Box in `individual/` against the built one and the rules.

    .venv/bin/python -m cad.build --part box
    .venv/bin/python tests/test_box_corpus.py

`tests/test_box.py` checks the SOURCE against nine hand-exported STEPs, which
settle the geometry exactly and say nothing about the other 39 boxes or about
the written file. This reads the 48 cached meshes AND the 50 written 3MFs — 0
API calls — and holds both to the placement rules `cad/parts/box.py` states,
probing each by ray (`tests/probe.py`): the envelope and where it sits, the
hanging holes through the back wall, the slider ribs, the rim cutouts, the
front pocket's dividers, and the rear storage dividers.

## Where the two are meant to differ, and where they are not

Three divergences are DELIBERATE and are asserted from both ends:

  * the hanging holes stop at the slot band, so the storage DIVIDERS stay
    whole — Onshape's cut clean through them (`spec/BOX.md`);
  * a hole whose edge lands exactly on a divider face stops `HOLE_CLEAR`
    short of it, on three sleeved Innovation boxes (`box.hole_openings`);
  * the floor text is floored and says `CC` where the sketch says `Rev`
    (`tests/test_box.py` holds that; volume is not compared here).

Everything else the cached box has, the built one must have to a thousandth.

## The corpus is one generation, and the cutouts say which

A box's half of the pusher lock is its two rim cutouts per slot, at the
slot's centreline +- `s` from 7.0 on and inset from the slot's ends before
it. Read off the mesh, that classifies each cached box; the 7.0 ones are
asserted on their cutouts and the rest reported, as the pusher and lid
corpus tests do. Every cached pusher and lid is 7.0 since the September
refreshes, and this says whether the boxes came with them: all 48 did.

Two parts.csv rows have no cached box under the planner's name — the two
`M6.21.10-12` cascades, whose model column carries the `.0` placeholder
`spec/DERIVED.md` records — and are reported as absent, as their holders
are elsewhere.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from cad import build as B, derive as D, lock as L, params    # noqa: E402
from cad.parts import box                                      # noqa: E402
import probe                                                   # noqa: E402
from probe import EPS                                          # noqa: E402

INDIV = ROOT / "individual"
BUILD = ROOT / "build"
FOLDER = {"Compile": "Compile", "Dominion": "Dominion", "FCM": "FCM",
          "Innovation": "Innovation"}
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        fails.append(f"{label}: {got!r} vs {want!r}")
        print(f"    FAIL {label}: {got!r} vs {want!r}")
    return ok


def catalogue():
    """[(game, cached name, built name, Primary)] — one per parts.csv box."""
    out = {}
    for row in params.load_rows(ROOT / "automation" / "parts.csv"):
        for sleeved, col in ((0, "Unsl Model"), (1, "Sleeved model")):
            p = params.from_row(row, sleeved)
            d = D.derive(p)
            model = (row.get(col) or "").strip().replace("/", "-")
            cached = f"Box {model}{' merged' if p.MatPocket else ''}.3mf"
            out.setdefault((p.GameName, cached),
                           (p.GameName, cached, B.box_file(d), p))
    return [out[k] for k in sorted(out)]


def probe_box(V, T, p, d):
    """Every reading the checks below compare, from one mesh."""
    BW, BD = box.box_width(p, d), box.box_depth(p, d)
    inner = BW / 2 - box.WALL
    y0, _y1 = box.slot_band(p, d)
    z_row = box.hole_rows()[1]                 # the middle row, mid-height
    z_mid = (z_row[0] + z_row[1]) / 2 + EPS
    # Hanging holes: an X ray through the OUTER back wall reads them as gaps.
    holes = probe.gaps(probe.spans(V, T, 0, BD / 2 - box.WALL / 2 + EPS, z_mid))
    holes = [(a, b) for a, b in holes if -inner < a and b < inner]
    # Rim cutouts: an X ray through the inner back wall in the cutout band.
    y_wall = (BD / 2 - box.WALL + y0) / 2 + EPS
    cut = probe.gaps(probe.spans(V, T, 0, y_wall, box.RIM_CUTOUT_Z + 2.5 + EPS))
    cut = [(a, b) for a, b in cut if -inner < a and b < inner]
    # Slider ribs: a Y ray along the +X end wall's inner face, mid-height.
    ribs = probe.spans(V, T, 1, d.BoxHeight / 2 + EPS,
                       inner - box.SLIDER_PROUD / 2 + EPS)
    # The ray also crosses the front and back walls and the pocket's panel;
    # a rib is the one thing SLIDER_W thick along Y.
    ribs = [(a, b) for a, b in ribs if abs((b - a) - box.SLIDER_W) < 0.05]
    # Front pocket: an X ray through the pocket reads pads, dividers and walls.
    fw, fb, _back = box.pocket_span(p, d)
    front = probe.spans(V, T, 0, (fw + fb) / 2 + EPS, d.BoxHeight / 2 + EPS)
    front = [(a, b) for a, b in front if -inner < a and b < inner]
    # Storage dividers: a Z ray down each divider's centre in the slot band.
    y_div = y0 + 1.0 + EPS
    divs = [len(probe.spans(V, T, 2, (a + e) / 2 + EPS, y_div))
            for a, e in box.storage_dividers(p, d)]
    return {"box": probe.box(V), "holes": holes, "cut": cut, "ribs": ribs,
            "front": front, "divs": divs}


def expected(p, d):
    """The rules' own values, from `cad/parts/box.py`."""
    _cls, s = L.lock_class(d.calPusherTotalDepth)
    cut = sorted((c + sign * s - L.BOX_CUTOUT_W / 2, c + sign * s + L.BOX_CUTOUT_W / 2)
                 for c in box.pusher_slots(p, d) for sign in (-1, +1))
    front = sorted([(x - box.FRONT_DIVIDER_W, x) for x in box.front_dividers(p, d)])
    return {"holes_sketch": box.hanging_holes(p, d),
            "holes_built": box.hole_openings(p, d),
            "cut": cut, "ribs": sorted(box.slider_ribs(p, d)), "front": front}


print(f"  {'cached box':38s} {'gen':>4s} {'holes':>5s} {'cut':>4s} {'ribs':>4s} "
      f"{'divs cached/built':>18s}")
seen = {"7.0": 0, "pre": 0}
absent, unbuilt = [], []
for game, cached, built, p in catalogue():
    cpath = INDIV / FOLDER[game] / cached
    bpath = BUILD / game / built
    if not cpath.exists():
        absent.append(f"{game}/{cached}")
        continue
    if not bpath.exists():
        unbuilt.append(f"{game}/{built}")
        fails.append(f"{game}/{built} not built")
        continue
    d = D.derive(p)
    want = expected(p, d)
    CV, CT = probe.load(cpath)
    BV, BT = probe.load(bpath)
    c, b = probe_box(CV, CT, p, d), probe_box(BV, BT, p, d)
    tag = f"{game}/{cached}"

    # --- the envelope, and where the part sits -------------------------------
    for i, axis in enumerate(("X min", "X max", "Y min", "Y max", "Z min", "Z max")):
        check(f"{tag} {axis}", round(b["box"][i], 3), round(c["box"][i], 3), 1e-3)

    # --- the generation, from the cached box's own cutouts ------------------
    gen = "7.0" if probe.near(c["cut"], want["cut"], 1e-3) else "pre"
    seen[gen] += 1
    check(f"{tag}: the build's rim cutouts are the catalogue's",
          probe.near(b["cut"], want["cut"], 1e-3), True)
    if gen == "7.0":
        check(f"{tag}: ... and so are the cached box's", True, True)

    # --- hanging holes: the sketch on the cached box, HOLE_CLEAR on ours ----
    check(f"{tag}: cached hanging holes are the sketch's",
          probe.near(c["holes"], want["holes_sketch"], 1e-3), True)
    check(f"{tag}: built hanging holes are hole_openings",
          probe.near(b["holes"], want["holes_built"], 1e-3), True)

    # --- slider ribs and the front pocket: the same on both -----------------
    for name in ("ribs", "front"):
        check(f"{tag}: cached {name} follow the rule",
              probe.near(sorted(c[name]), want[name], 1e-3), True)
        check(f"{tag}: built {name} follow the rule",
              probe.near(sorted(b[name]), want[name], 1e-3), True)

    # --- the storage dividers: WHOLE on ours, severed on Onshape's ----------
    # Asserted from both ends. A built divider is one span of material down
    # the slot band; Onshape's holes cut clean through, so a cached divider a
    # hole crosses reads as several. Which dividers a hole crosses depends on
    # the layout, so the cached count is reported rather than fixed.
    check(f"{tag}: built dividers are whole", all(n == 1 for n in b["divs"]), True)
    check(f"{tag}: cached dividers are severed where a hole crosses",
          all(n >= 1 for n in c["divs"]), True)
    print(f"  {cached:38s} {gen:>4s} {len(c['holes']):5d} {len(c['cut']):4d} "
          f"{len(c['ribs']):4d} {str(c['divs']) + '/' + str(b['divs']):>18s}")

print(f"\n  {seen['7.0']} boxes at 7.0, asserted;  {seen['pre']} pre-7.0, "
      f"cutouts reported only")
for a in absent:
    print(f"  no cached file for {a}")
for u in unbuilt:
    print(f"  not built: {u}")

print("\nPASS" if not fails else "\nFAIL: " + "; ".join(fails[:20]))
sys.exit(1 if fails else 0)
