#!/usr/bin/env python3
"""Shaded PNGs of a component 3MF, so a build can be eyeballed without Studio.

    .venv/bin/python -m cad.render build/Compile/*.3mf --out tmp/render

Orthographic, one z-buffer per view, flat per-triangle Lambert shading. Two
views per part: the FRONT of the plate, where the engraving and the tabs are,
tilted just enough off-axis that the 0.400 mm engraving walls catch the light,
and the BACK, which is what sits on the bed and must be flat.

This is a looking tool, not a checking one — `tests/test_pusher_regression.py`
is what asserts. It exists because the two things that most want a human eye,
text legibility and whether the lock looks sensible on a short pusher, are the
two the numbers are least able to settle.
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from . import mesh3mf

BG = 250
INK = (40, 44, 52)


def _basis(az, el):
    """Camera axes for an azimuth/elevation in degrees.

    Elevation 90 looks straight down -Z, which for a pusher in assembly
    position is straight at the front of the plate — the face that carries the
    engraving and the tabs. That is the view worth having, tilted a little so
    the 0.400 mm engraving walls and the 1.500 mm tabs cast a visible edge."""
    a, e = math.radians(az), math.radians(el)
    fwd = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                    -math.sin(e)])
    fwd = fwd / np.linalg.norm(fwd)
    # Near a plan view the world up is almost parallel to the view direction
    # and the basis flips, so switch to +Y well before it degenerates: at 74
    # degrees of elevation the dot product is already 0.96.
    up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(fwd, up)) > 0.85:
        up = np.array([0.0, 1.0, 0.0])
    right = np.cross(fwd, up)
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return right, up, fwd


def render(verts, tris, az, el, width=1400, margin=0.04, light=(-0.4, -0.5, 1.0)):
    """A shaded orthographic image of one mesh, as a PIL Image."""
    v = np.asarray(verts, dtype=float)
    right, up, fwd = _basis(az, el)
    x, y, z = v @ right, v @ up, v @ fwd
    span_x, span_y = x.max() - x.min(), y.max() - y.min()
    pad = margin * max(span_x, span_y)
    scale = (width - 1) / (span_x + 2 * pad)
    height = int(round((span_y + 2 * pad) * scale)) + 1
    px = (x - x.min() + pad) * scale
    py = (span_y - (y - y.min()) + pad) * scale

    t = np.asarray(tris, dtype=int)
    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(p1 - p0, p2 - p0)
    ln = np.linalg.norm(n, axis=1)
    keep = ln > 1e-12
    t, n, ln = t[keep], n[keep], ln[keep]
    n = n / ln[:, None]
    lit = np.asarray(light, dtype=float)
    lit /= np.linalg.norm(lit)
    shade = 0.30 + 0.70 * np.clip(np.abs(n @ lit), 0, 1)

    img = np.full((height, width), float(BG))
    zbuf = np.full((height, width), np.inf)
    ax, ay, az_ = px[t[:, 0]], py[t[:, 0]], z[t[:, 0]]
    bx, by, bz = px[t[:, 1]], py[t[:, 1]], z[t[:, 1]]
    cx, cy, cz = px[t[:, 2]], py[t[:, 2]], z[t[:, 2]]
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    for i in np.argsort(-shade):           # order only affects exact ties
        if abs(area[i]) < 1e-12:
            continue
        x0 = max(int(math.floor(min(ax[i], bx[i], cx[i]))), 0)
        x1 = min(int(math.ceil(max(ax[i], bx[i], cx[i]))) + 1, width)
        y0 = max(int(math.floor(min(ay[i], by[i], cy[i]))), 0)
        y1 = min(int(math.ceil(max(ay[i], by[i], cy[i]))) + 1, height)
        if x1 <= x0 or y1 <= y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        w0 = ((bx[i] - ax[i]) * (gy - ay[i]) - (by[i] - ay[i]) * (gx - ax[i])) / area[i]
        w1 = ((cx[i] - bx[i]) * (gy - by[i]) - (cy[i] - by[i]) * (gx - bx[i])) / area[i]
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w0 + w1 <= 1 + 1e-9)
        if not inside.any():
            continue
        # w0 and w1 are the signed sub-triangle areas over the whole signed
        # area, so they ARE barycentric weights whichever way the triangle
        # winds: w1 belongs to a, w0 to c, and b takes the remainder.
        depth = az_[i] * w1 + bz[i] * (1 - w0 - w1) + cz[i] * w0
        tile_z = zbuf[y0:y1, x0:x1]
        hit = inside & (depth < tile_z)
        tile_z[hit] = depth[hit]
        img[y0:y1, x0:x1][hit] = 255 * shade[i]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "L")


def contact(paths, target, cell=520, cols=4):
    """One grid image of every part's front view — the way to look over a whole
    build in one glance rather than 34 files."""
    from PIL import ImageDraw
    tiles = []
    for path in paths:
        for name, verts, tris in mesh3mf.read(path):
            img = render(verts, tris, 14, 74, cell)
            img.thumbnail((cell, cell))
            tiles.append((f"{path.parent.name}/{path.stem}", img.convert("RGB")))
    bar, gap = 18, 6
    rows = (len(tiles) + cols - 1) // cols
    h = max(t.height for _n, t in tiles) + bar
    canvas = Image.new("RGB", (cols * (cell + gap), rows * (h + gap)),
                       (BG, BG, BG))
    draw = ImageDraw.Draw(canvas)
    for i, (label, img) in enumerate(tiles):
        x, y = (i % cols) * (cell + gap), (i // cols) * (h + gap)
        draw.text((x + 2, y + 3), label, INK)
        canvas.paste(img, (x + (cell - img.width) // 2, y + bar))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)
    return target


def sheet(path, out, width=1200):
    """One PNG per part: front view above, back view below, with a caption."""
    from PIL import ImageDraw
    for name, verts, tris in mesh3mf.read(path):
        views = [render(verts, tris, az, el, width)
                 for az, el in ((14, 74), (-14, -74))]
        gap, bar = 16, 26
        w = max(v.width for v in views)
        h = sum(v.height for v in views) + gap + bar
        canvas = Image.new("L", (w, h), BG)
        y = bar
        for v in views:
            canvas.paste(v, ((w - v.width) // 2, y))
            y += v.height + gap
        canvas = canvas.convert("RGB")
        ImageDraw.Draw(canvas).text((8, 7), f"{path.parent.name}/{path.stem}"
                                            f"   [{name}]  front / back", INK)
        out.mkdir(parents=True, exist_ok=True)
        target = out / f"{path.parent.name} {path.stem}.png"
        canvas.save(target)
        yield target


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent.parent / "tmp" / "render")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--contact", type=Path,
                    help="write ONE grid image of every part's front view here")
    args = ap.parse_args(argv)
    if args.contact:
        print(f"  {contact(args.files, args.contact)}")
        return 0
    for f in args.files:
        for target in sheet(f, args.out, args.width):
            print(f"  {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
