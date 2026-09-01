#!/usr/bin/env python3
"""Build components from parts.csv into build/<Game>/. ZERO Onshape API calls.

    .venv/bin/python -m cad.build                 # every pusher, every game
    .venv/bin/python -m cad.build --game Dominion
    .venv/bin/python -m cad.build --list          # what it would build

    .venv/bin/python -m cad.build --part box      # every box — MINUTES
    .venv/bin/python -m cad.build --part box --model S2.40.12-30.45-Sl
    .venv/bin/python -m cad.build --part all      # both

Pushers are the default because they are seconds each. A box is about ten, so
all 50 is minutes; `--model` matches on the model code and is the way to build
one. Look at the result with

    .venv/bin/python -m cad.render "build/Dominion/Box S2.40.12-30.45-Sl.3mf" \
        --box --contact tmp/box.png

Output is the same interface Onshape's exports are — see `cad/mesh3mf.py` — in
the same assembly position, so a file here is comparable, part for part, with
the one in `individual/`. It is written to `build/`, never over `individual/`:
that directory is 242 components that cost a year's API budget to make and
cannot be re-fetched, and it stays the ground truth until a component type has
passed regression (`tests/test_pusher_regression.py`).

## Naming, and the axis the old key is missing

A pusher's depth depends on `FirstSlidingSlotCards`, but `plan_exports` keys it
`(risers, cards, sleeved)` and names the file `Pusher RxC-Sl.3mf`. Two Dominion
rows therefore collide — `324 Card` (no override) and `290 Card (Mat)` (first
riser 12) — and differ by 1.20 mm sleeved. So this builder carries the axis in
the name, following parts.csv's own model-code convention (`S2.40.12/30`, with
`/` folded to `-` as `components.cascade_filename` already does):

    no override        Pusher 6x10-Sl.3mf
    first riser 12     Pusher 6x10-12-Sl.3mf

Four files are consequently named differently from `individual/` (the 246 Card
and 472 Card pushers, which have overrides and no collision), and two are new.
`--legacy-names` writes the old names instead, which is what a promotion into
`individual/` would need until the planner's key is fixed; it refuses when two
geometries would land on one name.
"""
import argparse
import sys
from pathlib import Path

from build123d import Location

from . import derive as D
from . import mesh3mf
from . import params
from . import lock as L
from .parts import box as box_part
from .parts import pusher

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "automation" / "parts.csv"


def pusher_file(p, legacy=False):
    slv = "Sl" if p.isSleeved else "Un"
    first = ("" if legacy or not p.isFirstSlidingSlotOverride
             else f"-{p.FirstSlidingSlotCards}")
    return f"Pusher {p.RisingSliders}x{p.CardsPerSlidingSlot}{first}-{slv}.3mf"


def box_file(d):
    """`Box <model>.3mf`, the name `individual/` uses.

    `calModelName` IS the box's identity — it carries the size letter, the riser
    count, the capacities, the first-riser override, the Mat branch and the
    sleeving — and CLAUDE.md makes the CAD the authority on it. Only the
    separators differ from the studio's string.
    """
    name = d.calModelName.replace(".Sl", "-Sl").replace(".Un", "-Un")
    return "Box " + name.replace("/", "-") + ".3mf"


def box_catalogue(csv=CSV, game=None, model=None):
    """[(folder, filename, Primary)] — every distinct box, deduplicated.

    Boxes do NOT share across games or sleeving, and `calModelName` separates
    every axis that changes the geometry, so it is the whole key.
    """
    out = {}
    for row in params.load_rows(csv):
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            if game and p.GameName.lower() != game.lower():
                continue
            d = D.derive(p)
            fn = box_file(d)
            if model and model.lower() not in fn.lower():
                continue
            out.setdefault((p.GameName, fn), (p.GameName, fn, p))
    return [out[k] for k in sorted(out)]


def build_box(p, out_dir, folder, filename):
    """Build one box and write the 3MF. Boxes are NOT placed in an assembly
    offset — the part studio's origin is the assembly's."""
    part = box_part.build(p)
    path = out_dir / folder / filename
    before = path.read_bytes() if path.exists() else None
    meshed = mesh3mf.write(path, [("Box", part)])
    _, verts, tris = meshed[0]
    return {"path": path, "verts": len(verts), "tris": len(tris),
            "volume": part.volume, "bytes": path.stat().st_size,
            "changed": before is not None and before != path.read_bytes(),
            "new": before is None}


def catalogue(csv=CSV, game=None, legacy=False):
    """[(folder, filename, Primary)] — every distinct pusher, deduplicated.

    The key is the full one: the game, the riser count, the cards per slot, the
    first-riser override and the sleeving. 34 entries against the planner's 32.
    """
    out = {}
    for row in params.load_rows(csv):
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            if game and p.GameName.lower() != game.lower():
                continue
            key = (p.GameName, p.RisingSliders, p.CardsPerSlidingSlot,
                   p.FirstSlidingSlotCards if p.isFirstSlidingSlotOverride else 0,
                   sleeved)
            out.setdefault(key, (p.GameName, pusher_file(p, legacy), p))
    if legacy:
        names, clash = {}, []
        for folder, fn, p in out.values():
            prev = names.setdefault((folder, fn), p)
            if prev is not p:
                clash.append(f"{folder}/{fn}")
        if clash:
            sys.exit("--legacy-names: two distinct geometries share a name: "
                     + ", ".join(sorted(clash)))
    return [out[k] for k in sorted(out)]


def build_pusher(p, out_dir, folder, filename):
    """Build one pusher, place it in assembly position, write the 3MF."""
    d = D.derive(p)
    part = pusher.build(p).moved(Location(pusher.assembly_offset(d)))
    path = out_dir / folder / filename
    before = path.read_bytes() if path.exists() else None
    meshed = mesh3mf.write(path, [("Pusher", part)])
    _, verts, tris = meshed[0]
    return {"path": path, "depth": d.calPusherTotalDepth,
            "rise": d.calHeightIncrement,
            "cls": L.lock_class(d.calPusherTotalDepth)[0],
            "verts": len(verts), "tris": len(tris),
            "bytes": path.stat().st_size,
            "changed": before is not None and before != path.read_bytes(),
            "new": before is None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", help="Compile / Dominion / FCM / Innovation")
    ap.add_argument("--out", default=str(ROOT / "build"), type=Path)
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--legacy-names", action="store_true",
                    help="use plan_exports' names (drops the first-riser axis)")
    ap.add_argument("--list", action="store_true", help="print, do not build")
    ap.add_argument("--part", choices=("pusher", "box", "all"), default="pusher",
                    help="what to build. Pushers are the default because they "
                         "are seconds; a box is about ten, so all 48 is minutes")
    ap.add_argument("--model", help="build only boxes whose model code contains "
                                    "this, e.g. S2.40.12-30.45-Sl")
    args = ap.parse_args(argv)

    if args.part in ("box", "all"):
        boxes = box_catalogue(args.csv, args.game, args.model)
        if args.list:
            for folder, fn, p in boxes:
                print(f"  {folder + '/' + fn}")
            print(f"\n  {len(boxes)} boxes")
        else:
            print(f"  {'file':44s} {'mm3':>11s} {'verts':>7s} {'tris':>7s} {'KB':>6s}")
            total = 0
            for folder, fn, p in boxes:
                r = build_box(p, args.out, folder, fn)
                mark = "new" if r["new"] else ("changed" if r["changed"] else "")
                print(f"  {folder + '/' + fn:44s} {r['volume']:11.1f} "
                      f"{r['verts']:7d} {r['tris']:7d} {r['bytes'] / 1024:6.0f}  {mark}")
                total += r["bytes"]
            print(f"\n  {len(boxes)} boxes, {total / 1e6:.1f} MB, in {args.out}")
        if args.part == "box":
            return 0

    items = catalogue(args.csv, args.game, args.legacy_names)
    if args.list:
        for folder, fn, p in items:
            d = D.derive(p)
            print(f"  {folder + '/' + fn:40s} D {d.calPusherTotalDepth:6.2f}  "
                  f"{L.lock_class(d.calPusherTotalDepth)[0]}")
        print(f"\n  {len(items)} pushers")
        return 0

    print(f"  {'file':40s} {'D':>6s} {'rise':>6s} {'cls':>4s} "
          f"{'verts':>6s} {'tris':>6s} {'KB':>6s}")
    total = 0
    for folder, fn, p in items:
        r = build_pusher(p, args.out, folder, fn)
        mark = "new" if r["new"] else ("changed" if r["changed"] else "")
        print(f"  {folder + '/' + fn:40s} {r['depth']:6.2f} {r['rise']:6.3f} "
              f"{r['cls']:>4s} {r['verts']:6d} {r['tris']:6d} "
              f"{r['bytes'] / 1024:6.0f}  {mark}")
        total += r["bytes"]
    print(f"\n  {len(items)} pushers, {total / 1e6:.1f} MB, in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
