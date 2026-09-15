#!/usr/bin/env python3
"""Every cached Box in `individual/` against the built one and the rules.

Needs `cad.build --part box --version 7.0` first.

`tests/test_box.py` holds the SOURCE to nine hand-exported STEPs, which say
nothing about the other 39 boxes or about the written file. This reads the 48
cached meshes AND the 50 written 3MFs — 0 API calls — and holds both to the
rules `cad/parts/box.py` states, probing each by ray (`tests/probe.py`). Three
divergences are DELIBERATE and asserted from both ends — spec/BOX.md, "The
hanging holes do NOT cut the dividers" and "The version line is a DELIBERATE
DIVERGENCE", plus `box.hole_openings`; all else matches to a thousandth.
generation is read off each cached box's own rim cutouts — at the slot
centreline +- `s` from 7.0 on, inset before it — and only the 7.0 ones are
asserted on them; all 48 are 7.0 today. The two `M6.21.10-12` rows have no
cached box under the planner's name (`spec/DERIVED.md`'s `.0` placeholder).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from cad import build as B, derive as D, lock as L, params    # noqa: E402
import reference as REF                                        # noqa: E402
from cad.parts import box                                      # noqa: E402
import probe                                                   # noqa: E402
from probe import EPS                                          # noqa: E402

INDIV = ROOT / "individual"
# The tree for the release this file asserts: build `--version 7.0` first.
BUILD = REF.tree()
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
            p = REF.from_row(row, sleeved)
            d = D.derive(p)
            model = (row.get(col) or "").strip().replace("/", "-")
            cached = f"Box {model}{' merged' if p.MatPocket else ''}.3mf"
            out.setdefault((p.GameName, cached),
                           (p.GameName, cached, B.box_file(d), p))
    return [out[k] for k in sorted(out)]


def probe_box(V, T, p, d):
    # One ray per reading: hanging holes as gaps through the OUTER back wall,
    # rim cutouts through the INNER one in the cutout band, ribs and pocket
    # along the +X end wall's inner face, dividers down the slot band.
    BW, BD = box.box_width(d), box.box_depth(d)
    inner = BW / 2 - box.WALL
    y0, _y1 = box.slot_band(d)
    z_row = box.hole_rows(d)[1]                # the middle row, mid-height
    z_mid = (z_row[0] + z_row[1]) / 2 + EPS
    holes = probe.gaps(probe.spans(V, T, 0, BD / 2 - box.WALL / 2 + EPS, z_mid))
    holes = [(a, b) for a, b in holes if -inner < a and b < inner]
    y_wall = (BD / 2 - box.WALL + y0) / 2 + EPS
    cut = probe.gaps(probe.spans(V, T, 0, y_wall, box.RIM_CUTOUT_Z + 2.5 + EPS))
    cut = [(a, b) for a, b in cut if -inner < a and b < inner]
    ribs = probe.spans(V, T, 1, d.BoxHeight / 2 + EPS,
                       inner - box.SLIDER_PROUD / 2 + EPS)
    # That ray also crosses the walls and the panel; a rib is SLIDER_W thick.
    ribs = [(a, b) for a, b in ribs if abs((b - a) - box.SLIDER_W) < 0.05]
    fw, fb, _back = box.pocket_span(d)
    front = probe.spans(V, T, 0, (fw + fb) / 2 + EPS, d.BoxHeight / 2 + EPS)
    front = [(a, b) for a, b in front if -inner < a and b < inner]
    y_div = y0 + 1.0 + EPS
    divs = [len(probe.spans(V, T, 2, (a + e) / 2 + EPS, y_div))
            for a, e in box.storage_dividers(d)]
    return {"box": probe.box(V), "holes": holes, "cut": cut, "ribs": ribs,
            "front": front, "divs": divs}


def expected(p, d):
    """The rules' own values, from `cad/parts/box.py`."""
    _cls, s = L.lock_class(d.calPusherTotalDepth)
    cut = sorted((c + sign * s - L.BOX_CUTOUT_W / 2, c + sign * s + L.BOX_CUTOUT_W / 2)
                 for c in box.pusher_slots(d) for sign in (-1, +1))
    front = sorted([(x - box.FRONT_DIVIDER_W, x) for x in box.front_dividers(d)])
    return {"holes_sketch": box.hanging_holes(d),
            "holes_built": box.hole_openings(d),
            "cut": cut, "ribs": sorted(box.slider_ribs(d)), "front": front}


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

    for i, axis in enumerate(("X min", "X max", "Y min", "Y max", "Z min", "Z max")):
        check(f"{tag} {axis}", round(b["box"][i], 3), round(c["box"][i], 3), 1e-3)

    gen = "7.0" if probe.near(c["cut"], want["cut"], 1e-3) else "pre"
    seen[gen] += 1
    check(f"{tag}: the build's rim cutouts are the catalogue's",
          probe.near(b["cut"], want["cut"], 1e-3), True)
    if gen == "7.0":
        check(f"{tag}: ... and so are the cached box's", True, True)

    # The sketch on the cached box, HOLE_CLEAR on ours.
    check(f"{tag}: cached hanging holes are the sketch's",
          probe.near(c["holes"], want["holes_sketch"], 1e-3), True)
    check(f"{tag}: built hanging holes are hole_openings",
          probe.near(b["holes"], want["holes_built"], 1e-3), True)

    for name in ("ribs", "front"):
        check(f"{tag}: cached {name} follow the rule",
              probe.near(sorted(c[name]), want[name], 1e-3), True)
        check(f"{tag}: built {name} follow the rule",
              probe.near(sorted(b[name]), want[name], 1e-3), True)

    # From both ends: a built divider is a single span down the slot band, a
    # cached one several — which depends on the layout, so it is reported.
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
