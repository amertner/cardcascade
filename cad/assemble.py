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


def _all(path):
    """Every object in a component 3MF. A Lid is up to 31 of them: the body and
    one inlay per region of its logo pattern, all in the same frame, so they
    all take the lid's placement and the pattern shows in a bottom view."""
    return mesh3mf.read(path)


def lid_meshes(p, d, out_dir, folder):
    path = out_dir / folder / B.lid_file(d)
    if not path.exists():
        B.build_lid(p, out_dir, folder, path.name)
    return _all(path)


def token_holder_mesh(p, d, out_dir, folder, half=False):
    path = out_dir / folder / B.token_holder_file(d, half)
    if not path.exists():
        B.build_token_holder(p, half, out_dir, folder, path.name)
    return _one(path)


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


class MissingHolder(Exception):
    """No cached holder for this row, and no source one to fall back on.

    Not a bug and not rare: `Holder M-21-r6-Un (first)` has never been exported
    from Onshape, so the two `M6.21.10-12` cascades have no first-riser holder
    on disk at all. Substituting the standard holder would put a part of the
    wrong DEPTH under the fit test, which is worse than saying so. So the
    cascade is skipped and named — and `--holder source` is the way through it,
    at the cost of a Holder that is ~2 % heavy.
    """


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


def holder_mesh(p, d, folder, first=False, source=False):
    """The holder an assembly places, in its part frame.

    Cached by default: the source Holder is ~2 % heavy and not printable
    (`spec/HOLDER.md`), so an assembly built on it would report the Holder's own
    defect as the assembly's. `source=True` builds it from `cad/parts/holder`
    anyway, which is how that convergence gets watched — and is the only way to
    assemble the two `M6.21.10-12` cascades at all, their first-riser holder
    never having been exported.
    """
    if source:
        from .parts import holder as holder_part
        part = holder_part.build(p, first)
        name = "FirstHolder" if first else "Holder"
        return (name, *mesh3mf.triangulate(part))
    path = ROOT / "individual" / folder / holder_file(p, d, first)
    if not path.exists():
        raise MissingHolder(
            f"no cached {path.name} in individual/{folder}")
    return _one(path)


def assemble(p, d, state, folder, out_dir, take_tokens=False,
             half=False, holder_source=False):
    """(parts, instances) for one cascade — `parts` the distinct meshes,
    `instances` [(part index, Place)]."""
    parts, instances = [], []

    def add(mesh, places):
        parts.append((mesh[0], (mesh[1], mesh[2])))
        instances.extend((len(parts) - 1, pl) for pl in places)

    add(box_mesh(p, d, out_dir, folder), [A.box(p, d)])

    closed = state in (A.CLOSED, A.CLOSED_LID)
    if closed:
        add(pusher_mesh(p, d, out_dir, folder),
            [A.pusher_stored(p, d, k) for k in A.pushers(p, d)])
    else:
        add(pusher_mesh(p, d, out_dir, folder),
            [A.pusher_socketed(p, d, s) for s in A.play_sockets(p, d)])

    place = A.holder_closed if closed else A.holder_play
    for first in (False, True):
        js = [j for j, f in A.holders(p, d) if f == first]
        if js:
            add(holder_mesh(p, d, folder, first, holder_source),
                [place(p, d, j) for j in js])

    # The token holder is the FULL one: a merged cascade ships a HALF as well,
    # but the two are alternatives for one slot, not both at once — see
    # `assembly.token_holder`. A row with no `TokenHolder` gets neither.
    if take_tokens and p.GameName == "Dominion":
        # A merged row ships a HALF as well, and the two are alternatives for
        # one slot rather than both at once — `assembly.token_holder`. Same
        # placement either way; only the mesh differs.
        add(token_holder_mesh(p, d, out_dir, folder,
                              half=half and bool(p.MatPocket)),
            [A.token_holder(p, d)])

    if state == A.CLOSED_LID:
        for mesh in lid_meshes(p, d, out_dir, folder):
            add(mesh, [A.lid_closed(p, d)])
    elif state == A.PLAY:
        for mesh in lid_meshes(p, d, out_dir, folder):
            add(mesh, [A.lid_under(p, d)])
    return parts, instances


def catalogue(csv=CSV, game=None, model=None):
    """[(folder, Primary, tokens)] — every cascade, both sleevings.

    `tokens` is parts.csv's own `TokenHolder` column, which is per ROW and not
    derivable from the geometry: only the sets whose expansions need one carry
    it (`plan_exports.compose`)."""
    out = []
    for row in params.load_rows(csv):
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            d = D.derive(p)
            if game and p.GameName.lower() != game.lower():
                continue
            if model and model not in B.box_file(d):
                continue
            tokens = (row.get("TokenHolder") or "").strip().lower()
            out.append((params.GAME_NAME.get((row.get("Game") or "").strip(),
                                             p.GameName), p,
                        tokens not in ("", "none")))
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
    ap.add_argument("--holder", choices=("cached", "source"), default="cached",
                    help="where the Holder comes from. Cached by default: the "
                         "source one is ~2%% heavy and not printable, so it "
                         "would report its own defect as the assembly's")
    ap.add_argument("--half", action="store_true",
                    help="on a merged row, place the HALF token holder instead "
                         "of the FULL — they are alternatives for one slot")
    args = ap.parse_args(argv)

    rows = catalogue(args.csv, args.game, args.model)
    states = A.STATES if args.state == "all" else (args.state,)
    if args.list:
        for folder, p, _tk in rows:
            print(f"  {folder}/{D.derive(p).calModelName}")
        print(f"\n  {len(rows)} cascade{'' if len(rows) == 1 else 's'}")
        return 0

    print(f"  holders: {args.holder}"
          + ("   (the source Holder is ~2% heavy — spec/HOLDER.md)"
             if args.holder == "source" else ""))
    print(f"  {'file':52s} {'parts':>6s} {'inst':>5s} {'tris':>8s} {'KB':>6s}")
    skipped = []
    for folder, p, tokens in rows:
        d = D.derive(p)
        for state in states:
            try:
                parts, instances = assemble(p, d, state, folder, args.out,
                                            take_tokens=tokens,
                                            half=args.half,
                                            holder_source=args.holder == "source")
            except MissingHolder as e:
                skipped.append(f"{folder}/{d.calModelName}: {e}")
                break
            stem = B.box_file(d)[len("Box "):-len(".3mf")]
            path = args.out / "assemblies" / folder / f"{stem} {state}.3mf"
            meshed = mesh3mf.write_assembly(path, parts, instances,
                                            name=f"{stem} {state}")
            tris = sum(len(t) for _n, _v, t in meshed)
            print(f"  {folder + '/' + path.name:52s} {len(parts):6d} "
                  f"{len(instances):5d} {tris:8d} {path.stat().st_size / 1024:6.0f}")
    for s in skipped:
        print(f"  skip  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
