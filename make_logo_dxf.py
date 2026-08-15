#!/usr/bin/env python3
"""Lift a game's logo artwork out of a finished label 3MF into a DXF.

The logos we are given are messy - stray outliers, overlapping curves -
and the clean-up happens in Onshape, on the imported mesh, not in the
original DXF. The good copy of the artwork is therefore whatever is
printed on a label that was already made, so this reads that label's
mesh, chains the boundary of the logo's top faces into closed loops,
simplifies the tessellation and writes the loops out as a DXF for
labelmaker to fill and extrude (see its load_art).

    python3 make_logo_dxf.py "cascades/Compile/Compile Labels.3mf" \
            logos/Compile/compile_logo_clean.dxf --preview /tmp/logo.svg

The label to lift from is picked automatically: the object with the
largest artwork on it. Pass --object to choose another. Check the
--preview SVG before committing the result - a label modelled face-down
lifts mirrored, which the numbers below cannot tell you.

Requires: pip install ezdxf build123d
"""

import argparse
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import ezdxf

NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
LABEL_HEIGHT = 22.2      # every label is this tall: it identifies the axes
RAISED_MIN = 0.5         # a face this far above the plate is raised detail
LEVEL_TOL = 0.01
MIN_ART_VERTICES = 100   # fewer than this on a level: not the artwork


def read_objects(path: Path):
    """Every mesh in the 3MF as (name, vertices, triangles)."""
    with zipfile.ZipFile(path) as zf:
        for entry in zf.namelist():
            if not entry.endswith(".model"):
                continue
            root = ET.fromstring(zf.read(entry))
            for obj in root.iter(f"{NS}object"):
                verts = [(float(v.get("x")), float(v.get("y")), float(v.get("z")))
                         for v in obj.iter(f"{NS}vertex")]
                tris = [(int(t.get("v1")), int(t.get("v2")), int(t.get("v3")))
                        for t in obj.iter(f"{NS}triangle")]
                if verts and tris:
                    yield f"{Path(entry).name}:{obj.get('id')}", verts, tris


def label_axes(verts):
    """(thickness, across, up) axis indices of a label lying in any plane."""
    extent = [max(v[i] for v in verts) - min(v[i] for v in verts)
              for i in range(3)]
    thickness = min(range(3), key=lambda i: extent[i])
    plane = [i for i in range(3) if i != thickness]
    up = min(plane, key=lambda i: abs(extent[i] - LABEL_HEIGHT))
    return thickness, [i for i in plane if i != up][0], up


def art_level(verts, thickness):
    """The thickness coordinate of the logo's top faces.

    The raised detail stands proud of the plate, so it owns one of the
    two extreme levels. Which one depends on how the label was modelled,
    so try both, top first, and skip the level that turns out to be the
    plate's outer face - a bare rectangle, which gives itself away by its
    handful of vertices. Levels in between hold the underside of the
    detail and the shorter marks, never the logo alone."""
    levels = {}
    for v in verts:
        levels[round(v[thickness], 2)] = levels.get(round(v[thickness], 2), 0) + 1
    if not levels:
        return None
    for level in (max(levels), min(levels)):
        if levels[level] >= MIN_ART_VERTICES:
            return level
    return None


def boundary_loops(verts, tris, thickness, level):
    """Closed loops around the triangles lying in the artwork's plane."""
    flat = [t for t in tris
            if all(abs(verts[i][thickness] - level) < LEVEL_TOL for i in t)]
    edges = {}
    for a, b, c in flat:
        for edge in ((a, b), (b, c), (c, a)):
            key = (min(edge), max(edge))
            edges[key] = edges.get(key, 0) + 1
    neighbours = {}
    for a, b in (e for e, n in edges.items() if n == 1):   # unshared = border
        neighbours.setdefault(a, []).append(b)
        neighbours.setdefault(b, []).append(a)
    loops, seen = [], set()
    for start in neighbours:
        if start in seen:
            continue
        loop, current, previous = [start], start, None
        seen.add(start)
        while True:
            options = [v for v in neighbours[current] if v != previous]
            options = [v for v in options if v not in seen] or options
            if not options or options[0] == start:
                break
            current, previous = options[0], current
            loop.append(current)
            seen.add(current)
        if len(loop) > 2:
            loops.append(loop)
    return flat, loops


def flat_area(verts, tris, across, up):
    """Area of the artwork's top faces - what the DXF should come to."""
    total = 0.0
    for a, b, c in tris:
        (x0, y0) = verts[a][across], verts[a][up]
        (x1, y1) = verts[b][across], verts[b][up]
        (x2, y2) = verts[c][across], verts[c][up]
        total += abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2
    return total


def simplify(points, tolerance):
    """Douglas-Peucker on a closed loop, iteratively (loops run long)."""
    closed = points + [points[0]]
    keep = [False] * len(closed)
    keep[0] = keep[-1] = True
    stack = [(0, len(closed) - 1)]
    while stack:
        first, last = stack.pop()
        if last <= first + 1:
            continue
        (x0, y0), (x1, y1) = closed[first], closed[last]
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        worst, index = 0.0, first
        for i in range(first + 1, last):
            x, y = closed[i]
            if length < 1e-12:
                far = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
            else:
                far = abs(dy * x - dx * y + x1 * y0 - y1 * x0) / length
            if far > worst:
                worst, index = far, i
        if worst > tolerance:
            keep[index] = True
            stack += [(first, index), (index, last)]
    return [p for p, k in zip(closed[:-1], keep[:-1]) if k]


def write_svg(loops, path: Path):
    """Even-odd fill of the loops, to eyeball the lifted artwork."""
    xs = [p[0] for loop in loops for p in loop]
    ys = [p[1] for loop in loops for p in loop]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    pad = 0.05 * w
    d = "".join(
        "M " + " L ".join(f"{x - min(xs) + pad:.3f},{max(ys) - y + pad:.3f}"
                          for x, y in loop) + " Z " for loop in loops)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{(w + 2 * pad) * 20:.0f}" height="{(h + 2 * pad) * 20:.0f}" '
        f'viewBox="0 0 {w + 2 * pad:.2f} {h + 2 * pad:.2f}">'
        f'<rect width="100%" height="100%" fill="white"/>'
        f'<path d="{d}" fill="black" fill-rule="evenodd"/></svg>')


def verify(path: Path, expected: float):
    """Re-read the DXF the way labelmaker will and compare filled area."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from labelmaker import load_art
    except ImportError as exc:                       # build123d missing
        print(f"  (skipping check: {exc})")
        return
    art = load_art(path)
    area = sum(f.area for f in art.faces())
    box = art.bounding_box()
    print(f"  fills as {len(art.faces())} faces, {box.size.X:.2f} x "
          f"{box.size.Y:.2f} mm, area {area:.2f} mm2 "
          f"({100 * (area - expected) / expected:+.2f}% vs the mesh)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", type=Path, help="3MF holding a finished label")
    ap.add_argument("output", type=Path, help="DXF to write")
    ap.add_argument("--object", help="mesh to lift from (default: the one "
                                     "carrying the largest artwork)")
    ap.add_argument("--tolerance", type=float, default=0.008,
                    help="polyline simplification, mm (default 0.008)")
    ap.add_argument("--preview", type=Path, help="also write an SVG to check")
    args = ap.parse_args()

    candidates = []
    for name, verts, tris in read_objects(args.source):
        if args.object and args.object not in name:
            continue
        thickness, across, up = label_axes(verts)
        level = art_level(verts, thickness)
        if level is None:
            continue
        flat, loops = boundary_loops(verts, tris, thickness, level)
        if not loops:
            continue
        points = [[(verts[i][across], verts[i][up]) for i in loop]
                  for loop in loops]
        xs = [p[0] for loop in points for p in loop]
        ys = [p[1] for loop in points for p in loop]
        size = (max(xs) - min(xs), max(ys) - min(ys))
        candidates.append((size[0] * size[1], name, points, size,
                           flat_area(verts, flat, across, up),
                           (min(xs), min(ys))))
    if not candidates:
        sys.exit(f"{args.source}: no raised artwork found"
                 + (f" on {args.object!r}" if args.object else ""))
    _, name, points, size, area, origin = max(candidates)
    print(f"{args.source} -> {name}: artwork {size[0]:.2f} x {size[1]:.2f} mm, "
          f"{len(points)} loops, {sum(len(p) for p in points)} points, "
          f"{area:.2f} mm2")

    loops = [[(x - origin[0], y - origin[1]) for x, y in loop]
             for loop in points]
    simple = [simplify(loop, args.tolerance) for loop in loops]
    print(f"  simplified to {sum(len(loop) for loop in simple)} points "
          f"at {args.tolerance:g} mm")

    doc = ezdxf.new()
    for loop in simple:
        doc.modelspace().add_lwpolyline(loop, close=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(args.output)
    print(f"  wrote {args.output}")
    if args.preview:
        write_svg(simple, args.preview)
        print(f"  wrote {args.preview} - check it is not mirrored")
    verify(args.output, area)


if __name__ == "__main__":
    main()
