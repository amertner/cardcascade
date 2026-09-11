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

Anything missing from `build/` is built on the spot. The Holder and the
Toppers come from `individual/` — the Onshape 7.0 corpus, 30 of whose 50
holders are 6.6 — whatever release is assembled. `--holder source` builds the
holder from `cad/parts/holder.py` instead, as the released cascades print it,
and it is the only way to assemble the two `M6.21.10-12` cascades, whose
first-riser holder was never exported.
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
    """`mesh` moved by `by` — how a file's frame is brought to the part's."""
    name, verts, tris = mesh
    dx, dy, dz = by
    return (name, [(x + dx, y + dy, z + dz) for x, y, z in verts], tris)


def _body(objects):
    """The part among a component's objects: the biggest — a Lid carries its
    logo inlays as separate objects, and its body dwarfs them."""
    return max(objects, key=lambda o: len(o[1]))


def _one(path):
    """The body in a component 3MF."""
    return _body(mesh3mf.read(path))


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
    body = _body(objects)[0]
    return [(n if n == body else f"{body} {n}", v, t) for n, v, t in objects]


def _built(path, build, d, extra=None):
    """`path` under build/, built by `build` (a `cad.build` builder) first if
    it is not there yet."""
    if not path.exists():
        build(d, extra, path)
    return path


def lid_meshes(d, out_dir, folder):
    return _all(_built(out_dir / folder / B.lid_file(d), B.build_lid, d))


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
    """No cached component in `individual/` for this row — a holder with no
    source one to fall back on, or a topper.

    Not a bug and not rare: `Holder M-21-r6-Un (first)` has never been exported
    from Onshape, so the two `M6.21.10-12` cascades have no first-riser holder
    on disk at all. Substituting the standard holder would put a part of the
    wrong DEPTH under the fit test, which is worse than saying so. So the
    cascade is skipped and named, and `--holder source` is the way through it.
    """


def holder_file(d, first=False):
    """`plan_exports.holder`'s name for the CACHED holder in `individual/` —
    NOT `build.holder_file`, which names the rebuilt one by its model code.
    Compile and Innovation holders SPAN the box, so they are keyed on the
    horizontal count; the rest are per-slot and keyed on the size letter and
    the front capacity."""
    slv = "Sl" if d.isSleeved else "Un"
    if d.GameName in ("Compile", "Innovation"):
        return (f"Holder {d.HorizontalSlots}x{d.CardsPerSlidingSlot}"
                f"-r{d.RisingSliders}-{slv}.3mf")
    return (f"Holder {d.calSizeLetter}-{d.FrontPocketCardCapacity}"
            f"-r{d.RisingSliders}-{slv}" + (" (first)" if first else "") + ".3mf")


def holder_mesh(d, folder, first=False, source=False):
    """The holder an assembly places, in its part frame.

    Cached by default — `individual/`'s, the Onshape 7.0 corpus. `source=True`
    builds it from `cad/parts/holder`, regressed against all 50 cached holders
    and what the released cascades print; it is the only way to assemble the
    two `M6.21.10-12` cascades, their first-riser holder never having been
    exported.
    """
    if source:
        from .parts import holder as holder_part
        part = holder_part.build(d, first)
        name = "FirstHolder" if first else "Holder"
        return (name, *mesh3mf.triangulate(part))
    path = ROOT / "individual" / folder / holder_file(d, first)
    if not path.exists():
        raise MissingCached(
            f"no cached {path.name} in individual/{folder}")
    return _one(path)


# The six Innovation toppers, one per riser in this order, back to front;
# nothing in the geometry picks which expansion goes where, and a cascade with
# more risers than expansions repeats.
TOPPERS = ("Cities", "Echoes", "Artifacts", "Figures", "Unseen", "Blank")


def topper_meshes(d, folder, expansion):
    """Every object in a topper: the body AND its lettering.

    `_all`, not `_one`. A labelled topper carries its expansion name as inlays
    the same way a Lid carries its logo — `Topper Cities S15-Un.3mf` is a body
    plus nine of them — and taking only the body drops the lettering. What is
    left is the POCKETS the letters sit in, which read as text in a shaded
    render and are not text at all: they would print as bare recesses.
    """
    path = ROOT / "individual" / folder / B.topper_file(d, expansion)
    if not path.exists():
        raise MissingCached(f"no cached {path.name} in individual/{folder}")
    return _all(path)


def topper_risers(d, toppers=False):
    """[(riser, first)] that carry a topper: every riser where the row ships
    toppers (`build.ships_toppers`), none where it does not."""
    return A.holders(d) if toppers else []


def assemble(d, state, folder, out_dir, take_tokens=False,
             half=False, holder_source=False, toppers=False):
    """(parts, instances) for one cascade — `parts` the distinct meshes,
    `instances` [(part index, Place)]."""
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
    for first in (False, True):
        js = [j for j, f in A.holders(d) if f == first]
        if js:
            add(holder_mesh(d, folder, first, holder_source),
                [place(d, j) for j in js])

    # Toppers — Innovation only, one per riser, and only where the row has them
    # (`build.ships_toppers`: a box built for ONE set has nothing for a topper
    # to say). Each is its own cached component, so each is its own mesh with
    # one instance; the expansion order is `TOPPERS`' and is arbitrary as far
    # as the geometry is concerned.
    for j, first in topper_risers(d, toppers):
        pl = (A.topper if closed else A.topper_play)(d, j, first)
        for mesh in topper_meshes(d, folder, TOPPERS[j % len(TOPPERS)]):
            add(mesh, [pl])

    # The token holder is the FULL one: a merged row ships a HALF as well, but
    # the two are alternatives for one slot, not both at once, and the
    # placement is the same either way — `assembly.token_holder`. A row with
    # no `TokenHolder` gets neither.
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
    return parts, instances


def catalogue(csv=CSV, game=None, model=None, version=CURRENT):
    """[(folder, Derived, tokens, toppers)] — every cascade, both sleevings.

    `tokens` and `toppers` are per ROW and not derivable from the geometry —
    only the sets whose expansions need a token holder carry one, and a
    single-set cascade carries no toppers — so they are asked of the row, the
    way `cad.build`'s catalogues ask (`ships_token_holder`, `ships_toppers`).

    `version` is the RELEASE assembled, because a release can change a part —
    a 7.1 Lid has one socket per pusher where a 7.0 one has three
    (`cad/revisions.py`) — so the mechanism has to be checkable at each."""
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
    ap.add_argument("--holder", choices=("cached", "source"), default="cached",
                    help="where the Holder comes from: cached (individual/, "
                         "the Onshape 7.0 corpus) or source (cad/parts/holder, "
                         "as the released cascades print it)")
    ap.add_argument("--half", action="store_true",
                    help="on a merged row, place the HALF token holder instead "
                         "of the FULL — they are alternatives for one slot")
    args = ap.parse_args(argv)

    rows = catalogue(args.csv, args.game, args.model, args.version)
    states = A.STATES if args.state == "all" else (args.state,)
    if args.list:
        for folder, d, _tokens, _toppers in rows:
            print(f"  {folder}/{d.calModelName}")
        print(f"\n  {len(rows)} cascade{'' if len(rows) == 1 else 's'}")
        return 0

    print(f"  holders: {args.holder}")
    print(f"  {'file':52s} {'parts':>6s} {'inst':>5s} {'tris':>8s} {'KB':>6s}")
    skipped = []
    for folder, d, tokens, toppers in rows:
        for state in states:
            try:
                parts, instances = assemble(d, state, folder, args.out,
                                            take_tokens=tokens,
                                            half=args.half,
                                            holder_source=args.holder == "source",
                                            toppers=toppers)
            except MissingCached as e:
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
