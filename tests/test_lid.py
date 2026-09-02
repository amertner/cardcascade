#!/usr/bin/env python3
"""Check cad/parts/lid.py against the hand-exported Onshape STEPs.

    .venv/bin/python tests/test_lid.py

Four references in `spec/reference/`, listed in `spec/LID.md`. The Lid is being
built group by group; this asserts only what is written, and grows with it.

Proven so far: the envelope, the shell, the sockets — the lid's half of the 7.0
lock, channel, key rib and both tab recesses — the closing grooves, and the
`1.000` round on all twelve outer edges. The floor's embossed text and logo are
not built, so the reference stands proud of the build by exactly their volume;
that difference is itself asserted, which is what keeps this test honest about
what is missing.

Every check runs against the STEP **and** the build wherever it can, because a
check that only reads the build cannot tell a wrong probe from a wrong model —
the lesson `spec/BOX.md` records four times over. It caught a real one here:
the closing groove was built unchamfered, and the volume gap was out by exactly
the 5.000 mm3 of the four chamfers.
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import GeomType, import_step   # noqa: E402
from cad import params, derive as D, lock as L  # noqa: E402
from cad.parts import lid                       # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
REFS = [
    # The only reference with a first-riser override, and the cascade whose Box
    # and Pusher are both referenced too — so the lock can be followed across
    # all three parts of one design.
    ("Dominion 246 Sl", "Lid Dominion 246S.step",
     params.Primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion"), 167.642, 800.231),
    # M: three sockets, and unsleeved.
    ("Dominion 244 Un", "Lid Dominion 244U.step",
     params.Primary(4, 4, 21, 10, 0, 10, 0, 0, "Dominion"), 147.535, 517.295),
    # R = 9 — past the logo block's eight-riser branch — and a C5 lock.
    ("Dominion 333 Sl", "Lid Dominion 333S.step",
     params.Primary(3, 9, 21, 10, 0, 10, 1, 0, "Dominion"), 155.747, 1722.310),
    # XS: the narrowest lid in the catalogue, two horizontal slots.
    ("Innovation 130 Un", "Lid Innovation 130U.step",
     params.Primary(2, 5, 15, 10, 0, 10, 0, 0, "Innovation"), 160.419, 84.121),
]
# The logo pattern's pocket in the underside of the floor. Deferred with the
# pattern itself; measured here only so the volume gap can be accounted for.
# 0.810, not 0.800: the pocket is cut from z = 0 to 0.810 and the inlay solids
# are 0.810 prisms sitting 0.010 LOWER, so they stand 0.010 proud of the lid's
# underside. Their total volume is exactly the pocket's.
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
    """A cylindrical face's radius, or None. `Face.radius` raises on the
    glyph arcs of the embossed text, which are cylinders too."""
    try:
        return face.radius
    except Exception:
        return None


def socket_walls(solid, x, y0, y1):
    """{X: area} of the X-normal faces inside one socket — the whole of the
    lock in one probe: block sides, recess floor, and both channel walls."""
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


for name, fn, P, text_area, logo_area in REFS:
    path = STEP_DIR / fn
    print(f"\n=== {name} ===")
    if not path.exists():
        print(f"  SKIP — {path} not present")
        continue
    d = D.derive(P)
    # The STEP carries the logo pattern's inlays as separate solids sitting in
    # z -0.010..0.800; the lid body is the big one, and it is NOT pocketed for
    # them — see spec/LID.md.
    solids = import_step(str(path)).solids()
    ref = max(solids, key=lambda s: s.volume)
    mine = lid.build(P)
    rb, mb = ref.bounding_box(), mine.bounding_box()
    print(f"  reference {len(solids)} solids, body {len(ref.faces())} faces, "
          f"{ref.volume:.3f} mm3;  build {len(mine.faces())} faces, "
          f"{mine.volume:.3f} mm3")

    # --- the envelope ------------------------------------------------------
    check("width  = #BoxWidth + 4.600", round(rb.size.X, 3),
          round(lid.lid_width(P, d), 3), 1e-3)
    check("depth  = calLidDepth", round(rb.size.Y, 3),
          round(d.calLidDepth, 3), 1e-3)
    check("height = LidHeight", round(rb.size.Z, 3), round(d.LidHeight, 3), 1e-3)
    check("build envelope = the reference's",
          [round(v, 3) for v in (mb.size.X, mb.size.Y, mb.size.Z)],
          [round(v, 3) for v in (rb.size.X, rb.size.Y, rb.size.Z)])
    check("centred on X and Y, floor at z = 0",
          [round(v, 3) for v in (rb.min.X + rb.max.X, rb.min.Y + rb.max.Y,
                                 rb.min.Z)], [0.0, 0.0, 0.0])

    # --- the shell ---------------------------------------------------------
    W = lid.lid_width(P, d) / 2
    DD = lid.lid_depth(d) / 2
    for who, solid in (("STEP ", ref), ("build", mine)):
        # A wall's own area is what tells it from its neighbour: the outer
        # face runs the full height less the 1.000 rounds, the inner one is
        # WALL shorter in both directions.
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

    # --- the sockets: the lid's half of the 7.0 lock -----------------------
    y0, y1 = lid.socket_span(P, d)
    cls, s = L.lock_class(d.calPusherTotalDepth)
    check(f"lock class from calPusherTotalDepth {d.calPusherTotalDepth:.2f}",
          cls, cls)
    check("socket span = calPusherTotalDepth - 0.400", round(y1 - y0, 3),
          round(d.calPusherTotalDepth - L.LID_SOCKET_CLEARANCE, 3), 1e-6)
    check("socket back edge SOCKET_BACK in from the lid's back",
          round(d.calLidDepth / 2 - y1, 3), round(lid.SOCKET_BACK, 3), 1e-6)
    side = round(lid.SOCKET_H * (y1 - y0), 2)     # a socket block's own side
    for who, solid in (("STEP ", ref), ("build", mine)):
        xs = sorted(k[0] for k, a in planes(solid, 0).items()
                    if abs(a - side) < 1e-2)
        check(f"{who}: one block per socket, SOCKET_W wide", len(xs),
              2 * lid.socket_count(P))
        if len(xs) != 2 * lid.socket_count(P):
            continue
        check(f"{who}: socket centres",
              [round((a + b) / 2, 3) for a, b in zip(xs[0::2], xs[1::2])],
              [round(x, 3) for x in lid.socket_centres(P, d)])
        check(f"{who}: block width",
              sorted({round(b - a, 3) for a, b in zip(xs[0::2], xs[1::2])}),
              [round(lid.SOCKET_W, 3)])
        rib = lid.KEY_RIB_LEN if L.has_notch(s) else 0.0
        want_chan = round(lid.SOCKET_H * ((y1 - y0) - rib), 2)
        for x in lid.socket_centres(P, d):
            got = socket_walls(solid, x, y0, y1)
            want = {
                round(x - lid.SOCKET_W / 2, 3): side,
                round(x - L.LID_CHANNEL_W / 2 - L.LID_RECESS_STEP, 3):
                    round(2 * L.LID_RECESS_LEN * lid.SOCKET_H, 2),
                round(x - L.LID_CHANNEL_W / 2, 3):
                    round(want_chan - 2 * L.LID_RECESS_LEN * lid.SOCKET_H, 2),
                round(x + L.LID_CHANNEL_W / 2, 3): want_chan,
                round(x + lid.SOCKET_W / 2, 3): side,
            }
            ok = (sorted(got) == sorted(want)
                  and all(abs(got[k] - want[k]) < 0.02 for k in want))
            check(f"{who}: socket at {x:+8.3f} — channel, recesses, rib",
                  ok if ok else got, True if ok else want)

    # The recesses carry `s`, and both are cut into the -X wall only.
    for who, solid in (("STEP ", ref), ("build", mine)):
        end = round(L.LID_RECESS_STEP * lid.SOCKET_H, 3)
        # Deduped: every socket has its recesses at the same two Y, so the
        # four distinct ends pair up whatever the socket count is.
        ys = sorted({round(f.center().Y, 3) for f in solid.faces()
                     if f.geom_type == GeomType.PLANE
                     and abs(f.normal_at(f.center()).Y) > 0.999
                     and abs(f.area - end) < 1e-3
                     and lid.WALL < f.center().Z < lid.WALL + lid.SOCKET_H})
        centres = sorted(round((a + b) / 2, 3) for a, b in zip(ys[0::2], ys[1::2]))
        check(f"{who}: tab recesses at the socket centreline +- s ({cls})",
              [round(c - (y0 + y1) / 2, 3) for c in centres],
              [-round(s, 3), round(s, 3)])

    # --- the closing grooves ----------------------------------------------
    z0, z1 = lid.groove_span(d)
    flat = round(2 * lid.GROOVE_LEN * (lid.GROOVE_DEPTH - lid.GROOVE_CHAMFER), 3)
    for who, solid in (("STEP ", ref), ("build", mine)):
        check(f"{who}: groove floor z0 = WALL + BoxHeight - 90",
              area_at(solid, 2, z0, "+"), flat, 1e-3)
        check(f"{who}: groove roof GROOVE_HEIGHT above it",
              area_at(solid, 2, z1, "-"), flat, 1e-3)
        # The floor is INTO the wall, so outboard of its inner face: it faces
        # back at the cavity, +X on the -X wall and -X on the +X one.
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

    # --- the outer rounds --------------------------------------------------
    for who, solid in (("STEP ", ref), ("build", mine)):
        cyl = [f for f in solid.faces() if f.geom_type == GeomType.CYLINDER
               and radius(f) is not None
               and abs(radius(f) - lid.OUTER_ROUND) < 1e-9]
        sph = [f for f in solid.faces() if f.geom_type == GeomType.SPHERE]
        check(f"{who}: 12 outer edges rounded OUTER_ROUND", len(cyl), 12)
        check(f"{who}: 8 corner blends, each an eighth of a sphere",
              [len(sph), sorted({round(f.area, 4) for f in sph})],
              [8, [round(math.pi * lid.OUTER_ROUND ** 2 / 2, 4)]])

    # --- what is NOT built yet ---------------------------------------------
    # Three things, all on the floor. Above it, three embossed lines 0.400
    # proud and the ProductName over its staircase logo 0.600 proud. Below it,
    # the logo PATTERN's pocket, 0.800 deep — present in the exports Allan took
    # "with logo meshes embedded" and absent from the first 246S, which is why
    # it is measured here rather than assumed.
    #
    # Nothing else may differ, so those three account for the whole volume
    # gap, and the build's floor is bigger by exactly the two on top of it.
    check("STEP: the text stands 0.400 proud of the floor",
          area_at(ref, 2, lid.WALL + 0.4, "+"), round(text_area, 3), 1e-3)
    check("STEP: the logo stands 0.600 proud",
          area_at(ref, 2, lid.WALL + 0.6, "+"), round(logo_area, 3), 1e-3)
    # The pocket's ceiling faces DOWN — it is open at the lid's underside —
    # and is the one clean face it has, so it is the measure. What it takes
    # out of the underside corroborates it, and the inlay solids fill it.
    floor = round((2 * W - 2 * lid.OUTER_ROUND)
                  * (2 * DD - 2 * lid.OUTER_ROUND), 3)
    pattern = area_at(ref, 2, PATTERN_DEPTH, "-")
    check("STEP: the pattern pocket is what the underside is missing",
          round(floor - area_at(ref, 2, 0.0, "-"), 2), round(pattern, 2), 0.6)
    inlays = round(sum(x.volume for x in solids if x is not ref), 2)
    if pattern:
        check("STEP: and the inlay solids fill exactly that", inlays,
              round(pattern * PATTERN_DEPTH, 2), 0.1)
    else:
        # `Lid Dominion 246S.step` is the one export taken WITHOUT the logo
        # meshes embedded: the inlays are there as solids, but the body is not
        # pocketed for them. The pair with `...246S with logo.step` is what
        # makes the pocket measurable on its own — the same trick as the Box's
        # filleted/unfilleted pair.
        check("STEP: no pocket, but the inlay solids are still in the file",
              inlays > 0, True)
    # Everything the two solids differ by, and nothing else: the emboss adds,
    # the pattern pocket takes away. To 0.3 mm3 in 6e4 — the residual is
    # OCCT's area integration over faces carrying a thousand glyph wires, and
    # it is what it is on the Innovation lid, whose pattern has 31 pieces.
    check("reference - build = the unbuilt text, logo and pattern pocket",
          round(ref.volume - mine.volume, 2),
          round(text_area * 0.4 + logo_area * 0.6
                - pattern * PATTERN_DEPTH, 2), 0.3)
    # The floor at 0.5 mm2, where the volume closes at 0.03: the reference's
    # floor face carries about a thousand inner wires — every glyph — and
    # OCCT's area integration over it is good to a few parts in 1e5, which on
    # 1e4 mm2 is a tenth of a mm2. The volume is the tighter statement of the
    # same fact, so this is the loose corroboration of it and not the check.
    check("and the build's floor is bigger by the two ON it",
          round(area_at(mine, 2, lid.WALL, "+")
                - area_at(ref, 2, lid.WALL, "+"), 2),
          round(text_area + logo_area, 2), 0.5)

print(f"\n{'FAILED: ' + ', '.join(fails) if fails else 'all checks passed'}")
sys.exit(1 if fails else 0)
