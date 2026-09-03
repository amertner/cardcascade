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
    """A shaded orthographic image of ONE mesh, as an 8-bit PIL Image.

    Kept as it was, because the pusher and box sheets are tuned on it. An
    assembly goes through `scene`, which is the same rasteriser in colour."""
    return scene([(verts, tris, None)], az, el, width, margin, light
                 ).convert("L")


def scene(items, az, el, width=1400, margin=0.04, light=(-0.4, -0.5, 1.0),
          perspective=None):
    """A shaded image of SEVERAL meshes sharing one z-buffer, as an RGB Image.

    `items` is [(verts, tris, colour)], `colour` an (r, g, b) or None for the
    plain grey the single-part views use. One buffer is the point: an assembly
    is only worth looking at if a holder can be hidden behind a box wall.

    `perspective` is the camera's distance as a multiple of the scene's own
    size — `None` for the orthographic views, and about 2.5 for a shot with
    some depth in it. The divide happens in camera space, so the z-buffer is
    unaffected and near faces simply come out bigger.
    """
    right, up, fwd = _basis(az, el)
    vs = [np.asarray(v, dtype=float) for v, _t, _c in items]
    allv = np.concatenate(vs)
    cx, cy, cz = allv @ right, allv @ up, allv @ fwd
    depth0 = cz.max() + perspective * max(
        cx.max() - cx.min(), cy.max() - cy.min(), cz.max() - cz.min()
        ) if perspective else 0.0

    def project(v):
        x, y, z = v @ right, v @ up, v @ fwd
        if perspective:
            f = perspective and (depth0 - cz.mean())
            k = f / np.clip(depth0 - z, 1e-6, None)
            return x * k, y * k, z
        return x, y, z

    proj = [project(v) for v in vs]
    px_all = np.concatenate([p[0] for p in proj])
    py_all = np.concatenate([p[1] for p in proj])
    span_x = px_all.max() - px_all.min()
    span_y = py_all.max() - py_all.min()
    pad = margin * max(span_x, span_y)
    scale = (width - 1) / (span_x + 2 * pad)
    height = int(round((span_y + 2 * pad) * scale)) + 1
    x0, y0 = px_all.min(), py_all.min()

    img = np.full((height, width, 3), float(BG))
    zbuf = np.full((height, width), np.inf)
    lit = np.asarray(light, dtype=float)
    lit /= np.linalg.norm(lit)
    for (verts, tris, colour), v, (cxp, cyp, czp) in zip(items, vs, proj):
        _paint(img, zbuf, v, tris, cxp, cyp, czp, x0, y0, span_y, pad, scale,
               width, height, lit, colour)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def _paint(img, zbuf, v, tris, cxp, cyp, czp, x0, y0, span_y, pad, scale,
           width, height, lit, colour):
    """One mesh into a shared colour buffer and z-buffer.

    Flat per-triangle Lambert, painted brightest first so that exact ties are
    stable; the z-buffer does the rest, which is what lets a holder disappear
    behind a box wall.
    """
    px = (cxp - x0 + pad) * scale
    py = (span_y - (cyp - y0) + pad) * scale
    z = czp
    tint = (np.asarray(colour, dtype=float) / 255.0 if colour is not None
            else np.ones(3))

    t = np.asarray(tris, dtype=int)
    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(p1 - p0, p2 - p0)
    ln = np.linalg.norm(n, axis=1)
    keep = ln > 1e-12
    t, n, ln = t[keep], n[keep], ln[keep]
    n = n / ln[:, None]
    shade = 0.30 + 0.70 * np.clip(np.abs(n @ lit), 0, 1)

    ax, ay, az_ = px[t[:, 0]], py[t[:, 0]], z[t[:, 0]]
    bx, by, bz = px[t[:, 1]], py[t[:, 1]], z[t[:, 1]]
    cx, cy, cz = px[t[:, 2]], py[t[:, 2]], z[t[:, 2]]
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    for i in np.argsort(-shade):           # order only affects exact ties
        if abs(area[i]) < 1e-12:
            continue
        tx0 = max(int(math.floor(min(ax[i], bx[i], cx[i]))), 0)
        tx1 = min(int(math.ceil(max(ax[i], bx[i], cx[i]))) + 1, width)
        ty0 = max(int(math.floor(min(ay[i], by[i], cy[i]))), 0)
        ty1 = min(int(math.ceil(max(ay[i], by[i], cy[i]))) + 1, height)
        if tx1 <= tx0 or ty1 <= ty0:
            continue
        gx, gy = np.meshgrid(np.arange(tx0, tx1) + 0.5,
                             np.arange(ty0, ty1) + 0.5)
        w0 = ((bx[i] - ax[i]) * (gy - ay[i]) - (by[i] - ay[i]) * (gx - ax[i])) / area[i]
        w1 = ((cx[i] - bx[i]) * (gy - by[i]) - (cy[i] - by[i]) * (gx - bx[i])) / area[i]
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w0 + w1 <= 1 + 1e-9)
        if not inside.any():
            continue
        # w0 and w1 are the signed sub-triangle areas over the whole signed
        # area, so they ARE barycentric weights whichever way the triangle
        # winds: w1 belongs to a, w0 to c, and b takes the remainder.
        depth = az_[i] * w1 + bz[i] * (1 - w0 - w1) + cz[i] * w0
        tile_z = zbuf[ty0:ty1, tx0:tx1]
        hit = inside & (depth < tile_z)
        tile_z[hit] = depth[hit]
        img[ty0:ty1, tx0:tx1][hit] = 255 * shade[i] * tint


# The six named cameras, in the BOX's frame: +Y is the back of the cascade, +Z
# up. `_basis` points the camera ALONG `fwd`, so the view named for a face is
# the azimuth that looks at it — front is 180, not 0.
VIEWS = {
    "front":  (180, 0),
    "back":   (0, 0),
    "left":   (90, 0),
    "right":  (270, 0),
    "top":    (0, 90),
    "bottom": (0, -90),
    "hero":   (206, 24),        # front, left and above — the perspective one
}
HERO = "hero"
PERSPECTIVE = 2.6              # camera distance as a multiple of the scene's size

# One colour per component, so a render says what it is showing. Deliberately
# not the print's own white-and-black: two white parts against a white part is
# the one thing a shaded render cannot separate.
PART_COLOURS = {
    "Box": (108, 142, 178),
    "Lid": (128, 170, 132),
    "Pusher": (214, 154, 92),
    "Holder": (226, 226, 226),
    "FirstHolder": (206, 206, 206),
    "TokenHolder": (196, 138, 168),
    "HalfTokenHolder": (176, 124, 152),
    "Topper": (176, 186, 208),
}
DEFAULT_COLOUR = (200, 200, 200)


def colour_for(name):
    """A component's colour, matched on the name a part is written under."""
    return PART_COLOURS.get(name or "", DEFAULT_COLOUR)


def assembly_sheet(path, out, width=1600, views=None):
    """One PNG per named view of an assembly 3MF, coloured per component."""
    from PIL import ImageDraw
    items = [(v, tr, colour_for(n)) for n, v, tr in mesh3mf.read_assembly(path)]
    for view in views or list(VIEWS):
        az, el = VIEWS[view]
        img = scene(items, az, el, width,
                    perspective=PERSPECTIVE if view == HERO else None)
        img = img.convert("RGB")
        ImageDraw.Draw(img).text((8, 7), f"{path.stem}   [{view}]", INK)
        out.mkdir(parents=True, exist_ok=True)
        target = out / f"{path.stem} {view}.png"
        img.save(target)
        yield target


PUSHER_VIEWS = ((14, 74), (-14, -74))
# A box is TALL, so the near-plan view a pusher wants reads as a squashed
# ribbon. These two show it: a three-quarter from above the front-left, which
# is where the pocket, the sliders and the rear storage are all visible at
# once, and a plan.
BOX_VIEWS = ((38, 26), (10, 86))


def contact(paths, target, cell=520, cols=4, views=(PUSHER_VIEWS[0],)):
    """One grid image of every part, one tile per view — the way to look over a
    whole build in one glance rather than 34 files."""
    from PIL import ImageDraw
    tiles = []
    for path in paths:
        for name, verts, tris in mesh3mf.read(path):
            for az, el in views:
                img = render(verts, tris, az, el, cell)
                img.thumbnail((cell, cell))
                label = f"{path.parent.name}/{path.stem}"
                if len(views) > 1:
                    label += f"  [{az},{el}]"
                tiles.append((label, img.convert("RGB")))
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


def sheet(path, out, width=1200, views=PUSHER_VIEWS):
    """One PNG per part: one view above the next, with a caption."""
    from PIL import ImageDraw
    for name, verts, tris in mesh3mf.read(path):
        # NB not `views = [...]`: a file with more than one object comes round
        # again, and rebinding leaves the camera list holding Images.
        shots = [render(verts, tris, az, el, width) for az, el in views]
        gap, bar = 16, 26
        w = max(v.width for v in shots)
        h = sum(v.height for v in shots) + gap + bar
        canvas = Image.new("L", (w, h), BG)
        y = bar
        for v in shots:
            canvas.paste(v, ((w - v.width) // 2, y))
            y += v.height + gap
        canvas = canvas.convert("RGB")
        ImageDraw.Draw(canvas).text((8, 7), f"{path.parent.name}/{path.stem}"
                                            f"   [{name}]", INK)
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
                    help="write ONE grid image of every part here")
    ap.add_argument("--view", action="append", metavar="AZ,EL",
                    help="camera azimuth,elevation in degrees; repeatable. "
                         "Defaults suit a PUSHER; use --box for a box.")
    ap.add_argument("--box", action="store_true",
                    help=f"shorthand for the box views {BOX_VIEWS}")
    ap.add_argument("--assembly", action="store_true",
                    help="an assembly 3MF: the six named views plus the hero, "
                         "one PNG each, coloured per component")
    args = ap.parse_args(argv)

    if args.assembly:
        for f in args.files:
            for target in assembly_sheet(f, args.out, args.width):
                print(f"  {target}")
        return 0
    views = [tuple(float(n) for n in v.split(",")) for v in args.view or []]
    if not views:
        views = list(BOX_VIEWS if args.box else PUSHER_VIEWS)
    if args.contact:
        print(f"  {contact(args.files, args.contact, views=views)}")
        return 0
    for f in args.files:
        for target in sheet(f, args.out, args.width, views):
            print(f"  {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
