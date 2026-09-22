#!/usr/bin/env python3
"""Assemble a whole cascade into one 3MF. ZERO Onshape API calls.

    .venv/bin/python -m cad.assemble --model S4.16.10.32-Un
    .venv/bin/python -m cad.assemble --game Dominion --state closed
    .venv/bin/python -m cad.assemble --list

`cad/assembly.py` says where each part goes; this puts the meshes there, into
`build/assemblies/<Game>/<model> <state>.3mf`, written the way Onshape's own
`_raw` assemblies are. **It must never be written into `individual/`**:
`make_cascade.load_export` refuses a build item carrying a transform, and an
assembly is made of them.

Every part is taken in its PART frame; a **Pusher** in `build/` carries
`pusher.assembly_offset` and is corrected HERE, not in the placement. Anything
missing from `build/` is built on the spot, and the **Toppers** are the one
part still read from `individual/`.
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
from .revisions import CURRENT, RELEASES

pusher_part = lazy(".parts.pusher", __package__)

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "automation" / "parts.csv"


def shifted(mesh, by):
    name, verts, tris = mesh
    dx, dy, dz = by
    return (name, [(x + dx, y + dy, z + dz) for x, y, z in verts], tris)


def _body(objects):
    """The part among a component's objects: the BIGGEST, a Lid's inlays being
    objects too."""
    return max(objects, key=lambda o: len(o[1]))


def _one(path):
    return _body(mesh3mf.read(path))


def _all(path):
    """Every object in a component 3MF, the inlays named after their body: an
    ASSEMBLY holds a Lid's inlays and six Toppers' together and a render
    colours the two sets differently, so here they are QUALIFIED — `Lid Part
    7`, `Topper Cities Part 7`."""
    objects = mesh3mf.read(path)
    body = _body(objects)[0]
    return [(n if n == body else f"{body} {n}", v, t) for n, v, t in objects]


def _built(path, build, d, extra=None):
    """`path` under build/, built by `build` first if it is not there yet."""
    if not path.exists():
        build(d, extra, path)
    return path


def lid_meshes(d, out_dir, folder):
    """The cascade's FIRST lid (`build.lid_variants_built`): its own, or the
    unmarked one for a GENERIC game, which ships no other."""
    variant = B.lid_variants_built(d)[0]
    return _all(_built(out_dir / folder / B.lid_file(d, variant), B.build_lid, d,
                       variant))


def token_holder_mesh(d, out_dir, folder, half=False):
    return _one(_built(out_dir / folder / B.token_holder_file(d, half),
                       B.build_token_holder, d, half))


def box_mesh(d, out_dir, folder):
    return _one(_built(out_dir / folder / B.box_file(d), B.build_box, d))


def pusher_mesh(d, out_dir, folder):
    path = _built(out_dir / folder / B.pusher_file(d), B.build_pusher, d)
    ox, oy, oz = pusher_part.assembly_offset(d)
    return shifted(_one(path), (-ox, -oy, -oz))


class MissingCached(Exception):
    """No cached topper in `individual/` for this row: the cascade is skipped
    and named, not assembled without them."""


def holder_mesh(d, out_dir, folder, first=False, rear=False):
    """The holder an assembly places, in its part frame: `cad.build`'s, built
    first if it is not there yet. `first` is the deep one, `rear` the
    RearHolder."""
    return _one(_built(out_dir / folder / B.holder_file(d, first, rear),
                       B.build_holder, d, (first, rear)))


# The six Innovation toppers, one per riser back to front. Nothing in the
# geometry picks which expansion goes where; a longer cascade repeats.
TOPPERS = ("Cities", "Echoes", "Artifacts", "Figures", "Unseen", "Blank")


def topper_meshes(d, folder, expansion):
    """Every object in a topper: the body AND its lettering. `_all`, not
    `_one` — taking only the body leaves the POCKETS, which read as text in a
    shaded render and are not."""
    path = ROOT / "individual" / folder / B.topper_file(d, expansion)
    if not path.exists():
        raise MissingCached(f"no cached {path.name} in individual/{folder}")
    return _all(path)


def topper_risers(d, toppers=False):
    """[(riser, first)] that carry a topper: every riser where the row ships
    them (`build.ships_toppers`)."""
    return A.holders(d) if toppers else []


# The set number on a card stack's front face, for `--cards`: this far proud
# of the front card, its cap top this far below the card's top edge.
CARD_LABEL_PROUD = 0.300
CARD_LABEL_DROP = 1.000


def card_meshes(d, state, sets=None):
    """`[(name, shape)]` — one box per card stack and one numeral per stack, in
    the cascade frame (`assembly.card_fill`), named `Cards <expansion> <set>`
    and `Cards Label <expansion> <set>`, which `cad.gltf` colours by."""
    # Lazily, like every other build123d user here: `cad.assemble --list` must
    # import none of it (`tests/test_smoke.py`), and `cad.text` does.
    from build123d import Axis, Box, Location
    from . import text as T
    from .geom import text_solid

    out = []
    cap = A.card_label_cap(d)
    size = cap / T.CAP
    for slot, name, n, count in A.card_fill(d, sets):
        x0, x1, y0, y1, z0, z1 = A.card_stack(d, slot, count, state)
        stack = Box(x1 - x0, y1 - y0, z1 - z0).moved(
            Location(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))
        out.append((f"Cards {name} {n}", stack))
        txt = A.card_set_label(n)
        adv, _lsb, _lo, _hi = T.metrics(txt, T.LOGO_FONT)
        # Drawn flat in XY and stood up: a quarter turn about X takes the
        # glyph's height to +Z and its extrusion to -Y, proud of the face.
        glyph = text_solid(txt, T.LOGO_FONT, size, CARD_LABEL_PROUD)
        glyph = glyph.rotate(Axis.X, 90).moved(Location((
            (x0 + x1) / 2 - adv * size / 2, y0, z1 - CARD_LABEL_DROP - cap)))
        out.append((f"Cards Label {name} {n}", glyph))
    return out


def assemble(d, state, folder, out_dir, take_tokens=False,
             half=False, toppers=False, cards=None, topper_order=TOPPERS):
    """(parts, instances) for one cascade — `parts` the distinct meshes,
    `instances` [(part index, Place)]. `cards` is None or the expansion names
    to fill the slots with; `topper_order` is the expansion per riser, `j = 0`
    the back one."""
    parts, instances = [], []

    def add(mesh, places):
        parts.append((mesh[0], (mesh[1], mesh[2])))
        instances.extend((len(parts) - 1, pl) for pl in places)

    add(box_mesh(d, out_dir, folder), [A.box(d)])

    closed = state in (A.CLOSED, A.CLOSED_LID)
    if closed:
        add(pusher_mesh(d, out_dir, folder),
            [A.pusher_stored(d, k) for k in A.pushers(d)])
    else:
        add(pusher_mesh(d, out_dir, folder),
            [A.pusher_socketed(d, s) for s in A.play_sockets(d)])

    place = A.holder_closed if closed else A.holder_play
    for (first, rear), js in A.holder_kinds(d):
        add(holder_mesh(d, out_dir, folder, first, rear),
            [place(d, j) for j in js])

    # Toppers — one per riser, only where the row has them
    # (`build.ships_toppers`). Each is its own cached component, so each is its
    # own mesh with one instance; the expansion order is arbitrary.
    for j, first in topper_risers(d, toppers):
        pl = (A.topper if closed else A.topper_play)(d, j, first)
        for mesh in topper_meshes(d, folder, topper_order[j % len(topper_order)]):
            add(mesh, [pl])

    # The token holder is the FULL one: the HALF is an ALTERNATIVE for the same
    # slot, at the same placement (`assembly.token_holder`).
    if take_tokens and d.GameName == "Dominion":
        add(token_holder_mesh(d, out_dir, folder,
                              half=half and bool(d.MatPocket)),
            [A.token_holder(d)])

    if state == A.CLOSED_LID:
        for mesh in lid_meshes(d, out_dir, folder):
            add(mesh, [A.lid_closed(d)])
    elif state == A.PLAY:
        for mesh in lid_meshes(d, out_dir, folder):
            add(mesh, [A.lid_under(d)])

    # The cards, already in the cascade frame: a shape each, meshed by the
    # writer, with the identity placement.
    if cards is not None:
        for name, shape in card_meshes(d, state, cards):
            parts.append((name, shape))
            instances.append((len(parts) - 1, A.Place()))
    return parts, instances


def catalogue(csv=CSV, game=None, model=None, version=CURRENT):
    """[(folder, Derived, tokens, toppers)] — every cascade, both sleevings.
    `tokens` and `toppers` are per ROW and not derivable from the geometry.
    `version` is the RELEASE assembled: a release can change a part, so the
    mechanism has to be checkable at each."""
    out = []
    for row, p in params.cascades(csv, game, version):
        d = D.derive(p)
        if not B.model_matches(d, model):
            continue
        out.append((d.GameName, d, B.ships_token_holder(row),
                    B.ships_toppers(row, d)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game")
    ap.add_argument("--model", help="e.g. S4.16.10.32-Un")
    ap.add_argument("--state", choices=A.STATES + ("all",), default=A.CLOSED)
    ap.add_argument("--out", default=ROOT / "build", type=Path)
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--version", default=CURRENT, choices=RELEASES,
                    help=f"the release to assemble (default {CURRENT}); a "
                         "release can change a part, so the mechanism is "
                         "checkable at each (cad/revisions.py)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--half", action="store_true",
                    help="on a merged row, place the HALF token holder instead "
                         "of the FULL — they are alternatives for one slot")
    ap.add_argument("--no-toppers", action="store_true",
                    help="assemble without toppers even where the row ships "
                         "them (a row with none cached would otherwise skip)")
    ap.add_argument("--cards", action="store_true",
                    help="fill every slot with a numbered card stack, written "
                         "to `<model> <state> cards.3mf` (assembly.card_fill)")
    ap.add_argument("--sets", help="the expansions the cards belong to, in "
                                   "order, e.g. Echoes,Figures,Unseen "
                                   f"(default: {', '.join(A.INNOVATION_SETS)})")
    args = ap.parse_args(argv)
    sets = ([s.strip() for s in args.sets.split(",") if s.strip()]
            if args.sets else list(A.INNOVATION_SETS)) if args.cards else None

    rows = catalogue(args.csv, args.game, args.model, args.version)
    states = A.STATES if args.state == "all" else (args.state,)
    if args.list:
        for folder, d, _tokens, _toppers in rows:
            print(f"  {folder}/{d.calModelName}")
        print(f"\n  {len(rows)} cascade{'' if len(rows) == 1 else 's'}")
        return 0

    print(f"  {'file':52s} {'parts':>6s} {'inst':>5s} {'tris':>8s} {'KB':>6s}")
    skipped = []
    for folder, d, tokens, toppers in rows:
        for state in states:
            try:
                parts, instances = assemble(d, state, folder, args.out,
                                            take_tokens=tokens,
                                            half=args.half,
                                            toppers=toppers and not args.no_toppers,
                                            cards=sets)
            except MissingCached as e:
                skipped.append(f"{folder}/{d.calModelName}: {e}")
                break
            stem = B.model_stem(d.calModelName)
            label = f"{stem} {state}" + (" cards" if args.cards else "")
            path = args.out / "assemblies" / folder / f"{label}.3mf"
            meshed = mesh3mf.write_assembly(path, parts, instances, name=label)
            tris = sum(len(t) for _n, _v, t in meshed)
            print(f"  {folder + '/' + path.name:52s} {len(parts):6d} "
                  f"{len(instances):5d} {tris:8d} {path.stat().st_size / 1024:6.0f}")
    for s in skipped:
        print(f"  skip  {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
