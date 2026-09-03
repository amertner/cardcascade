#!/usr/bin/env python3
"""Every cached Topper in `individual/` against the rules `cad/parts/topper.py`
states.

    .venv/bin/python tests/test_topper_corpus.py

`tests/test_topper.py` checks the source against four hand-exported STEPs at
two parameter sets. Two parameter sets cannot tell a rule from a coincidence,
so this reads all 48 cached meshes instead — 0 API calls — and holds every one
of them to the placement rules: the envelope, the ribs and front bands, the two
holder tabs, and the eight lip notches.

Onshape's catalogue is 6 expansions over 8 bodies, and only the BODY is built
here: `Expansion Name` is not written. So the eight `Blank` files are checked on
volume as well, and the other forty on placement only — an engraved topper is
the blank less its lettering, which is 10 to 30 mm3.

Probed by ray-casting the mesh, the same way `tests/test_lid_corpus.py` does,
and with the same rule: **never aim a ray at a feature's exact centre**. A
rectangular face is two triangles and a ray down their shared diagonal is
counted twice, which cancels and makes the face vanish. Every probe here is
offset by EPS.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import build as B, mesh3mf, params, derive as D  # noqa: E402
from cad.parts import holder as H, topper as T            # noqa: E402

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
    """[(lo, hi)] of material along `axis` on the ray through the other two
    coordinates, in cyclic order — (y, z) for X, (z, x) for Y, (x, y) for Z."""
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
    """{`M10-Un`: Primary} — the topper's own key, which is NOT calModelName.

    Size letter, cards per sliding slot and sleeving are the only three things
    the geometry depends on, and Onshape's file names say exactly that.
    """
    out = {}
    for row in params.load_rows(ROOT / "automation" / "parts.csv"):
        # Single-set cascades hold one expansion, so they carry no toppers at
        # all (Allan). cad.build.topper_catalogue skips them for the same
        # reason and by the same column.
        if B.SINGLE_SET in (row.get("Set/Extension") or "").lower():
            continue
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            if p.GameName != "Innovation":
                continue
            d = D.derive(p)
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
    x0, x1 = T.x_span(p, d)
    front, rear = T.y_span(p, d)
    tag = f"{expansion} {key}"

    # --- the envelope, and its three rules ---------------------------------
    check(f"{tag}: X min", round(float(V[:, 0].min()), 3), round(x0, 3), 1e-3)
    check(f"{tag}: X max", round(float(V[:, 0].max()), 3), round(x1, 3), 1e-3)
    check(f"{tag}: Y front", round(float(V[:, 1].max()), 3), round(front, 3), 1e-3)
    check(f"{tag}: Y rear", round(float(V[:, 1].min()), 3), round(rear, 3), 1e-3)
    check(f"{tag}: base", round(float(V[:, 2].min()), 3), round(T.Z_BASE, 3), 1e-3)
    check(f"{tag}: tab tops", round(float(V[:, 2].max()), 3),
          round(T.Z_BASE + T.TOTAL_HEIGHT, 3), 1e-3)

    # --- the two holder tabs, well above the wall -------------------------
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

    # --- a T in plan: a wide band at the front face, a rib behind it -------
    # The two END half-bands read short, because `Top and front edges` rounds
    # the part's front vertical corners and this ray passes EPS inside them.
    # Their INNER edge is the one this rule is about, so that is what is held.
    z = (T.Z_BASE + T.FLOOR + T.FRONT_WALL_RISE
         + T.slant_z(p, d, front - T.FRONT_WALL)) / 2
    band = spans(V, Tr, 0, front - EPS, z)
    check(f"{tag}: one band per boundary plus two halves",
          len(band), p.HorizontalSlots + 1)
    if len(band) == p.HorizontalSlots + 1:
        want = T.band_x(p, d)
        check(f"{tag}: the left half-band ends at {round(want[0][1], 2)}",
              round(band[0][1], 3), round(want[0][1], 3), 1e-3)
        check(f"{tag}: the right half-band starts at {round(want[-1][0], 2)}",
              round(band[-1][0], 3), round(want[-1][0], 3), 1e-3)
        for (a, b), (c, e) in zip(band[1:-1], want[1:-1]):
            check(f"{tag}: band at {round(c, 2)}", (round(a, 3), round(b, 3)),
                  (round(c, 3), round(e, 3)))

    # One step behind the front wall only the ribs are left — and, at each end,
    # the end wall and the tab merged into one 2.900 block: INNER_END_INSET
    # 1.400 of end wall overlapping a tab that starts TAB_INSET 1.300 in.
    rib = spans(V, Tr, 0, front - T.FRONT_WALL - EPS, z)
    blk = T.TAB_INSET + T.TAB_W
    want = [(x0, x0 + blk)] + T.rib_x(p, d) + [(x1 - blk, x1)]
    check(f"{tag}: ribs, plus an end block each side", len(rib), len(want))
    for (a, b), (c, e) in zip(rib, want):
        check(f"{tag}: rib/block at {round(c, 2)}", (round(a, 3), round(b, 3)),
              (round(c, 3), round(e, 3)))

    # --- the lip notches, in the rear wall --------------------------------
    # The rear wall is only #TopperHeight - FLOOR - LIP_ROOM_RISE = 1.000 tall
    # above the notch floor at the rear FACE, so the ray goes half way up that,
    # where LIP_FILLET has not finished opening. `off` is where the fillet's
    # arc is at that height, and it has to be allowed for exactly — a probe
    # that ignores it reads every notch 0.655 too narrow.
    h = (T.topper_height(p, d) - T.FLOOR - T.LIP_ROOM_RISE) / 2
    r = T.LIP_FILLET
    off = r - (2 * r * h - h * h) ** 0.5
    z = T.Z_BASE + T.FLOOR + T.LIP_ROOM_RISE + h
    wall = spans(V, Tr, 0, rear + EPS, z)
    rooms = T.lip_room_x(p, d)
    check(f"{tag}: {len(rooms)} notches leave {len(rooms) + 1} runs of wall",
          len(wall), len(rooms) + 1)
    if len(wall) == len(rooms) + 1:
        # ARC_TOL, not the 1e-3 the flat probes use: this ray lands on the
        # fillet's curved face, which the mesh chords, so it reads inside the
        # true surface by up to the sagitta. Measured 0.002 on all 48.
        for (_a, b), (c, _e) in zip(wall, rooms):
            check(f"{tag}: notch starts at {round(c, 2)}", round(b, 3),
                  round(c + off, 3), ARC_TOL)
        for (a, _b), (_c, e) in zip(wall[1:], rooms):
            check(f"{tag}: ... and ends at {round(e, 2)}", round(a, 3),
                  round(e - off, 3), ARC_TOL)

    # --- the mark, measured off the pocket's TOP rim ----------------------
    # A prismatic pocket is tessellated with vertices only at its two ends, so
    # anything strictly between the two reads the `Top and front edges` fillet
    # instead and every file comes back 0.800 wide.
    if expansion != "Blank":
        rim = V[(np.abs(V[:, 2] - (T.Z_BASE + T.ENGRAVE)) < 1e-4)
                & (V[:, 0] < T.text_origin_x(p, d))]
        got = float(rim[:, 0].max() - rim[:, 0].min())
        want = T.MARKS[expansion](d.calLogoSidelength).bounding_box().size.X
        marks.append((tag, expansion, key, got, want))

    blanks.append((tag, expansion, mesh_volume(V, Tr),
                   mesh_volume(*mesh3mf.triangulate(T.build(p, d, expansion)))))

# The four SLEEVED `Unseen` files are STALE: their mark is drawn at the M10-Un
# size — 5.3422, which is 1.2644 * 4.2250 — whatever their own
# calLogoSidelength is. That is a fault in the CACHE, not in the source; the
# hand-exported `Topper Unseen M5.15.15.62-Sl.step` at the same parameter set
# has it right at 10.7949. All four UNSLEEVED ones are correct.
#
# Listed rather than detected, so that re-exporting them makes this test say
# so instead of quietly passing on a smaller list.
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
    # Both sides are tessellations of the same tolerance, so this is a real
    # comparison and not a mesh-versus-solid one. The residual is the font.
    check(f"{tag}: within 0.02% of the cached mesh", abs(off) < 0.02, True)
print(f"\n  worst of the {len(blanks) - len(STALE)} sound files: {worst:.4f}%")

print(f"\n{len(files)} files, {len(seen)} of {len(cat)} parameter sets matched")
missing = sorted(set(cat) - seen)
if missing:
    # Every parameter set the catalogue emits should be in the cache. A gap
    # means either a cascade whose toppers were never exported, or a row that
    # should have been excluded as single-set.
    check(f"every catalogued parameter set is cached (missing {missing})",
          missing, [])
if unmatched:
    print(f"  FAIL unmatched files: {unmatched}")
    fails.append("unmatched files")

print("\nPASS" if not fails else f"\nFAIL ({len(fails)}): " + "; ".join(fails[:6]))
sys.exit(1 if fails else 0)
