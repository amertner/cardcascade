#!/usr/bin/env python3
"""Every cached Lid in `individual/` against the rules `cad/parts/lid.py` states.

    .venv/bin/python tests/test_lid_corpus.py

`tests/test_lid.py` checks the source against four hand-exported STEPs. Four
references cannot tell a rule from a coincidence across a 46-lid catalogue, so
this reads the cached meshes instead — 0 API calls — and holds every one of
them to the placement rules: the envelope, the socket count, where the sockets
sit in X and Y, the closing groove, and where the floor's two engraved blocks
are anchored.

## The corpus is a MIXED generation, exactly as the pushers are

A lid's recess step says which: `1.700` is 7.0 and `1.800` is the pre-7.0
figure `LOCK_STANDARD.md` records as "loose". The 7.0 lids also put their
recesses at the socket centreline +- `s` and carry the key rib on that
centreline; the pre-7.0 ones inset the recesses from the socket's two ends
instead, which is the same rule their pushers' tabs follow.

`cad/` builds 7.0 only (cad/README.md, "One generation"), so the 7.0 lids are
REPRODUCED and asserted, and the pre-7.0 ones are MOVED onto the catalogue —
reported, and asserted only on what does not depend on the generation. That is
the same split `tests/test_pusher_regression.py` makes.

Probed by ray-casting the mesh: a vertex scan misses a face wherever the
tessellation splits one, which cost a false reading on three Innovation lids.

**Never aim a ray at a feature's exact centre.** A rectangular face is two
triangles, and a ray through their shared diagonal is counted once per triangle
— which cancels, and the face vanishes from the reading. Every probe below is
offset by `EPS`, an amount no dimension in the part is a multiple of. Aimed at
the centres instead, half the Compile lids read as pre-7.0 because their recess
walls disappeared.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import mesh3mf, params, derive as D, lock as L, text as TX  # noqa: E402
from cad.parts import lid                                 # noqa: E402

EPS = 0.013            # see the module docstring: never probe down a diagonal
INDIV = ROOT / "individual"
GAMES = ("Compile", "Dominion", "FCM", "Innovation")
fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    if not ok:
        fails.append(f"{label}: {got!r} vs {want!r}")
        print(f"    FAIL {label}: {got!r} vs {want!r}")
    return ok


def load(path):
    """(vertices, triangles) of the lid BODY. A lid 3MF also carries the logo
    pattern's inlays as separate objects; the body is the biggest."""
    meshes = mesh3mf.read(path)
    _n, verts, tris = max(meshes, key=lambda m: len(m[2]))
    return np.array(verts), np.array(tris)


def spans(V, T, axis, u, v, tol=1e-6):
    """[(lo, hi)] of material along `axis` on the ray through the other two
    coordinates, in cyclic order — (y, z) for X, (z, x) for Y, (x, y) for Z."""
    i, j, k = axis, (axis + 1) % 3, (axis + 2) % 3
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    a = np.column_stack([A[:, j], A[:, k]])
    b = np.column_stack([B[:, j], B[:, k]])
    c = np.column_stack([C[:, j], C[:, k]])
    p = np.array([u, v])

    def cross(m, n):        # numpy 2.0 deprecates cross() on 2-vectors
        return m[:, 0] * n[:, 1] - m[:, 1] * n[:, 0]

    d1, d2, d3 = (cross(b - a, p - a), cross(c - b, p - b), cross(a - c, p - c))
    area = cross(b - a, c - a)
    inside = (((d1 >= 0) & (d2 >= 0) & (d3 >= 0))
              | ((d1 <= 0) & (d2 <= 0) & (d3 <= 0))) & (np.abs(area) > 1e-12)
    idx = np.where(inside)[0]
    w1, w2 = d2[idx] / area[idx], d3[idx] / area[idx]
    t = np.sort(w1 * A[idx, i] + w2 * B[idx, i] + (1 - w1 - w2) * C[idx, i])
    merged = []
    for x in t:                       # a ray grazing a shared edge crosses twice
        if merged and abs(x - merged[-1]) < tol:
            merged.pop()
        else:
            merged.append(float(x))
    return list(zip(merged[0::2], merged[1::2]))


def faces_at(V, T, z, tol=1e-6):
    """[(x0, x1, y0, y1)] of the triangles lying in the plane `z` and facing
    up — the top of one embossed feature."""
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    n = np.cross(B - A, C - A)
    ln = np.linalg.norm(n, axis=1)
    keep = (ln > 1e-12)
    up = np.zeros(len(T), dtype=bool)
    up[keep] = (n[keep, 2] / ln[keep] > 0.999) & (np.abs(A[keep, 2] - z) < tol)
    out = []
    for tri in T[up]:
        P = V[tri]
        out.append((P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max()))
    return out


def near(spans_, want, tol=1e-3):
    return (len(spans_) == len(want)
            and all(abs(a - c) < tol and abs(b - e) < tol
                    for (a, b), (c, e) in zip(spans_, want)))


def catalogue():
    """{(GameName, model as the filename spells it): Primary}."""
    out = {}
    for row in params.load_rows(ROOT / "automation" / "parts.csv"):
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            d = D.derive(p)
            name = (d.calModelName.replace(".Sl", "-Sl").replace(".Un", "-Un")
                    .replace("/", "-"))
            out[(p.GameName, name)] = p
    return out


cat = catalogue()
seen = {"7.0": 0, "6.6": 0}
skipped = []
for game in GAMES:
    for path in sorted((INDIV / game).glob("Lid *.3mf")):
        model = path.stem[4:]
        p = cat.get((game, model))
        if p is None:
            # Empty today. It used to catch the two Dominion M8.40.10 lids,
            # read at the time as "a row parts.csv no longer carries" — wrong:
            # they are the Mat `400 Card`'s, and they went unmatched only
            # because individual/ spelled a Mat lid without the `-M` its
            # calModelName carries. Renaming them put the whole corpus under
            # test. Kept as the guard for the next name that drifts.
            skipped.append(f"{game}/{path.name}")
            continue
        d = D.derive(p)
        V, T = load(path)
        print(f"  {game}/{path.stem}")
        W, DD = lid.lid_width(d) / 2, lid.lid_depth(d) / 2
        H = d.LidHeight

        # --- the envelope --------------------------------------------------
        lo, hi = V.min(0), V.max(0)
        check(f"{model}: envelope", [round(v, 3) for v in hi - lo],
              [round(2 * W, 3), round(2 * DD, 3), round(H, 3)])
        check(f"{model}: centred on X and Y, floor at z = 0",
              [round(lo[0] + hi[0], 3), round(lo[1] + hi[1], 3),
               round(float(lo[2]), 3)], [0.0, 0.0, 0.0])

        # --- the sockets ---------------------------------------------------
        y0, y1 = lid.socket_span(d)
        yc = (y0 + y1) / 2
        z = lid.WALL + lid.SOCKET_H / 2 + EPS    # mid-socket, clear of both faces
        centres = lid.socket_centres(d)
        _cls, s = L.lock_class(d.calPusherTotalDepth)
        chan, half = L.LID_CHANNEL_W / 2, d.calFootTotalWidth / 2
        inner = W - lid.WALL - 1e-6              # anything beyond is end wall

        def cavity(axis, u, v, limit):
            return [iv for iv in spans(V, T, axis, u, v)
                    if -limit < iv[0] and iv[1] < limit]

        # One X ray just inside the socket's front end reads every block: two
        # walls with the channel between them.
        check(f"{model}: {len(centres)} sockets, channel {L.LID_CHANNEL_W} wide",
              near(cavity(0, y0 + 0.25 + EPS, z, inner),
                   sorted(sum([[(x - half, x - chan), (x + chan, x + half)]
                               for x in centres], []))), True)

        # --- the closing groove --------------------------------------------
        z0, z1 = lid.groove_span(d)
        for probe, want_wall in ((z0 - 0.5, lid.WALL),
                                 ((z0 + z1) / 2, lid.WALL - lid.GROOVE_DEPTH)):
            got = [iv for iv in spans(V, T, 0, EPS, probe) if iv[0] < -W + 2]
            check(f"{model}: end wall at z={probe:.2f}",
                  [round(got[0][0], 3), round(got[0][1] - got[0][0], 3)],
                  [round(-W, 3), round(want_wall, 3)])
        # Along Y, just outboard of the end wall's inner face — inside the
        # groove, but far enough in that the 1.000 corner rounds are behind us
        # and the ray reaches the lid's own +-calLidDepth/2.
        check(f"{model}: groove is GROOVE_LEN long, centred on y = 0",
              near(spans(V, T, 1, (z0 + z1) / 2 + EPS, -W + lid.WALL - 0.2),
                   [(-DD, -lid.GROOVE_LEN / 2), (lid.GROOVE_LEN / 2, DD)]), True)

        # --- the engraving's two anchors -----------------------------------
        # Not the geometry — that is tests/test_lid.py's job against the STEPs
        # — but the two expressions that place it, which four references
        # cannot tell from a coincidence. Read off the emboss's own top faces:
        # 0.400 proud for the text and 0.600 for the logo.
        text_gap = 2.0 if p.HorizontalSlots > 2 else 15.0
        base = (lid.lid_depth(d) / 2 - lid.WALL - D.FootDistanceFromWall
                - text_gap - lid.CAP_LINE)
        # One of the 0.400-proud lines is calCapacityLabel, and the rule says
        # where. Matched by ink TOP rather than by position in the block: the
        # version is 0.400 proud too, and on an XS lid it sits ABOVE the block
        # rather than beside it.
        want_top = round(base + TX.metrics(d.calCapacityLabel)[3]
                         * lid.CAP_LINE / TX.CAP, 3)
        tops = {round(b[3], 3) for b in faces_at(V, T, lid.WALL + lid.TEXT_PROUD)}
        check(f"{model}: calCapacityLabel's baseline off the socket line",
              any(abs(t - want_top) < 2e-3 for t in tops), True)
        logo = faces_at(V, T, lid.WALL + lid.LOGO_PROUD)
        left = -(lid.lid_width(d) / 2 - lid.WALL) + lid.logo_offset(d)
        check(f"{model}: the logo block starts at logo_offset",
              round(min(b[0] for b in logo), 2),
              round(left + (0.0 if p.HorizontalSlots > 2
                            else 0.056 * lid.logo_size(d)), 2), 0.35)

        # --- which generation this lid is, and then the 7.0 lock ------------
        # The recess step is the tell: probe the -X channel wall where 7.0 puts
        # a recess. At 7.0 the wall has retreated LID_RECESS_STEP there; at 6.6
        # it has not (its own recesses are elsewhere), or it has retreated the
        # pre-7.0 1.800 because the two happen to overlap.
        edge = centres[0] - chan
        ends = [iv[1] for iv in cavity(0, yc - s + EPS, z, inner)
                if abs(iv[1] - edge) < 2.0]
        step = round(edge - ends[0], 3) if ends else None
        if step != L.LID_RECESS_STEP:
            print(f"    pre-7.0 lid (recess step {step}) — moved onto the "
                  f"catalogue, lock not asserted")
            seen["6.6"] += 1
            continue
        seen["7.0"] += 1
        # A Y ray down a channel reads the key rib, or nothing at all.
        check(f"{model}: key rib on the centreline ({_cls})",
              near(cavity(1, z, centres[0] + EPS, DD - lid.WALL),
                   [(yc - lid.KEY_RIB_LEN / 2, yc + lid.KEY_RIB_LEN / 2)]
                   if L.has_notch(s) else []), True)
        for sign in (-1, +1):
            check(f"{model}: tab recesses at the centreline {sign:+d} s",
                  near(cavity(0, yc + sign * s + EPS, z, inner),
                       sorted(sum([[(x - half, x - chan - L.LID_RECESS_STEP),
                                    (x + chan, x + half)]
                                   for x in centres], []))), True)

print(f"\n  {seen['7.0']} lids at 7.0, asserted;  {seen['6.6']} still pre-7.0, "
      f"moved onto the catalogue")
if skipped:
    print(f"  skipped (no parts.csv row): {', '.join(skipped)}")
print(f"\n{'FAILED: ' + '; '.join(fails) if fails else 'all checks passed'}")
sys.exit(1 if fails else 0)
