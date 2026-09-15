"""No lid mark is thinner than the cut floor at any scale the fit picks.

The mark is an inlay in a cut pocket, so it takes the CUT floor
`text.FLOOR_CUT`, and a DRAWN mark's strokes scale with the fit
(`spec/LID.md`, "Sizing the mark"). So the question is per scale: each (game,
drawing, factor) is rasterised at RES px/mm and read off the medial axis, as
`cad/text.STROKE` was measured.

    .venv/bin/python tests/test_lid_marks.py     # about two minutes
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import Compound                                  # noqa: E402
from cad import build as B, derive as D, marks as MK, text as T  # noqa: E402
from cad.parts import lid                                       # noqa: E402

RES = 40                     # px per mm: a stroke reads to 0.025
# The thinnest stroke of each drawing AT ITS DRAWN SIZE, as measured.
DRAWN = {("Compile", "lid_logo.dxf"): 0.250,
         ("Dominion", "lid_logo.dxf"): 0.550,
         ("FCM", "lid_logo.dxf"): 0.492,
         ("Innovation", "@innovation-plain"): 0.602,
         ("Innovation", "@innovation-ultimate"): 0.602,
         ("Innovation", "@innovation-ultimate-big"): 0.604}
fails = []


def check(label, got, want, tol=0.0):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok ' if ok else 'FAIL'}  {label:64s} {got} vs {want}")
    if not ok:
        fails.append(label)


def raster(faces):
    """The mark's ink as a boolean image, RES px/mm, 2 mm of border."""
    bb = Compound(children=faces).bounding_box()
    im = Image.new("L", (int((bb.size.X + 4) * RES), int((bb.size.Y + 4) * RES)), 0)
    draw = ImageDraw.Draw(im)
    for f in faces:
        verts, tris = f.tessellate(0.01, 0.2)
        for a, b, c in tris:
            draw.polygon([((verts[i].X - bb.min.X + 2) * RES,
                           (verts[i].Y - bb.min.Y + 2) * RES) for i in (a, b, c)],
                         fill=255)
    return np.array(im) > 127


def thinnest(ink):
    """1st percentile of twice the distance to background, along the medial
    axis, in mm; corner pixels excluded."""
    dist = ndimage.distance_transform_edt(ink)
    ridge = ink & (dist >= ndimage.maximum_filter(dist, size=3) - 1e-9) & (dist > 0.5)
    return float(np.percentile(2 * dist[ridge] / RES, 1))


print("=== the scales the catalogue fits ===")
scales = {}
for game, fn, p, variant in B.lid_catalogue():
    d = D.derive(p)
    name, n = lid.logo_choice(d, variant)   # (None, 0.0) for an unmarked lid
    if name:
        scales.setdefault((game, name), {})[round(n, 6)] = fn
for (game, name), by_n in sorted(scales.items()):
    print(f"  {game:11s} {name:18s} {len(by_n)} scale(s), "
          f"{min(by_n):.3f} .. {max(by_n):.3f}")
check("every mark in the catalogue has a recorded n = 1 stroke",
      sorted(scales), sorted(DRAWN))

print("\n=== the thinnest stroke, at n = 1 and every fitted scale ===")
floor = T.FLOOR_CUT
for (game, name), by_n in sorted(scales.items()):
    drawn = thinnest(raster(MK.faces(game, name, 1.0)))
    check(f"{game} {name}: thinnest stroke at n = 1",
          round(drawn, 3), DRAWN[(game, name)], 0.03)
    worst = None
    for n in sorted(by_n):
        t = thinnest(raster(MK.faces(game, name, n)))
        if worst is None or t < worst[0]:
            worst = (t, n, by_n[n])
        check(f"{game} {name} at n={n:.3f} ({by_n[n]}): stroke >= {floor}",
              t >= floor - 1e-9, True)
    print(f"      {game} {name}: thinnest in the catalogue {worst[0]:.3f} mm "
          f"at n={worst[1]:.3f} on {worst[2]}")

# The floor in ARITHMETIC: the raster quantises to 0.025, no finer than
# Compile's margin (0.250 x 0.855 = 0.214 vs 0.200, spec/LID.md).
print("\n=== a drawn mark's thinnest stroke, exactly ===")
for (game, name), by_n in sorted(scales.items()):
    if name.startswith("@"):
        continue                 # generated: its strokes do not scale at all
    for n in sorted(by_n):
        check(f"{game} {name} at n={n:.3f} ({by_n[n]}): "
              f"{DRAWN[(game, name)]} x n >= {floor}",
              round(DRAWN[(game, name)] * n, 4) >= floor, True)

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
