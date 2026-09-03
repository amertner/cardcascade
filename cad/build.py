#!/usr/bin/env python3
"""Build components from parts.csv into build/<Game>/. ZERO Onshape API calls.

    .venv/bin/python -m cad.build                 # every pusher, every game
    .venv/bin/python -m cad.build --game Dominion
    .venv/bin/python -m cad.build --list          # what it would build

    .venv/bin/python -m cad.build --part lid      # every lid — seconds each
    .venv/bin/python -m cad.build --part box      # every box — MINUTES
    .venv/bin/python -m cad.build --part box --model S2.40.12-30.45-Sl
    .venv/bin/python -m cad.build --part holder   # every holder — INCOMPLETE
    .venv/bin/python -m cad.build --part tokenholder  # Dominion only
    .venv/bin/python -m cad.build --part all      # all five

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
from .parts import holder as holder_part
from .parts import lid as lid_part
from .parts import pusher
from .parts import token_holder

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


def lid_file(d):
    """`Lid <model>.3mf`, the name `individual/` uses.

    Keyed on `calModelName` exactly as the Box is, which means a Mat cascade
    gets its own lid where `plan_exports` keys one `("Lid", model)` for both.
    Nothing in the geometry depends on `MatPocket`, so the two are identical
    files today; they part company when the floor's engraved `calModelName` is
    built, and the CAD is the authority on that code (CLAUDE.md).
    """
    name = d.calModelName.replace(".Sl", "-Sl").replace(".Un", "-Un")
    return "Lid " + name.replace("/", "-") + ".3mf"


def lid_catalogue(csv=CSV, game=None, model=None):
    """[(folder, filename, Primary)] — every distinct lid, deduplicated."""
    out = {}
    for row in params.load_rows(csv):
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            if game and p.GameName.lower() != game.lower():
                continue
            fn = lid_file(D.derive(p))
            if model and model.lower() not in fn.lower():
                continue
            out.setdefault((p.GameName, fn), (p.GameName, fn, p))
    return [out[k] for k in sorted(out)]


def build_lid(p, out_dir, folder, filename):
    """Build one lid and write the 3MF. Like the Box, a Lid sits at the part
    studio's origin, which is the assembly's.

    A lid is MORE THAN ONE BODY: the logo pattern's inlays print in the second
    filament, so Onshape exports them as their own objects and so does this.
    `make_cascade.load_export` pairs bodies to template parts by name and
    reconciles the rest onto same-extruder slots, so the names matter and the
    order does not — but the order is fixed anyway (down the artwork, largest
    first) to keep a rebuild byte-identical.
    """
    part = lid_part.build(p)
    inlays = lid_part.inlays(p)
    bodies = [("Lid", part)]
    bodies += [(f"Part {i}", s) for i, s in enumerate(
        sorted(inlays, key=lambda s: (-round(s.volume, 6),
                                      round(s.bounding_box().min.X, 6),
                                      round(s.bounding_box().min.Y, 6))),
        start=2)]
    path = out_dir / folder / filename
    before = path.read_bytes() if path.exists() else None
    meshed = mesh3mf.write(path, bodies)
    verts = sum(len(v) for _n, v, _t in meshed)
    tris = sum(len(t) for _n, _v, t in meshed)
    return {"path": path, "verts": verts, "tris": tris,
            "volume": part.volume, "bodies": len(bodies),
            "bytes": path.stat().st_size,
            "changed": before is not None and before != path.read_bytes(),
            "new": before is None}


def holder_file(d, first=False):
    """`Holder <model>.3mf`, or `FirstHolder ...` for the first-riser one.

    Keyed on `calModelName` like the Box and the Lid. That is a wider key than
    the geometry needs — a holder does not depend on the front capacity or the
    Mat branch — so two rows can produce identical files under different names.
    It is the same trade `lid_file` makes, and the alternative is a name that
    cannot be looked up from a parts.csv row.

    NB `plan_exports` names these `Holder M-21-r4-Sl`, keyed on
    `(size, front capacity, risers, sleeved, first)`. That key is missing
    `HorizontalSlots` for the per-slot games, where the size letter stands in
    for it, and missing the card count, which sets the depth. Both are in
    `calModelName`.
    """
    name = d.calModelName.replace(".Sl", "-Sl").replace(".Un", "-Un")
    stem = "FirstHolder " if first else "Holder "
    return stem + name.replace("/", "-") + ".3mf"


def holder_catalogue(csv=CSV, game=None, model=None):
    """[(folder, filename, Primary, first)] — every distinct holder.

    A row with a first-riser override yields TWO: the standard holder and the
    deeper `FirstHolder` that replaces one of them, exactly as
    `plan_exports.compose` emits them.
    """
    out = {}
    for row in params.load_rows(csv):
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            if game and p.GameName.lower() != game.lower():
                continue
            d = D.derive(p)
            for first in ((False, True) if p.isFirstSlidingSlotOverride
                          else (False,)):
                fn = holder_file(d, first)
                if model and model.lower() not in fn.lower():
                    continue
                out.setdefault((p.GameName, fn), (p.GameName, fn, p, first))
    return [out[k] for k in sorted(out)]


def build_holder(p, first, out_dir, folder, filename):
    """Build one holder and write the 3MF.

    INCOMPLETE — `cad/parts/holder.py` stops after the rear lips, so a written
    holder is about 2% heavy. See spec/HOLDER.md; the object name is the one
    `plan_exports` uses so the files drop straight in once it is finished.
    """
    part = holder_part.build(p, first)
    path = out_dir / folder / filename
    before = path.read_bytes() if path.exists() else None
    meshed = mesh3mf.write(path, [("FirstHolder" if first else "Holder", part)])
    _, verts, tris = meshed[0]
    return {"path": path, "verts": len(verts), "tris": len(tris),
            "volume": part.volume, "bytes": path.stat().st_size,
            "changed": before is not None and before != path.read_bytes(),
            "new": before is None}


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


def token_holder_file(d, half, legacy=False):
    """`TokenHolder <model>.3mf`, or the name `individual/` uses.

    Keyed on `calTokenHolderModel`, which is what the part has engraved on it,
    where `plan_exports` keys `(front capacity, merged, sleeved)` and names the
    file `TokenHolder <cap>-<slv>[ merged]`. That key is right about the
    GEOMETRY — `HorizontalSlots` cancels out of `calTokenHolderSlotWidth`, so a
    3-slot and a 4-slot box with the same front capacity really do want the
    same tray — and wrong about the ENGRAVING, which carries the size letter.
    Dominion `324 Card` (M) and `333 Card` (S) collide on `TokenHolder 21-Sl`
    today and the cached file is stamped `M21.Sl` for both.

    So this builder carries the letter in the name, as it carries the Pusher's
    first-riser axis, and `--legacy-names` writes the old name for a promotion
    into `individual/` — refusing when two model codes would land on one file.
    """
    kind = "HalfTokenHolder" if half else "TokenHolder"
    if legacy:
        cap, mat = d.calTokenHolderModel, ""
        # `M21-M.Sl` -> capacity `21`, merged; `M21.Sl` -> capacity `21`.
        body = cap.split(".")[0]
        if body.endswith("-M"):
            body, mat = body[:-2], " merged"
        digits = "".join(c for c in body if c.isdigit())
        slv = "Sl" if cap.endswith(".Sl") else "Un"
        return f"{kind} {digits}-{slv}{mat}.3mf"
    name = d.calTokenHolderModel.replace(".Sl", "-Sl").replace(".Un", "-Un")
    return f"{kind} {name}.3mf"


def token_holder_catalogue(csv=CSV, game=None, model=None, legacy=False):
    """[(folder, filename, Primary, half)] — every distinct token holder.

    A row asks for one through parts.csv's `TokenHolder` column (`full` or
    `none`); the HALF is a Mat-box feature, so a merged row yields both, which
    is what `plan_exports.compose` emits and what `PIPELINE.md` records.
    """
    out, clash = {}, {}
    for row in params.load_rows(csv):
        if (row.get("TokenHolder") or "").strip().lower() in ("", "none"):
            continue
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            if game and p.GameName.lower() != game.lower():
                continue
            d = D.derive(p)
            for half in ((False, True) if p.MatPocket else (False,)):
                fn = token_holder_file(d, half, legacy)
                if model and model.lower() not in fn.lower():
                    continue
                key = (p.GameName, fn)
                ident = (d.calTokenHolderModel, half)
                if legacy and clash.setdefault(key, ident) != ident:
                    raise SystemExit(
                        f"--legacy-names: {fn} would carry both "
                        f"{clash[key][0]} and {ident[0]}")
                out.setdefault(key, (p.GameName, fn, p, half))
    return [out[k] for k in sorted(out)]


def build_token_holder(p, half, out_dir, folder, filename):
    """Build one token holder and write the 3MF.

    Like the Box and the Lid it sits at the part studio's origin, which is the
    assembly's — every cached component is already at those coordinates.
    """
    part = token_holder.build(p, half)
    path = out_dir / folder / filename
    before = path.read_bytes() if path.exists() else None
    name = "HalfTokenHolder" if half else "TokenHolder"
    meshed = mesh3mf.write(path, [(name, part)])
    _, verts, tris = meshed[0]
    return {"path": path, "volume": part.volume,
            "verts": len(verts), "tris": len(tris),
            "bytes": path.stat().st_size,
            "changed": before is not None and before != path.read_bytes(),
            "new": before is None}


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
    ap.add_argument("--part",
                    choices=("pusher", "box", "lid", "holder", "tokenholder",
                             "all"),
                    default="pusher",
                    help="what to build. Pushers are the default because they "
                         "are seconds; a box is about ten, so all 48 is minutes")
    ap.add_argument("--model", help="build only boxes whose model code contains "
                                    "this, e.g. S2.40.12-30.45-Sl")
    args = ap.parse_args(argv)

    if args.part in ("lid", "all"):
        lids = lid_catalogue(args.csv, args.game, args.model)
        if args.list:
            for folder, fn, p in lids:
                print(f"  {folder + '/' + fn}")
            print(f"\n  {len(lids)} lid{'' if len(lids) == 1 else 's'}")
        else:
            print(f"  {'file':44s} {'mm3':>11s} {'bod':>4s} {'verts':>7s} "
                  f"{'tris':>7s} {'KB':>6s}")
            total, plain = 0, []
            for folder, fn, p in lids:
                r = build_lid(p, args.out, folder, fn)
                mark = "new" if r["new"] else ("changed" if r["changed"] else "")
                if r["bodies"] == 1:
                    plain.append(p.GameName)
                print(f"  {folder + '/' + fn:44s} {r['volume']:11.1f} "
                      f"{r['bodies']:4d} {r['verts']:7d} {r['tris']:7d} "
                      f"{r['bytes'] / 1024:6.0f}  {mark}")
                total += r["bytes"]
            if plain:
                # Not silently: a lid without its logo is a lid that cannot be
                # printed in two filaments.
                print(f"\n  NO LOGO ARTWORK for {sorted(set(plain))} — those "
                      f"lids built without a pattern (cad/tables.LID_LOGO)")
            print(f"\n  {len(lids)} lid{'' if len(lids) == 1 else 's'}, "
                  f"{total / 1e6:.1f} MB, in {args.out}")
        if args.part == "lid":
            return 0

    if args.part in ("holder", "all"):
        holders = holder_catalogue(args.csv, args.game, args.model)
        if args.list:
            for folder, fn, p, first in holders:
                print(f"  {folder + '/' + fn}")
            print(f"\n  {len(holders)} holders")
        else:
            print("  NB holders are INCOMPLETE — about 2% heavy, see "
                  "spec/HOLDER.md")
            print(f"  {'file':44s} {'mm3':>11s} {'verts':>7s} {'tris':>7s} {'KB':>6s}")
            total = 0
            for folder, fn, p, first in holders:
                r = build_holder(p, first, args.out, folder, fn)
                mark = "new" if r["new"] else ("changed" if r["changed"] else "")
                print(f"  {folder + '/' + fn:44s} {r['volume']:11.1f} "
                      f"{r['verts']:7d} {r['tris']:7d} {r['bytes'] / 1024:6.0f}  {mark}")
                total += r["bytes"]
            print(f"\n  {len(holders)} holders, {total / 1e6:.1f} MB, in {args.out}")
        if args.part == "holder":
            return 0

    if args.part in ("tokenholder", "all"):
        ths = token_holder_catalogue(args.csv, args.game, args.model,
                                     args.legacy_names)
        if args.list:
            for folder, fn, p, half in ths:
                print(f"  {folder + '/' + fn}")
            print(f"\n  {len(ths)} token holders")
        else:
            print(f"  {'file':44s} {'mm3':>11s} {'verts':>7s} {'tris':>7s} "
                  f"{'KB':>6s}")
            total = 0
            for folder, fn, p, half in ths:
                r = build_token_holder(p, half, args.out, folder, fn)
                mark = "new" if r["new"] else ("changed" if r["changed"] else "")
                print(f"  {folder + '/' + fn:44s} {r['volume']:11.1f} "
                      f"{r['verts']:7d} {r['tris']:7d} "
                      f"{r['bytes'] / 1024:6.0f}  {mark}")
                total += r["bytes"]
            print(f"\n  {len(ths)} token holders, {total / 1e6:.1f} MB, "
                  f"in {args.out}")
        if args.part == "tokenholder":
            return 0

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
