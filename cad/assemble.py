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

Anything missing from `build/` is built on the spot. The Holder defaults to
the CACHED mesh even though `cad/parts/holder.py` is finished now, because
`individual/` is the geometry that actually shipped and an assembly is a
statement about a real cascade. `--holder source` builds it instead, and is no
longer a compromise — it is also the only way to assemble the two
`M6.21.10-12` cascades, whose first-riser holder was never exported.
"""
import argparse
import sys
from pathlib import Path

from . import assembly as A
from . import build as B
from . import derive as D
from . import mesh3mf
from . import params
from .lazy import lazy

pusher_part = lazy(".parts.pusher", __package__)

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
    """Every object in a component 3MF, the inlays named after their body.

    A Lid is up to 31 objects: the body and one region of its logo pattern
    each, all in the same frame, so they all take the lid's placement and the
    pattern shows. A labelled Topper is the same shape for its lettering.

    `cad/` writes those regions as bare `Part 2`, `Part 3`, ... — which is what
    the hand-exported STEPs carry and what `individual/` has, so it is not
    changed there. But an ASSEMBLY holds a Lid's inlays and six Toppers'
    together, and `Part 7` alone cannot say which body it belongs to. A render
    needs to: on Allan's prints the lid's logo is a contrast on a BLUE lid
    while a topper's lettering is a contrast on a WHITE topper, so the two sets
    are different colours. Here they are qualified — `Lid Part 7`,
    `Topper Cities Part 7` — and the body keeps its own name.
    """
    objects = mesh3mf.read(path)
    body = max(objects, key=lambda o: len(o[1]))[0]
    return [(n if n == body else f"{body} {n}", v, t) for n, v, t in objects]


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
    cascade is skipped and named, and `--holder source` is the way through it.
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

    Cached by default, because `individual/` is what shipped. `source=True`
    builds it from `cad/parts/holder`, which is finished and regressed against
    all 50 cached holders — so it is an equal alternative now rather than a
    compromise, and it is the only way to assemble the two `M6.21.10-12`
    cascades at all, their first-riser holder never having been exported.
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


# The six Innovation toppers, from `components.GAMES["Innovation"]["toppers"]`.
# One per riser in catalogue order, back to front; nothing in the geometry
# picks which expansion goes where, and a cascade with more risers than
# expansions repeats.
TOPPERS = ("Cities", "Echoes", "Artifacts", "Figures", "Unseen", "Blank")

# Rows that carry no toppers, by parts.csv Short name — `components.no_toppers`.
NO_TOPPERS = {"Single Set", "Single Mini"}


def topper_file(p, d, expansion):
    """`plan_exports.compose`'s name: `Topper Cities S15-Un.3mf`. Keyed on the
    cards per slot as well as the size, because a topper's depth is 2.000 plus
    a card thickness per card and a 15-card one will not fit a 10-card slot."""
    slv = "Sl" if p.isSleeved else "Un"
    return (f"Topper {expansion} {d.calSizeLetter}"
            f"{p.CardsPerSlidingSlot}-{slv}.3mf")


def topper_meshes(p, d, folder, expansion):
    """Every object in a topper: the body AND its lettering.

    `_all`, not `_one`. A labelled topper carries its expansion name as inlays
    the same way a Lid carries its logo — `Topper Cities S15-Un.3mf` is a body
    plus nine of them — and taking only the body drops the lettering. What is
    left is the POCKETS the letters sit in, which read as text in a shaded
    render and are not text at all: they would print as bare recesses.
    """
    path = ROOT / "individual" / folder / topper_file(p, d, expansion)
    if not path.exists():
        raise MissingHolder(f"no cached {path.name} in individual/{folder}")
    return _all(path)


def topper_risers(p, d, short_name=None):
    """[(riser, first)] that carry a topper. Innovation only."""
    if p.GameName != "Innovation" or short_name in NO_TOPPERS:
        return []
    return A.holders(p, d)


def assemble(p, d, state, folder, out_dir, take_tokens=False,
             half=False, holder_source=False, short_name=None):
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

    # Toppers — Innovation only, one per riser, and only where the row has them
    # (`components.no_toppers`: a box built for ONE set has nothing for a
    # topper to say). Each is its own cached component, so each is its own mesh
    # with one instance; the expansion order is the catalogue's and is
    # arbitrary as far as the geometry is concerned.
    for j, first in topper_risers(p, d, short_name):
        pl = (A.topper if closed else A.topper_play)(p, d, j, first)
        for mesh in topper_meshes(p, d, folder, TOPPERS[j % len(TOPPERS)]):
            add(mesh, [pl])

    # The token holder is the FULL one: a merged row ships a HALF as well, but
    # the two are alternatives for one slot, not both at once, and the
    # placement is the same either way — `assembly.token_holder`. A row with
    # no `TokenHolder` gets neither.
    if take_tokens and p.GameName == "Dominion":
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
    """[(folder, Primary, tokens, short name)] — every cascade, both sleevings.

    `tokens` is parts.csv's own `TokenHolder` column, which is per ROW and not
    derivable from the geometry: only the sets whose expansions need one carry
    it (`plan_exports.compose`)."""
    out = []
    for row, p in params.cascades(csv, game):
        if not B.model_matches(D.derive(p), model):
            continue
        tokens = (row.get("TokenHolder") or "").strip().lower()
        out.append((p.GameName, p, tokens not in ("", "none"),
                    (row.get("Short name") or "").strip()))
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
                    help="where the Holder comes from. Cached by default, "
                         "because individual/ is what shipped; source builds "
                         "the (now finished) cad/parts/holder instead")
    ap.add_argument("--half", action="store_true",
                    help="on a merged row, place the HALF token holder instead "
                         "of the FULL — they are alternatives for one slot")
    args = ap.parse_args(argv)

    rows = catalogue(args.csv, args.game, args.model)
    states = A.STATES if args.state == "all" else (args.state,)
    if args.list:
        for folder, p, _tk, _sn in rows:
            print(f"  {folder}/{D.derive(p).calModelName}")
        print(f"\n  {len(rows)} cascade{'' if len(rows) == 1 else 's'}")
        return 0

    print(f"  holders: {args.holder}")
    print(f"  {'file':52s} {'parts':>6s} {'inst':>5s} {'tris':>8s} {'KB':>6s}")
    skipped = []
    for folder, p, tokens, short_name in rows:
        d = D.derive(p)
        for state in states:
            try:
                parts, instances = assemble(p, d, state, folder, args.out,
                                            take_tokens=tokens,
                                            half=args.half,
                                            holder_source=args.holder == "source",
                                            short_name=short_name)
            except MissingHolder as e:
                skipped.append(f"{folder}/{d.calModelName}: {e}")
                break
            stem = B.model_stem(d.calModelName)
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
