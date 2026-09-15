#!/usr/bin/env python3
"""Band-by-band comparison of cad/parts/holder.py against the reference STEPs —
a DEV LOOP, not a test. `tests/test_holder.py` is what asserts.

Takes reference keys (`holder_diff.py 246Sl 333Sl`), else all ten, and prints
the total volume either side plus the signed difference in each of five bands;
positive means the build has MORE material there. It INTERSECTS where
`tests/box_diff.py` subtracts: with `Bottom Text` built, `ref - mine` returns
the whole solid on five of the ten and no fuzzy tolerance helps. An error
moving material within one cell then cancels, so the bands are cut at the
feature groups — `lips` (proud of the rear face), `text` (the ENGRAVE-deep
slice of the underside), `base` (above that, to the pocket's floor), `rests`
(`Lip Rest`'s swept zone, widened by REST_MARGIN so a chamfer error is in it
and not in `body`) and `body` (the rest). **`residual` is the method's own
error, why `rests` is not a measurement** — spec/HOLDER.md, "Completeness".
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from build123d import Box, Location, Vector, import_step, extrude  # noqa: E402
from build123d import BuildLine, BuildSketch, Plane, Polyline, make_face  # noqa: E402
from cad import params, derive as D                    # noqa: E402
import reference as REF                                        # noqa: E402
from cad.parts import holder                           # noqa: E402

STEP_DIR = ROOT / "spec" / "reference"
_ROWS = list(params.load_rows(ROOT / "automation" / "parts.csv"))

REST_MARGIN = 1.0          # widen the rest's section so a chamfer error is in it
COLS = ("text", "base", "body", "rests", "lips")


def row_params(short_name, sleeved):
    for row in _ROWS:
        if row.get("Short name") == short_name:
            return REF.from_row(row, sleeved)
    raise KeyError(short_name)


# The same ten `tests/test_holder.py` asserts against, by the same keys.
def refs():
    P246 = REF.primary(3, 2, 40, 12, 1, 30, 1, 0, "Dominion")
    P333 = REF.primary(3, 9, 21, 10, 0, 10, 1, 0, "Dominion")
    PINN_SL = REF.primary(4, 5, 10, 10, 0, 10, 1, 0, "Innovation")
    PINN_UN = REF.primary(4, 5, 10, 10, 0, 10, 0, 0, "Innovation")
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
    """The lip rests' swept prisms, widened by REST_MARGIN a side — OBLIQUE
    along the slant, as `holder.lip_rests` cuts them: a right prism puts the
    chamfer residual outside its band."""
    slope = holder.slant_slope(d, first)
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
    for xc in holder.compartment_x(d):
        for sign in (+1, -1):
            at = Vector(xc + sign * x_mid, 0.0,
                        holder.slant_top(d) - holder.SLANT_STEP / 2)
            face = sk.sketch.moved(Location(at))
            prism = extrude(face, amount=holder.LIP_REST_THROUGH, dir=dirv)
            zone = prism if zone is None else zone + prism
    return zone


def bands(p, d, first):
    """[(name, cell)] — the five, as solids to intersect both shapes with."""
    x0, x1 = holder.x_span(d)
    dep = holder.holder_depth(d, first)
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
    # `body` is `upper` less `rests` as a subtraction of VOLUMES, not solids:
    # cutting the zone out loses a few mm3 to OCCT and the bands then do not
    # add up to the difference they explain.
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
        mine = holder.build(D.derive(p), first)
        d = D.derive(p)
        deltas = {}
        for name, cell in bands(p, d, first):
            deltas[name] = volume(mine, cell) - volume(ref, cell)
        deltas["body"] = deltas.pop("upper") - deltas["rests"]
        # The bands tile the part: what is left over is a failed boolean.
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
