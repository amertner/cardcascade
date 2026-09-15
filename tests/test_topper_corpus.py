#!/usr/bin/env python3
"""Every cached Topper in `individual/` against the rules `cad/parts/topper.py`
states.

`tests/test_topper.py` checks the source against four hand-exported STEPs at
two parameter sets, which cannot tell a rule from coincidence; this reads all
48 cached meshes — 0 API calls. Onshape's catalogue is 6 expansions over 8
bodies: the `Blank` files are checked on volume too, the other forty on
placement and the mark's rim, the lettering against the STEPs. Probed by
ray-casting under `tests/probe.py`'s rule — **never aim a ray at a feature's
exact centre**.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from cad import build as B, mesh3mf, params, derive as D  # noqa: E402
import reference as REF                                        # noqa: E402
from cad.parts import topper as T                         # noqa: E402

EPS = 0.013            # see the module docstring: never probe down a diagonal
ARC_TOL = 0.005        # a probe that lands on a fillet, not on a plane
INDIV = ROOT / "individual" / "Innovation"
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        fails.append(f"{label}: {got!r} vs {want!r}")
        print(f"    FAIL {label}: {got!r} vs {want!r}")
    return ok


def load(path):
    _n, verts, tris = max(mesh3mf.read(path), key=lambda m: len(m[2]))
    return np.array(verts), np.array(tris)


def spans(V, Tr, axis, u, v, tol=1e-6):
    """[(lo, hi)] of material along `axis` — see `tests/probe.spans`."""
    i, j, k = axis, (axis + 1) % 3, (axis + 2) % 3
    A, B, C = V[Tr[:, 0]], V[Tr[:, 1]], V[Tr[:, 2]]
    a = np.column_stack([A[:, j], A[:, k]])
    b = np.column_stack([B[:, j], B[:, k]])
    c = np.column_stack([C[:, j], C[:, k]])
    p = np.array([u, v])

    def cross(m, n):
        return m[:, 0] * n[:, 1] - m[:, 1] * n[:, 0]

    d1, d2, d3 = (cross(b - a, p - a), cross(c - b, p - b), cross(a - c, p - c))
    area = cross(b - a, c - a)
    inside = (((d1 >= 0) & (d2 >= 0) & (d3 >= 0))
              | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))) & (np.abs(area) > 1e-12)
    idx = np.where(inside)[0]
    w1, w2 = d2[idx] / area[idx], d3[idx] / area[idx]
    t = np.sort(w1 * A[idx, i] + w2 * B[idx, i] + (1 - w1 - w2) * C[idx, i])
    merged = []
    for x in t:
        if merged and abs(x - merged[-1]) < tol:
            merged.pop()
        else:
            merged.append(float(x))
    return list(zip(merged[0::2], merged[1::2]))


def mesh_volume(V, Tr):
    V, Tr = np.asarray(V), np.asarray(Tr)
    A, B, C = V[Tr[:, 0]], V[Tr[:, 1]], V[Tr[:, 2]]
    return float(abs(np.einsum('ij,ij->i', A, np.cross(B, C)).sum()) / 6.0)


def catalogue():
    """{`M10-Un`: Primary} — the topper's key, which is NOT calModelName."""
    out = {}
    for row in params.load_rows(ROOT / "automation" / "parts.csv"):
        for sleeved in (0, 1):
            p = REF.from_row(row, sleeved)
            if p.GameName != "Innovation":
                continue
            d = D.derive(p)
            # Single-set cascades carry no toppers, and `Toppers` = `none`
            # opts out a row sharing this key at another rise
            # (`build.ships_toppers`).
            if not B.ships_toppers(row, d):
                continue
            key = (f"{d.calSizeLetter}{p.CardsPerSlidingSlot}"
                   f"{'-Sl' if sleeved else '-Un'}")
            out[key] = p
    return out


cat = catalogue()
files = sorted(INDIV.glob("Topper *.3mf"))
print(f"{len(files)} cached toppers, {len(cat)} parameter sets in parts.csv\n")

seen, unmatched, blanks, marks = set(), [], [], []
for path in files:
    stem = path.stem[len("Topper "):]
    expansion, key = stem.split(" ", 1)
    p = cat.get(key)
    if p is None:
        unmatched.append(path.name)
        continue
    seen.add(key)
    d = D.derive(p)
    V, Tr = load(path)
    x0, x1 = T.x_span(d)
    front, rear = T.y_span(d)
    tag = f"{expansion} {key}"

    check(f"{tag}: X min", round(float(V[:, 0].min()), 3), round(x0, 3), 1e-3)
    check(f"{tag}: X max", round(float(V[:, 0].max()), 3), round(x1, 3), 1e-3)
    check(f"{tag}: Y front", round(float(V[:, 1].max()), 3), round(front, 3), 1e-3)
    check(f"{tag}: Y rear", round(float(V[:, 1].min()), 3), round(rear, 3), 1e-3)
    check(f"{tag}: base", round(float(V[:, 2].min()), 3), round(T.Z_BASE, 3), 1e-3)
    check(f"{tag}: tab tops", round(float(V[:, 2].max()), 3),
          round(T.Z_BASE + T.TOTAL_HEIGHT, 3), 1e-3)

    z = T.Z_BASE + T.TOTAL_HEIGHT - 5.0
    y = (front - T.FRONT_WALL + rear) / 2 + EPS
    got = spans(V, Tr, 0, y, z)
    want = [(x0 + T.TAB_INSET, x0 + T.TAB_INSET + T.TAB_W),
            (x1 - T.TAB_INSET - T.TAB_W, x1 - T.TAB_INSET)]
    check(f"{tag}: two tabs, TAB_W wide, TAB_INSET in", len(got), 2)
    if len(got) == 2:
        for (a, b), (c, e) in zip(got, want):
            check(f"{tag}: tab at {round(c, 2)}", (round(a, 3), round(b, 3)),
                  (round(c, 3), round(e, 3)))

    # A T in plan. The END half-bands read short (rounded front corners), so
    # only their INNER edge is held.
    z = (T.Z_BASE + T.FLOOR + T.FRONT_WALL_RISE
         + T.slant_z(d, front - T.FRONT_WALL)) / 2
    band = spans(V, Tr, 0, front - EPS, z)
    check(f"{tag}: one band per boundary plus two halves",
          len(band), p.HorizontalSlots + 1)
    if len(band) == p.HorizontalSlots + 1:
        want = T.band_x(d)
        check(f"{tag}: the left half-band ends at {round(want[0][1], 2)}",
              round(band[0][1], 3), round(want[0][1], 3), 1e-3)
        check(f"{tag}: the right half-band starts at {round(want[-1][0], 2)}",
              round(band[-1][0], 3), round(want[-1][0], 3), 1e-3)
        for (a, b), (c, e) in zip(band[1:-1], want[1:-1]):
            check(f"{tag}: band at {round(c, 2)}", (round(a, 3), round(b, 3)),
                  (round(c, 3), round(e, 3)))

    # One step back only the ribs are left, plus a 2.900 end block each side.
    rib = spans(V, Tr, 0, front - T.FRONT_WALL - EPS, z)
    blk = T.TAB_INSET + T.TAB_W
    want = [(x0, x0 + blk)] + T.rib_x(d) + [(x1 - blk, x1)]
    check(f"{tag}: ribs, plus an end block each side", len(rib), len(want))
    for (a, b), (c, e) in zip(rib, want):
        check(f"{tag}: rib/block at {round(c, 2)}", (round(a, 3), round(b, 3)),
              (round(c, 3), round(e, 3)))

    # The rear wall is only 1.000 tall above the notch floor, so the ray goes
    # half way up it, where LIP_FILLET is still opening; `off` is the arc
    # there, and ignoring it reads every notch 0.655 too narrow.
    h = (T.topper_height(d) - T.FLOOR - T.LIP_ROOM_RISE) / 2
    r = T.LIP_FILLET
    off = r - (2 * r * h - h * h) ** 0.5
    z = T.Z_BASE + T.FLOOR + T.LIP_ROOM_RISE + h
    wall = spans(V, Tr, 0, rear + EPS, z)
    rooms = T.lip_room_x(d)
    check(f"{tag}: {len(rooms)} notches leave {len(rooms) + 1} runs of wall",
          len(wall), len(rooms) + 1)
    if len(wall) == len(rooms) + 1:
        # ARC_TOL: this ray lands on a chorded curved face and reads inside
        # it by up to the sagitta — 0.002 on all 48.
        for (_a, b), (c, _e) in zip(wall, rooms):
            check(f"{tag}: notch starts at {round(c, 2)}", round(b, 3),
                  round(c + off, 3), ARC_TOL)
        for (a, _b), (_c, e) in zip(wall[1:], rooms):
            check(f"{tag}: ... and ends at {round(e, 2)}", round(a, 3),
                  round(e - off, 3), ARC_TOL)

    # Off the pocket's TOP rim: a prismatic pocket has vertices only at its
    # ends, and between them the reading is the fillet, 0.800 wide.
    if expansion != "Blank":
        rim = V[(np.abs(V[:, 2] - (T.Z_BASE + T.ENGRAVE)) < 1e-4)
                & (V[:, 0] < T.text_origin_x(d))]
        got = float(rim[:, 0].max() - rim[:, 0].min())
        want = T.MARKS[expansion](d.calLogoSidelength).bounding_box().size.X
        marks.append((tag, expansion, key, got, want))

    blanks.append((tag, expansion, mesh_volume(V, Tr),
                   mesh_volume(*mesh3mf.triangulate(T.build(d, expansion)))))

# The four SLEEVED `Unseen` files are STALE — a fault in the CACHE, not the
# source (spec/TOPPER.md). Listed, not detected, so a re-export says so.
STALE = {("Unseen", k) for k in ("M10-Sl", "M15-Sl", "S10-Sl", "S15-Sl")}
STALE_MARK_W = 5.3422          # 1.2644 * the M10-Un calLogoSidelength

print("=== the mark, on all 40 named files ===")
for tag, expansion, key, got, want in sorted(marks):
    if (expansion, key) in STALE:
        check(f"{tag}: STALE, and stale in the recorded way",
              round(got, 3), STALE_MARK_W, 1e-3)
        continue
    check(f"{tag}: the mark is drawn at this row's calLogoSidelength",
          round(got, 4), round(want, 4), 1e-3)
stale_seen = {(e, k) for _t, e, k, _g, _w in marks if (e, k) in STALE}
check("every file listed as stale is still in the corpus",
      stale_seen, STALE)
print(f"  {len(marks) - len(STALE)} sound, {len(STALE)} stale "
      f"(all four sleeved Unseen — they want re-exporting)")


print("\n=== all 48, source against the cached mesh ===")
worst = 0.0
for tag, expansion, cached, built in sorted(blanks):
    off = 100 * (built - cached) / cached
    key = (expansion, tag.split(" ", 1)[1])
    if key in STALE:
        print(f"  {tag:18s} cached {cached:10.4f}  built {built:10.4f}  "
              f"{off:+.3f}%   STALE CACHE, not checked")
        continue
    worst = max(worst, abs(off))
    # Both sides are tessellated alike, so the residual is the font.
    check(f"{tag}: within 0.02% of the cached mesh", abs(off) < 0.02, True)
print(f"\n  worst of the {len(blanks) - len(STALE)} sound files: {worst:.4f}%")

print(f"\n{len(files)} files, {len(seen)} of {len(cat)} parameter sets matched")
missing = sorted(set(cat) - seen)
if missing:
    # A gap is toppers never exported, or a row that should be single-set.
    check(f"every catalogued parameter set is cached (missing {missing})",
          missing, [])
if unmatched:
    print(f"  FAIL unmatched files: {unmatched}")
    fails.append("unmatched files")

print("\nPASS" if not fails else f"\nFAIL ({len(fails)}): " + "; ".join(fails[:6]))
sys.exit(1 if fails else 0)
