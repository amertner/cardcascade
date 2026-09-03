#!/usr/bin/env python3
"""Assemble a whole cascade into one 3MF. ZERO Onshape API calls.

    .venv/bin/python -m cad.assemble --model S4.16.10.32-Un
    .venv/bin/python -m cad.assemble --game Dominion --state closed
    .venv/bin/python -m cad.assemble --list

`cad/assembly.py` says where each part goes; this puts the meshes there. Output
is `build/assemblies/<Game>/<model> <state>.3mf`, written the way Onshape's own
`_raw` assemblies are — the component meshes as objects, one object instancing
them with a transform each — so eight holders cost one mesh.

**It must never be written into `individual/`.** `make_cascade.load_export`
refuses a build item carrying a transform, and an assembly is made of them.

## Where the meshes come from

Every part is taken in its PART frame, because that is the frame
`cad/assembly.py` places. Two of the three sources are not in it already and
are corrected here rather than in the placement, which stays a statement about
geometry and not about file formats:

* a **Box** in `build/` is at the part origin — `cad.build` says so;
* a **Pusher** in `build/` carries `pusher.assembly_offset`, the transform an
  Onshape export arrives in, so it is subtracted back off;
* a **Holder** comes from `individual/`, which IS its part frame (checked:
  `Holder S-16-r4-Un` runs Z -45.250.. against `holder.base_z` -45.250, and its
  X centres on `holder.x_span`'s).

Anything missing from `build/` is built on the spot. The Holder is never built:
the source one is ~2 % heavy and not printable (`spec/HOLDER.md`), so the cached
mesh is the default and `--holder=source` is how that gets watched.
"""
import argparse
import sys
from pathlib import Path

from . import assembly as A
from . import build as B
from . import derive as D
from . import mesh3mf
from . import params
from .parts import pusher as pusher_part

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "automation" / "parts.csv"


def shifted(mesh, by):
    """`mesh` moved by `by` — how a file's frame is brought to the part's."""
    name, verts, tris = mesh
    dx, dy, dz = by
    return (name, [(x + dx, y + dy, z + dz) for x, y, z in verts], tris)


def _one(path):
    """The single object in a component 3MF, or the biggest of them — a Lid
    carries its logo inlays as separate objects and the body is the largest."""
    objs = mesh3mf.read(path)
    return max(objs, key=lambda o: len(o[1]))


def box_mesh(p, d, out_dir, folder):
    path = out_dir / folder / B.box_file(d)
    if not path.exists():
        B.build_box(p, out_dir, folder, path.name)
    return _one(path)


def pusher_mesh(p, d, out_dir, folder):
    path = out_dir / folder / B.pusher_file(p)
    if not path.exists():
        B.build_pusher(p, out_dir, folder, path.name)
    ox, oy, oz = pusher_part.assembly_offset(d)
    return shifted(_one(path), (-ox, -oy, -oz))


def holder_file(p, d, first=False):
    """`plan_exports.holder`'s name. Compile and Innovation holders SPAN the
    box, so they are keyed on the horizontal count; the rest are per-slot and
    keyed on the size letter and the front capacity."""
    slv = "Sl" if p.isSleeved else "Un"
    if p.GameName in ("Compile", "Innovation"):
        return (f"Holder {p.HorizontalSlots}x{p.CardsPerSlidingSlot}"
                f"-r{p.RisingSliders}-{slv}.3mf")
    return (f"Holder {d.calSizeLetter}-{p.FrontPocketCardCapacity}"
            f"-r{p.RisingSliders}-{slv}" + (" (first)" if first else "") + ".3mf")


def holder_mesh(p, d, folder, first=False):
    path = ROOT / "individual" / folder / holder_file(p, d, first)
    if not path.exists():
        raise FileNotFoundError(
            f"no cached holder {path.name} in individual/{folder} — the source "
            f"Holder is not printable yet, so there is nothing to fall back on")
    return _one(path)


def assemble(p, d, state, folder, out_dir):
    """(parts, instances) for one cascade — `parts` the distinct meshes,
    `instances` [(part index, Place)]."""
    parts, instances = [], []

    def add(mesh, places):
        parts.append((mesh[0], (mesh[1], mesh[2])))
        instances.extend((len(parts) - 1, pl) for pl in places)

    add(box_mesh(p, d, out_dir, folder), [A.box(p, d)])

    if state in (A.CLOSED, A.CLOSED_LID):
        add(pusher_mesh(p, d, out_dir, folder),
            [A.pusher_stored(p, d, k) for k in A.pushers(p, d)])
        plain = [j for j, first in A.holders(p, d) if not first]
        firsts = [j for j, first in A.holders(p, d) if first]
        if plain:
            add(holder_mesh(p, d, folder),
                [A.holder_closed(p, d, j) for j in plain])
        if firsts:
            add(holder_mesh(p, d, folder, first=True),
                [A.holder_closed(p, d, j) for j in firsts])
    else:
        raise NotImplementedError(f"state {state!r} is not written yet")
    return parts, instances


def catalogue(csv=CSV, game=None, model=None):
    """[(folder, Primary)] — every cascade, both sleevings."""
    out = []
    for row in params.load_rows(csv):
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            d = D.derive(p)
            if game and p.GameName.lower() != game.lower():
                continue
            if model and model not in B.box_file(d):
                continue
            out.append((params.GAME_NAME.get((row.get("Game") or "").strip(),
                                             p.GameName), p))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game")
    ap.add_argument("--model", help="e.g. S4.16.10.32-Un")
    ap.add_argument("--state", choices=A.STATES + ("all",), default=A.CLOSED)
    ap.add_argument("--out", default=ROOT / "build", type=Path)
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)

    rows = catalogue(args.csv, args.game, args.model)
    states = A.STATES if args.state == "all" else (args.state,)
    if args.list:
        for folder, p in rows:
            print(f"  {folder}/{D.derive(p).calModelName}")
        print(f"\n  {len(rows)} cascade{'' if len(rows) == 1 else 's'}")
        return 0

    print(f"  {'file':52s} {'parts':>6s} {'inst':>5s} {'tris':>8s} {'KB':>6s}")
    for folder, p in rows:
        d = D.derive(p)
        for state in states:
            parts, instances = assemble(p, d, state, folder, args.out)
            stem = B.box_file(d)[len("Box "):-len(".3mf")]
            path = args.out / "assemblies" / folder / f"{stem} {state}.3mf"
            meshed = mesh3mf.write_assembly(path, parts, instances,
                                            name=f"{stem} {state}")
            tris = sum(len(t) for _n, _v, t in meshed)
            print(f"  {folder + '/' + path.name:52s} {len(parts):6d} "
                  f"{len(instances):5d} {tris:8d} {path.stat().st_size / 1024:6.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
