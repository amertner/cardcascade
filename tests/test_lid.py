#!/usr/bin/env python3
"""Check cad/parts/lid.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_lid.py

References in `spec/reference/`, listed in `spec/LID.md`.

Every check runs against the STEP **and** the build wherever it can: a check
that only reads the build cannot tell a wrong probe from a wrong model.
"""
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from build123d import Compound, GeomType, import_step   # noqa: E402
from cad import art, build, marks, params, derive as D, lock as L  # noqa: E402
import reference as REF                                        # noqa: E402
from cad import tables as TB, text as TX                    # noqa: E402
from cad.parts import lid                       # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
REFS = [
    # The only first-riser override, and the only cascade whose Box and Pusher
    # are referenced too, so the lock can be followed across all three.
    ("Dominion 246 Sl", "Lid Dominion 246S with logo.step",
     REF.primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion")),
    # M: three sockets, and unsleeved.
    ("Dominion 244 Un", "Lid Dominion 244U.step",
     REF.primary(4, 4, 21, 10, 0, 10, 0, 0, "Dominion")),
    # R = 9 — past the logo block's eight-riser branch — and a C5 lock.
    ("Dominion 333 Sl", "Lid Dominion 333S.step",
     REF.primary(3, 9, 21, 10, 0, 10, 1, 0, "Dominion")),
    # XS: the narrowest lid in the catalogue, two horizontal slots.
    ("Innovation 130 Un", "Lid Innovation 130U.step",
     REF.primary(2, 5, 15, 10, 0, 10, 0, 0, "Innovation")),
    # Ultimate at scale 1; `lid_logo_big.brep` is lifted from THIS STEP.
    ("Innovation M5.15.15 Un (Ultimate)", "Lid Innovation M5.15.15.45-Un with logo.step",
     REF.primary(4, 5, 15, 15, 0, 15, 0, 0, "Innovation")),
    # A second GAME's card size, and the only reference whose lock is C4.
    ("Compile 126 Sl", "Lid Compile 126S.step",
     REF.primary(3, 5, 7, 7, 0, 7, 1, 0, "Compile")),
]
# 0.810, not 0.800: the pocket is cut z = 0..0.810 and the inlays are 0.810
# prisms sitting 0.010 lower, standing that proud of the underside.
PATTERN_DEPTH = 0.810

fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:52s} {got!r:>26} vs {want!r}")
    if not ok:
        fails.append(label)


def planes(solid, axis, tol=3):
    """{(coord, facing): area} of the faces normal to `axis`."""
    out = {}
    for f in solid.faces():
        if f.geom_type != GeomType.PLANE:
            continue
        n, c = f.normal_at(f.center()), f.center()
        v = [n.X, n.Y, n.Z][axis]
        if abs(v) > 0.999:
            key = (round([c.X, c.Y, c.Z][axis], tol), "+" if v > 0 else "-")
            out[key] = out.get(key, 0.0) + f.area
    return out


def area_at(solid, axis, coord, facing):
    return round(planes(solid, axis).get((round(coord, 3), facing), 0.0), 3)


def radius(face):
    """A cylindrical face's radius, or None: `Face.radius` raises on the
    embossed text's glyph arcs, which are cylinders too."""
    try:
        return face.radius
    except Exception:
        return None


def emboss_lines(solid, z):
    """[(x0, x1, y0, y1)] of the embossed lines, by Y, up the lid."""
    fs = [f for f in solid.faces()
          if f.geom_type == GeomType.PLANE
          and abs(f.center().Z - z) < 1e-6
          and f.normal_at(f.center()).Z > 0.999]
    out = []
    for bb in sorted((f.bounding_box() for f in fs), key=lambda b: b.min.Y):
        if out and bb.min.Y <= out[-1][3] + 0.6:
            o = out[-1]
            out[-1] = [min(o[0], bb.min.X), max(o[1], bb.max.X),
                       min(o[2], bb.min.Y), max(o[3], bb.max.Y)]
        else:
            out.append([bb.min.X, bb.max.X, bb.min.Y, bb.max.Y])
    return [[round(v, 3) for v in line] for line in out]


def baselines(solid, z, n):
    """The `n` baselines: the MODAL bottom edge, not the box floor.

    A descender puts a line's box a millimetre low; clustering by box read
    Compile 1.118 low on BOTH ends — agreeing wrongly is a probe fault.
    """
    bottoms = Counter(round(f.bounding_box().min.Y, 2) for f in solid.faces()
                      if f.geom_type == GeomType.PLANE
                      and abs(f.center().Z - z) < 1e-6
                      and f.normal_at(f.center()).Z > 0.999)
    return sorted(v for v, _n in bottoms.most_common(n))


def socket_walls(solid, x, y0, y1):
    """{X: area} of one socket's X-normal faces — the whole lock."""
    out = {}
    for f in solid.faces():
        if f.geom_type != GeomType.PLANE:
            continue
        n, c = f.normal_at(f.center()), f.center()
        if (abs(n.X) > 0.999 and y0 - 1 < c.Y < y1 + 1
                and x - 6 < c.X < x + 6
                and lid.WALL < c.Z < lid.WALL + lid.SOCKET_H):
            out[round(c.X, 3)] = round(out.get(round(c.X, 3), 0.0) + f.area, 2)
    return out


# The fit rule is PINNED here: every STEP predates `lid.logo_choice` and
# carries its game's DEFAULT mark at the drawn size (the rule itself is
# asserted at the bottom). Innovation's two are pinned BY NAME.
_EXPORTED_WITH = {
    "Lid Innovation 130U.step": ("lid_logo.dxf", 1.0),
    "Lid Innovation M5.15.15.45-Un with logo.step": ("lid_logo_big.brep", 1.0),
}
_PIN_FN = None
_choice = lid.logo_choice
lid.logo_choice = lambda d, variant=TB.LID_OWN: (
    _EXPORTED_WITH.get(_PIN_FN) or (TB.LID_LOGO[d.GameName][None][-1], 1.0))


for name, fn, P in REFS:
    _PIN_FN = fn
    path = STEP_DIR / fn
    print(f"\n=== {name} ===")
    if not path.exists():
        # A missing reference is a FAILURE, not a skip: every STEP is in git.
        print(f"  FAIL — reference {path.name} not present")
        fails.append(f"{name}: reference {path.name} missing")
        continue
    d = D.derive(P)
    # The STEP carries the inlays as separate solids; the body is the big one.
    solids = import_step(str(path)).solids()
    ref = max(solids, key=lambda s: s.volume)
    mine = lid.build(D.derive(P))
    rb, mb = ref.bounding_box(), mine.bounding_box()
    print(f"  reference {len(solids)} solids, body {len(ref.faces())} faces, "
          f"{ref.volume:.3f} mm3;  build {len(mine.faces())} faces, "
          f"{mine.volume:.3f} mm3")

    check("width  = #BoxWidth + 4.600", round(rb.size.X, 3),
          round(lid.lid_width(d), 3), 1e-3)
    check("depth  = calLidDepth", round(rb.size.Y, 3),
          round(d.calLidDepth, 3), 1e-3)
    check("height = LidHeight", round(rb.size.Z, 3), round(d.LidHeight, 3), 1e-3)
    check("build envelope = the reference's",
          [round(v, 3) for v in (mb.size.X, mb.size.Y, mb.size.Z)],
          [round(v, 3) for v in (rb.size.X, rb.size.Y, rb.size.Z)])
    check("centred on X and Y, floor at z = 0",
          [round(v, 3) for v in (rb.min.X + rb.max.X, rb.min.Y + rb.max.Y,
                                 rb.min.Z)], [0.0, 0.0, 0.0])

    W = lid.lid_width(d) / 2
    DD = lid.lid_depth(d) / 2
    for who, solid in (("STEP ", ref), ("build", mine)):
        # A wall's own area is what tells it from its neighbour.
        check(f"{who}: outer end walls at +-lid_width/2",
              [area_at(solid, 0, -W, "-") > 0, area_at(solid, 0, W, "+") > 0],
              [True, True])
        check(f"{who}: inner end walls WALL in",
              [area_at(solid, 0, -(W - lid.WALL), "+") > 0,
               area_at(solid, 0, W - lid.WALL, "-") > 0], [True, True])
        check(f"{who}: outer side walls at +-calLidDepth/2",
              [area_at(solid, 1, -DD, "-") > 0, area_at(solid, 1, DD, "+") > 0],
              [True, True])
        check(f"{who}: rim = the wall band, less the outer rounds",
              area_at(solid, 2, d.LidHeight, "+"),
              round((2 * W - 2 * lid.OUTER_ROUND) * (2 * DD - 2 * lid.OUTER_ROUND)
                    - (2 * W - 2 * lid.WALL) * (2 * DD - 2 * lid.WALL), 3), 1e-3)

    y0, y1 = lid.socket_span(d)
    cls, s = L.lock_class(d.calPusherTotalDepth)
    check(f"lock class from calPusherTotalDepth {d.calPusherTotalDepth:.2f}",
          cls, cls)
    check("socket span = calPusherTotalDepth - 0.400", round(y1 - y0, 3),
          round(d.calPusherTotalDepth - L.LID_SOCKET_CLEARANCE, 3), 1e-6)
    check("socket back edge SOCKET_BACK in from the lid's back",
          round(d.calLidDepth / 2 - y1, 3), round(lid.SOCKET_BACK, 3), 1e-6)
    side = round(lid.SOCKET_H * (y1 - y0), 2)     # a socket block's own side

    # Pinned to 7.0 (`tests/reference.py`), Onshape's size rule; 7.1's
    # one-per-pusher is a RELEASE change, asserted in test_revisions.py.
    want_c = lid.socket_centres(d)
    for who, solid in (("STEP ", ref), ("build", mine)):
        xs = sorted(k[0] for k, a in planes(solid, 0).items()
                    if abs(a - side) < 1e-2)
        check(f"{who}: one block per socket, calFootTotalWidth wide", len(xs),
              2 * len(want_c))
        if len(xs) != 2 * len(want_c):
            continue
        check(f"{who}: socket centres",
              [round((a + b) / 2, 3) for a, b in zip(xs[0::2], xs[1::2])],
              [round(x, 3) for x in want_c])
        check(f"{who}: block width",
              sorted({round(b - a, 3) for a, b in zip(xs[0::2], xs[1::2])}),
              [round(d.calFootTotalWidth, 3)])
        rib = lid.KEY_RIB_LEN if L.has_notch(s) else 0.0
        want_chan = round(lid.SOCKET_H * ((y1 - y0) - rib), 2)
        for x in want_c:
            got = socket_walls(solid, x, y0, y1)
            want = {
                round(x - d.calFootTotalWidth / 2, 3): side,
                round(x - L.LID_CHANNEL_W / 2 - L.LID_RECESS_STEP, 3):
                    round(2 * L.LID_RECESS_LEN * lid.SOCKET_H, 2),
                round(x - L.LID_CHANNEL_W / 2, 3):
                    round(want_chan - 2 * L.LID_RECESS_LEN * lid.SOCKET_H, 2),
                round(x + L.LID_CHANNEL_W / 2, 3): want_chan,
                round(x + d.calFootTotalWidth / 2, 3): side,
            }
            ok = (sorted(got) == sorted(want)
                  and all(abs(got[k] - want[k]) < 0.02 for k in want))
            check(f"{who}: socket at {x:+8.3f} — channel, recesses, rib",
                  ok if ok else got, True if ok else want)

    # The recesses carry `s`, and both are cut into the -X wall only.
    for who, solid in (("STEP ", ref), ("build", mine)):
        end = round(L.LID_RECESS_STEP * lid.SOCKET_H, 3)
        # Deduped: every socket has its recesses at the same two Y.
        ys = sorted({round(f.center().Y, 3) for f in solid.faces()
                     if f.geom_type == GeomType.PLANE
                     and abs(f.normal_at(f.center()).Y) > 0.999
                     and abs(f.area - end) < 1e-3
                     and lid.WALL < f.center().Z < lid.WALL + lid.SOCKET_H})
        centres = sorted(round((a + b) / 2, 3) for a, b in zip(ys[0::2], ys[1::2]))
        check(f"{who}: tab recesses at the socket centreline +- s ({cls})",
              [round(c - (y0 + y1) / 2, 3) for c in centres],
              [-round(s, 3), round(s, 3)])

    z0, z1 = lid.groove_span(d)
    flat = round(2 * lid.GROOVE_LEN * (lid.GROOVE_DEPTH - lid.GROOVE_CHAMFER), 3)
    for who, solid in (("STEP ", ref), ("build", mine)):
        check(f"{who}: groove floor z0 = WALL + BoxHeight - 90",
              area_at(solid, 2, z0, "+"), flat, 1e-3)
        check(f"{who}: groove roof GROOVE_HEIGHT above it",
              area_at(solid, 2, z1, "-"), flat, 1e-3)
        # The floor is INTO the wall, so it faces back at the cavity.
        deep = round(W - lid.WALL + lid.GROOVE_DEPTH, 3)
        check(f"{who}: groove floor GROOVE_DEPTH into the wall",
              [area_at(solid, 0, -deep, "+"), area_at(solid, 0, deep, "-")],
              [round(lid.GROOVE_LEN * (lid.GROOVE_HEIGHT
                                       - 2 * lid.GROOVE_CHAMFER), 3)] * 2)
        ch = [f for f in solid.faces()
              if f.geom_type == GeomType.PLANE
              and abs(abs(f.normal_at(f.center()).X) - 2 ** -0.5) < 1e-3]
        check(f"{who}: 4 groove chamfers, GROOVE_CHAMFER square",
              [len(ch), sorted({round(f.area, 3) for f in ch})],
              [4, [round(lid.GROOVE_LEN * lid.GROOVE_CHAMFER * 2 ** 0.5, 3)]])

    for who, solid in (("STEP ", ref), ("build", mine)):
        cyl = [f for f in solid.faces() if f.geom_type == GeomType.CYLINDER
               and radius(f) is not None
               and abs(radius(f) - lid.OUTER_ROUND) < 1e-9]
        sph = [f for f in solid.faces() if f.geom_type == GeomType.SPHERE]
        check(f"{who}: 12 outer edges rounded OUTER_ROUND", len(cyl), 12)
        check(f"{who}: 8 corner blends, each an eighth of a sphere",
              [len(sph), sorted({round(f.area, 4) for f in sph})],
              [8, [round(math.pi * lid.OUTER_ROUND ** 2 / 2, 4)]])

    # BASELINES, not ink widths: Onshape's advance runs 0.31 % wider than the
    # font file's, a divergence cad/README.md records.
    for who, solid in (("STEP ", ref), ("build", mine)):
        check(f"{who}: the text stands {lid.TEXT_PROUD} proud of the floor",
              area_at(solid, 2, lid.WALL + lid.TEXT_PROUD, "+") > 0, True)
        check(f"{who}: the logo stands {lid.LOGO_PROUD} proud",
              area_at(solid, 2, lid.WALL + lid.LOGO_PROUD, "+") > 0, True)
    text_gap = 2.0 if P.HorizontalSlots > 2 else 15.0
    base = round(d.calLidDepth / 2 - lid.WALL - D.FootDistanceFromWall
                 - text_gap - lid.CAP_LINE, 3)
    want = [round(base - 5.5 - 5.0, 3), round(base - 5.5, 3), base]
    for who, solid in (("STEP ", ref), ("build", mine)):
        lines = emboss_lines(solid, lid.WALL + lid.TEXT_PROUD)
        got = baselines(solid, lid.WALL + lid.TEXT_PROUD, 3)
        check(f"{who}: the three lines' baselines, 5.500 and 5.000 apart",
              [b for b in got if b in want], want)
        # Only the three lines: the version is right-aligned on the LOGO.
        right = max(line[1] for line in lines if round(line[2], 3) in want)
        check(f"{who}: text block right edge = text_offset in from the wall",
              right < W - lid.WALL - lid.text_offset(d) + 1e-6, True)
    # The logo: its box, its own two lines, and the staircase.
    size = lid.logo_size(d)
    left = round(-(W - lid.WALL) + lid.logo_offset(d), 3)
    logo_base = round(d.calLidDepth / 2 - lid.WALL - D.FootDistanceFromWall
                      - lid.LOGO_DROP - TX.CAP * size, 3)
    for who, solid in (("STEP ", ref), ("build", mine)):
        logo = emboss_lines(solid, lid.WALL + lid.LOGO_PROUD)
        check(f"{who}: ProductName's box starts at logo_offset",
              round(logo[-1][0], 1), round(left + 0.056 * size, 1), 0.15)
        check(f"{who}: ProductName's baseline = FootDistanceFromWall + 1 down",
              round(logo[-1][2], 1), round(logo_base, 1), 0.06)
    # The staircase is the rest of the 0.600 group; its area is closed form.
    if P.HorizontalSlots > 2:
        top = logo_base - 2 * TX.CAP * size / 3
        slope = top - lid.socket_span(d)[0]
        for who, solid in (("STEP ", ref), ("build", mine)):
            stair = max((f for f in solid.faces()
                         if f.geom_type == GeomType.PLANE
                         and abs(f.center().Z - lid.WALL - lid.LOGO_PROUD) < 1e-6
                         and f.normal_at(f.center()).Z > 0.999), key=lambda f: f.area)
            bb = stair.bounding_box()
            check(f"{who}: staircase, {P.RisingSliders} steps",
                  [len(stair.edges()), round(bb.size.X, 2)],
                  [2 * P.RisingSliders + 2, round(lid.logo_width(d), 2)])
            # Its HEIGHT carries the 0.31 % cap divergence (31.3 vs 31.2).
            check(f"{who}: staircase height = the slope",
                  round(bb.size.Y, 3), round(slope, 3), 0.15)
            # Against its OWN box, so the 0.31 % cancels: R equal steps fill
            # (R + 1) / 2R of the rectangle they descend.
            check(f"{who}: staircase area = R steps of LogoStepWidth x Height",
                  round(stair.area, 2),
                  round(bb.size.X * bb.size.Y
                        * (P.RisingSliders + 1) / (2 * P.RisingSliders), 2),
                  0.02)
    else:
        for who, solid in (("STEP ", ref), ("build", mine)):
            check(f"{who}: XS carries the word alone, no staircase",
                  len(emboss_lines(solid, lid.WALL + lid.LOGO_PROUD)), 1)

    # Pocket and inlay come off ONE sketch, so they are asserted together.
    ref_inlays = [x for x in solids if x is not ref]
    mine_inlays = lid.inlays(D.derive(P))
    check("the reference carries inlay solids", len(ref_inlays) > 0, True)
    check("one inlay per artwork region", len(mine_inlays), len(ref_inlays))
    if mine_inlays:
        rv = sum(x.volume for x in ref_inlays)
        mv = sum(x.volume for x in mine_inlays)
        # 0.1 %, the DXF round trip: Dominion is all straight lines and
        # matches to 0.000; Innovation's 361 arcs land at 0.09 %.
        check("inlay volume", round(mv, 3), round(rv, 3), rv * 1e-3)
        # ORIENTATION, from both ends — printed 7.1 lids settled it
        # (spec/LID.md). Volume and footprint miss a half turn; this can.
        def regions(inlays, turn):
            """Each region's (x, y, volume), turned about the lid's centre."""
            s = -1 if turn else 1
            return [(s * q.center().X, s * q.center().Y, q.volume)
                    for q in inlays]

        def matched(a, b):
            """Every region of `a` has one of `b` within 0.1 mm and 3 % —
            loose for the rebuilt Innovation regions, tight against a turn."""
            return all(any(abs(x - u) < 0.1 and abs(y - v) < 0.1
                           and abs(w - q) < 0.03 * w for u, v, q in b)
                       for x, y, w in a)
        turned = P.GameName in TB.LID_LOGO_TURNED
        as_drawn, half_turn = " as drawn", " turned a half turn"
        check(f"the build's regions are the STEP's"
              f"{half_turn if turned else as_drawn}",
              matched(regions(ref_inlays, turned), regions(mine_inlays, False)),
              True)
        check(f"... and not the STEP's{as_drawn if turned else half_turn}",
              matched(regions(ref_inlays, not turned),
                      regions(mine_inlays, False)), False)
        rb = Compound(children=ref_inlays).bounding_box()
        mb = Compound(children=mine_inlays).bounding_box()
        want = ((-rb.max.X, -rb.min.X, -rb.max.Y, -rb.min.Y) if turned
                else (rb.min.X, rb.max.X, rb.min.Y, rb.max.Y))
        check(f"inlay footprint{' (turned)' if turned else ''}",
              [round(v, 3) for v in (mb.min.X, mb.max.X, mb.min.Y, mb.max.Y)],
              [round(v, 3) for v in want])
        # The one number that says the two features agree.
        check("inlays sit PATTERN_PROUD below the underside",
              [round(mb.min.Z, 3), round(mb.max.Z, 3)],
              [round(-lid.PATTERN_PROUD, 3),
               round(lid.PATTERN_DEPTH - lid.PATTERN_PROUD, 3)])
        check("STEP: and the reference's do too",
              [round(rb.min.Z, 3), round(rb.max.Z, 3)],
              [round(-lid.PATTERN_PROUD, 3),
               round(lid.PATTERN_DEPTH - lid.PATTERN_PROUD, 3)])
        # The pocket, from the body's own faces: its ceiling faces DOWN.
        for who, solid in (("STEP ", ref), ("build", mine)):
            check(f"{who}: the pocket is PATTERN_DEPTH deep",
                  area_at(solid, 2, lid.PATTERN_DEPTH, "-") > 0, True)
        check("pocket area", area_at(mine, 2, lid.PATTERN_DEPTH, "-"),
              area_at(ref, 2, lid.PATTERN_DEPTH, "-"),
              area_at(ref, 2, lid.PATTERN_DEPTH, "-") * 1e-3)

    # Nothing else may differ: 1 mm3 in 6e4, the advance and the DXF trip.
    check("reference - build, the whole body", round(ref.volume - mine.volume, 2),
          0.0, 1.0)

# `Lid Dominion 246S.step` is the one export WITHOUT the logo meshes: its body
# is NOT pocketed, which is what makes the pocket measurable on its own.
print("\n=== the export pair ===")
plain = STEP_DIR / "Lid Dominion 246S.step"
if not plain.exists():
    print(f"  FAIL — reference {plain.name} not present")
    fails.append(f"export pair: reference {plain.name} missing")
else:
    P = REFS[0][2]
    solids = import_step(str(plain)).solids()
    body = max(solids, key=lambda s: s.volume)
    inlays = [s for s in solids if s is not body]
    check("the plain export has the inlay solids", len(inlays), 6)
    check("but its body is NOT pocketed",
          area_at(body, 2, lid.PATTERN_DEPTH, "-"), 0.0)
    check("so it stands proud of the with-logo export by the pocket",
          round(body.volume - sum(x.volume for x in inlays), 2),
          round(lid.build(D.derive(P)).volume, 2), 1.0)

# The pin comes off: `lid.logo_choice` is `cad/` policy, not Onshape
# (spec/LID.md, "Sizing the mark"). One lid per branch, then two invariants.
lid.logo_choice = _choice
print("\n=== the fit rule ===")

for model, want_file, want_scale in [
        # drawn to this lid and still down 2.3 % for LOGO_CLEAR; 0.977
        # through 7.2e, 0.945 from 7.2f's shallower lid (`rev.shorter_box`)
        ("S4.16.10.32-Un", "lid_logo.dxf", 0.945),
        # too deep for the mark as drawn: the width fraction sizes it
        ("L8.50.10.62-Sl", "lid_logo.dxf", 1.655),
        # shallower than drawn, where the round clamp bites hardest
        # (spec/LID.md, "per SIDE"): 0.855 through 7.2e, 0.821 from 7.2f
        ("S4.7.7.20-Un", "lid_logo.dxf", 0.821),
        # Ultimate at its two published sizes; 1.211 not the drawn ladder's
        # 1.210, because the generated mark's 0.600 stroke does not scale
        ("S5.15.15.45-Un", "@innovation-ultimate-big", 1.000),
        ("S5.10.10.32-Un", "@innovation-ultimate", 1.211),
        # the plain mark: drawn size on the XS lid, the fraction on the S
        ("XS5.15.10.32-Un", "@innovation-plain", 1.000),
        ("S3.15.10.20-Un", "@innovation-plain", 1.211)]:
    hit = [(pp, dd) for _f, fn, pp, _alt in build.lid_catalogue()
           for dd in [D.derive(pp)] if fn == f"Lid {model}.3mf"]
    if not hit:
        check(f"{model}: in the catalogue", False, True)
        continue
    pp, dd = hit[0]
    got_file, got_scale = lid.logo_choice(dd)
    check(f"{model}: drawing", got_file, want_file)
    check(f"{model}: scale", round(got_scale, 3), want_scale, 1e-3)

# Two invariants over every lid: a pocket into an outer round breaks the rim,
# and a published mark is never shrunk except to fit. Per SIDE on the INK, not
# a size against the flat floor — Compile's smallest lid cut 0.561 into its
# round with its height exactly filling it (`marks.reach`).


def slack(game, name, d, n):
    """Spare on the mark's tightest side, against LOGO_CLEAR."""
    lw, ld = lid.logo_limit(d)
    return min(lim - (a * n + b) for lim, (a, b)
               in zip((lw, lw, ld, ld), marks.reach(game, name)))


worst_clear, worst_shrink = None, []
for _folder, fn, pp, variant in build.lid_catalogue():
    if variant == TB.LID_UNMARKED:
        continue        # no mark by design (7.2b); nothing to fit or clear
    dd = D.derive(pp)
    name, scale = lid.logo_choice(dd, variant)
    if not name:
        check(f"{fn}: has artwork", False, True)
        continue
    got = slack(pp.GameName, name, dd, scale)
    if worst_clear is None or got < worst_clear[0]:
        worst_clear = (got, fn)
    if scale < 1.0 and slack(pp.GameName, name, dd, 1.0) >= -1e-9:
        # only where the mark genuinely does not clear at its drawn size
        worst_shrink.append(fn)
check(f"every mark keeps {lid.LOGO_CLEAR} clear of the outer rounds",
      worst_clear[0] >= -1e-9, True)
print(f"       tightest is {worst_clear[1]}, "
      f"{worst_clear[0] + lid.LOGO_CLEAR:.3f} mm from the round")
check("no mark is shrunk that did not have to be", worst_shrink, [])

# `cad/marks.py` BUILDS the plain mark so its 0.600 strokes hold at any size;
# the two drawings it replaced are the reference (spec/LID.md).
print("\n=== the generated Innovation mark ===")
for n, ref in ((1.0, "lid_logo_plain.dxf"), (1.6, "lid_logo_plain_big.dxf")):
    drawn = art.logo("Innovation", ref)
    built = marks.faces("Innovation", "@innovation-plain", n)
    if not drawn:
        check(f"n={n}: {ref} present", False, True)
        continue

    def boxes(faces):
        whole = Compound(children=list(faces)).bounding_box()
        cx = (whole.min.X + whole.max.X) / 2
        cy = (whole.min.Y + whole.max.Y) / 2
        return sorted((f.bounding_box().min.X - cx, f.bounding_box().max.X - cx,
                       f.bounding_box().min.Y - cy, f.bounding_box().max.Y - cy,
                       f.area, len(f.wires())) for f in faces)

    b, l = boxes(built), boxes(drawn)
    check(f"n={n}: one region per drawn region", len(b), len(l))
    if len(b) != len(l):
        continue
    check(f"n={n}: the same holes", [x[5] for x in b], [x[5] for x in l])
    check(f"n={n}: total area", round(sum(x[4] for x in b), 3),
          round(sum(x[4] for x in l), 3), sum(x[4] for x in l) * 2e-3)
    worst = max(max(abs(x[i] - y[i]) for i in range(4)) for x, y in zip(b, l))
    # The letters land inside 0.035; the HAND-PLACED star is where the two
    # drawings disagree with each other by 0.11, which is the tolerance.
    check(f"n={n}: worst region edge", round(worst, 3), 0.0, 0.12)
    print(f"       worst region edge {worst:.4f} mm over {len(b)} regions")

# A deliberate divergence from the crop, both ends: the crop is BOX-centred,
# the build WORD-centred (spec/LID.md, "The plain mark sits on its WORD").
for n, want in ((1.0, 1.493), (1.6, 2.209)):
    built = Compound(children=list(
        marks.faces("Innovation", "@innovation-plain", n))).bounding_box()
    ref = "lid_logo_plain.dxf" if n == 1.0 else "lid_logo_plain_big.dxf"
    drawn = Compound(children=list(art.logo("Innovation", ref))).bounding_box()
    bc = (built.min.Y + built.max.Y) / 2
    dc = (drawn.min.Y + drawn.max.Y) / 2
    # Same SHAPE to 0.12 above, so the box-centre difference IS the rise.
    check(f"n={n}: the build stands the same word about {want} higher than "
          f"the crop does", round(bc - dc, 3), want, 0.2)
    check(f"n={n}: and the crop's own box is on the lid's centre — box-datum",
          round(dc, 3), 0.0, 0.2)
    # The datum itself, from the font metrics: the same statement as
    # "baseline to cap is on the origin", and it fails if `_centre` reverts.
    raw_faces, base, letter_I = marks._wordmark(round(marks.NOMINAL_SIZE * n, 6))
    raw = Compound(children=list(raw_faces)).bounding_box()
    gap = (raw.min.Y + raw.max.Y) / 2 - (base + letter_I.bounding_box().max.Y) / 2
    check(f"n={n}: it is the WORD on the origin, not the box", round(bc, 4),
          round(gap, 4), 1e-3)

# The strokes are the point: they must NOT scale.
w1, _ = marks.extent("Innovation", "@innovation-plain", 1.0)
w2, _ = marks.extent("Innovation", "@innovation-plain", 2.0)
check("the strokes do not scale", round(2 * w1 - w2, 3),
      round(marks.LINE_WIDTH, 3), 1e-3)

# Against `lid_logo_big.brep` all 31 regions must land; against the small
# drawing all but the fan under the U, which the corrected sketch moved — and
# the fan MUST differ there, or that drawing is not the one this says it is.
print("\n=== the generated Innovation Ultimate mark ===")
for n, ref, fan_moved in ((1.6, "lid_logo_big.brep", False),
                          (1.0, "lid_logo.dxf", True)):
    drawn = art.logo("Innovation", ref)
    built = marks.faces("Innovation", "@innovation-ultimate", n)
    if not drawn:
        check(f"Ultimate n={n}: {ref} present", False, True)
        continue
    b, l = boxes(built), boxes(drawn)
    check(f"Ultimate n={n}: one region per drawn region", len(b), len(l))
    if len(b) != len(l):
        continue
    # pair each built region with the nearest drawn one by centre
    pairs, free = [], list(range(len(l)))
    for x in b:
        i = min(free, key=lambda i: abs((x[0] + x[1]) - (l[i][0] + l[i][1]))
                + abs((x[2] + x[3]) - (l[i][2] + l[i][3])))
        free.remove(i)
        pairs.append((x, l[i]))
    check(f"Ultimate n={n}: the same holes", [x[5] for x, _y in pairs],
          [y[5] for _x, y in pairs])
    fan_area = 0.625 * 1.250 * n * n
    fan = [(x, y) for x, y in pairs if abs(x[4] - fan_area) < 0.01]
    rest = [(x, y) for x, y in pairs if abs(x[4] - fan_area) >= 0.01]
    check(f"Ultimate n={n}: five fan boxes", len(fan), 5)
    worst = max(max(abs(x[i] - y[i]) for i in range(4)) for x, y in rest)
    check(f"Ultimate n={n}: worst region edge outside the fan",
          round(worst, 3), 0.0, 0.035)
    worst_fan = max(max(abs(x[i] - y[i]) for i in range(4)) for x, y in fan)
    if fan_moved:
        check(f"Ultimate n={n}: the fan is where the OLD sketch had it",
              worst_fan > 0.3, True)
    else:
        check(f"Ultimate n={n}: the fan is where the sketch has it",
              round(worst_fan, 3), 0.0, 0.035)
    print(f"       worst region edge {worst:.4f} mm outside the fan, "
          f"{worst_fan:.4f} on it, over {len(b)} regions")

print(f"\n{'FAILED: ' + ', '.join(fails) if fails else 'all checks passed'}")
sys.exit(1 if fails else 0)
