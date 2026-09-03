#!/usr/bin/env python3
"""Band-by-band comparison of cad/parts/holder.py against the reference STEPs —
a DEV LOOP, not a test. `tests/test_holder.py` is what asserts.

    .venv/bin/python tests/holder_diff.py            # all ten references
    .venv/bin/python tests/holder_diff.py 246Sl 333Sl

Prints, per reference, the total volume either side and the signed difference
in each of five bands. Positive means the build has MORE material there than
the STEP.

## Why this intersects rather than subtracts

`tests/box_diff.py` subtracts slab by slab, because for the Box that works. It
does not work here: once `Bottom Text` was built, `ref - mine` returns the whole
solid on five of the ten references — OCCT cannot clean a difference whose
two operands agree face-for-face over a few hundred engraved glyph edges. A
fuzzy tolerance does not help and neither does slicing.

Intersecting each solid with the SAME cell and comparing the two volumes does
work, and it answers the question a diff was being asked for anyway: not "what
lump is missing" but "which feature group still disagrees, and by how much".
The cost is that an error which moves material from one band to another within
a cell cancels, so the bands are cut where the feature groups are:

    lips    everything proud of the rear face — `Rear lip` and its chamfer
    text    the ENGRAVE-deep slice of the underside — `Bottom Text`
    base    the underside above the engraving, up to the pocket's floor
    rests   the swept zone of `Lip Rest`, widened, minus what the lips took
    body    everything else — the shell, the pocket, the lattice, the scallops

`rests` is the only band that is not a plain half-space: it is the lip rest's
own oblique prism, widened by REST_MARGIN so that a chamfer error falls inside
it rather than half in `body`. The two therefore move together and are read
together — see spec/HOLDER.md, "Completeness, band by band".
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import Box, Location, Vector, import_step, extrude  # noqa: E402
from build123d import BuildLine, BuildSketch, Plane, Polyline, make_face  # noqa: E402
from cad import params, derive as D                    # noqa: E402
from cad.parts import holder                           # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
_ROWS = list(params.load_rows(ROOT / "automation" / "parts.csv"))

REST_MARGIN = 1.0          # widen the rest's section so a chamfer error is in it
COLS = ("text", "base", "body", "rests", "lips")


def row_params(short_name, sleeved):
    for row in _ROWS:
        if row.get("Short name") == short_name:
            return params.from_row(row, sleeved)
    raise KeyError(short_name)


# The same ten `tests/test_holder.py` asserts against, by the same keys.
def refs():
    P246 = params.Primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion")
    P333 = params.Primary(3, 9, 21, 10, 0, 10, 1, 0, "Dominion")
    PINN_SL = params.Primary(4, 5, 10, 10, 0, 10, 1, 0, "Innovation")
    PINN_UN = params.Primary(4, 5, 10, 10, 0, 10, 0, 0, "Innovation")
    return {
        "246Sl": ("Holder S2.40.12-30.45-Sl.step", P246, False),
        "246First": ("FirstHolder S2.40.12-30.45-Sl.step", P246, True),
        "333Sl": ("Holder S9.21.10.62-Sl.step", P333, False),
        "InnoMSl": ("Holder M5.10.10.45-Sl.step", PINN_SL, False),
        "InnoMUn": ("Holder M5.10.10.32-Un.step", PINN_UN, False),
        "InnoXS": ("Holder XS5.15.10.45-Sl.step", row_params("Single Mini", 1),
                   False),
        "Cmp105": ("Holder S4.7.7.32-Sl.step", row_params("105 Card", 1), False),
        "FCM198": ("Holder S4.18.12.32-Un.step", row_params("198 Card", 0),
                   False),
        "Cmp210Sl": ("Holder L5.7.7.45-Sl.step", row_params("210 Card", 1),
                     False),
        "Cmp210Un": ("Holder L5.7.7.20-Un.step", row_params("210 Card", 0),
                     False),
    }


def rest_zone(p, d, first):
    """The lip rests' swept prisms, widened by REST_MARGIN a side.

    Built the same way `holder.lip_rests` builds the cut — an OBLIQUE prism
    along the slant — because a right prism would lean the wrong way and put
    the chamfer residual half outside its own band.
    """
    slope = holder.slant_slope(p, d, first)
    unit = 1.0 / (1.0 + slope * slope) ** 0.5
    dirv = Vector(0.0, -unit, -slope * unit)
    w = holder.LIP_LEN / 2 + holder.LIP_CHAMFER + REST_MARGIN
    h = holder.SLANT_STEP / 2 + REST_MARGIN
    with BuildSketch(Plane.XZ) as sk:
        with BuildLine():
            Polyline((-w, -h), (w, -h), (w, h), (-w, h), close=True)
        make_face()
    x_mid = (holder.FINGER_R + holder.FINGER_FILLET + holder.LIP_GAP
             + holder.LIP_LEN / 2)
    zone = None
    for xc in holder.compartment_x(p, d):
        for sign in (+1, -1):
            at = Vector(xc + sign * x_mid, 0.0,
                        holder.slant_top(d) - holder.SLANT_STEP / 2)
            face = sk.sketch.moved(Location(at))
            prism = extrude(face, amount=holder.LIP_REST_THROUGH, dir=dirv)
            zone = prism if zone is None else zone + prism
    return zone


def bands(p, d, first):
    """[(name, cell)] — the five, as solids to intersect both shapes with."""
    x0, x1 = holder.x_span(p, d)
    dep = holder.holder_depth(p, d, first)
    z0 = holder.base_z(d)
    pz0, _ = holder.pocket_z(d)
    w, tall = (x1 - x0) + 4.0, 400.0
    xc = (x0 + x1) / 2

    def slab(zlo, zhi, ylo, yhi):
        return Box(w, yhi - ylo, zhi - zlo).moved(
            Location((xc, (ylo + yhi) / 2, (zlo + zhi) / 2)))

    lips = slab(z0 - 1.0, z0 + tall, 0.0, 20.0)
    text = slab(z0, z0 + holder.ENGRAVE, -dep - 1.0, 0.0)
    base = slab(z0 + holder.ENGRAVE, pz0, -dep - 1.0, 0.0)
    upper = slab(pz0, z0 + tall, -dep - 1.0, 0.0)
    # `body` is not a cell: it is `upper` less `rests`, taken as a SUBTRACTION
    # OF VOLUMES rather than of solids. Cutting the zone out of the slab and
    # intersecting with that instead loses a couple of cubic millimetres to
    # OCCT, and then the five bands no longer add up to the difference they are
    # supposed to be explaining.
    return [("text", text), ("base", base), ("upper", upper),
            ("rests", upper & rest_zone(p, d, first)), ("lips", lips)]


def volume(shape, cell):
    got = shape & cell
    return got.volume if got and got.solids() else 0.0


def report(keys=None):
    table = refs()
    rows = []
    for key, (fn, p, first) in table.items():
        if keys and key not in keys:
            continue
        path = STEP_DIR / fn
        if not path.exists():
            print(f"{key}: SKIP — {path} not present")
            continue
        ref = import_step(str(path)).solids()[0]
        mine = holder.build(p, first)
        d = D.derive(p)
        deltas = {}
        for name, cell in bands(p, d, first):
            deltas[name] = volume(mine, cell) - volume(ref, cell)
        deltas["body"] = deltas.pop("upper") - deltas["rests"]
        # The bands tile the part, so they have to add up to the whole
        # difference. Anything left over is a boolean that quietly failed.
        deltas["residual"] = (mine.volume - ref.volume) - sum(
            deltas[n] for n in COLS)
        rows.append((key, mine.volume, ref.volume, deltas))
        print(f"{key:10s} built {mine.volume:11.3f}  STEP {ref.volume:11.3f}"
              f"  {(mine.volume / ref.volume - 1) * 100:+7.3f}%   "
              + "  ".join(f"{n} {deltas[n]:+8.2f}" for n in COLS + ("residual",)))
    if len(rows) > 1:
        tot_m = sum(r[1] for r in rows)
        tot_r = sum(r[2] for r in rows)
        print(f"\n{'TOTAL':10s} built {tot_m:11.3f}  STEP {tot_r:11.3f}"
              f"  {(tot_m / tot_r - 1) * 100:+7.3f}%   "
              + "  ".join(f"{n} {sum(r[3][n] for r in rows):+8.2f}"
                          for n in COLS + ("residual",)))


if __name__ == "__main__":
    report(sys.argv[1:] or None)
