#!/usr/bin/env python3
"""Build components from parts.csv into build/<Game>/. ZERO Onshape API calls.

    .venv/bin/python -m cad.build                 # every pusher, every game
    .venv/bin/python -m cad.build --game Dominion
    .venv/bin/python -m cad.build --list          # what it would build, 0.1 s

    .venv/bin/python -m cad.build --part lid      # every lid — 2.5 min pooled
    .venv/bin/python -m cad.build --part box      # every box — 2 min pooled
    .venv/bin/python -m cad.build --part box --model S2.40.12-30.45-Sl
    .venv/bin/python -m cad.build --part holder   # every holder — 1 min pooled
    .venv/bin/python -m cad.build --part tokenholder  # Dominion only
    .venv/bin/python -m cad.build --part topper   # Innovation only
    .venv/bin/python -m cad.build --part all      # all six — 5 min pooled
    .venv/bin/python -m cad.build --part all      # again: 0 s, all skipped
    .venv/bin/python -m cad.build --jobs 1        # serial; --force rebuilds

Builds run in a process pool, one part per job (`--jobs`, default every
core), and a stamp beside each file records what it was built from, so a
rerun with nothing changed skips it; `--model` matches on the filename and
is the way to build one. Look at the result with

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
import hashlib
import os
import sys
import time
from pathlib import Path

from . import derive as D
from . import mesh3mf
from . import params
from . import lock as L
from . import tables as TB

# build123d is NOT imported here. It costs four seconds to load, and the
# catalogue paths — `--list`, `--help`, `cad.promote`, `cad.assemble --list` —
# are pure arithmetic over parts.csv; the part modules are imported inside
# the builders, in the process that actually builds.

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
    from .parts import lid as lid_part
    part, inlays = lid_part.build_all(p)
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

    The object name is the one `plan_exports` uses, so the file drops straight
    in. NB `individual/`'s own first-riser files name their body `Holder` — the
    assembly named both that, and `assembly_split.py` told them apart by height.
    Generated locally, the part simply gets named; nothing downstream reads the
    body name (`make_cascade.load_export` sorts by object id), and the `object`
    role `plan_exports` emits is `FirstHolder` either way.
    """
    from .parts import holder as holder_part
    part = holder_part.build(p, first)
    path = out_dir / folder / filename
    before = path.read_bytes() if path.exists() else None
    meshed = mesh3mf.write(path, [("FirstHolder" if first else "Holder", part)])
    _, verts, tris = meshed[0]
    return {"path": path, "verts": len(verts), "tris": len(tris),
            "volume": part.volume, "bytes": path.stat().st_size,
            "changed": before is not None and before != path.read_bytes(),
            "new": before is None}


def topper_file(p, d, expansion="Blank"):
    """`Topper Blank M10-Un.3mf` — the cached corpus' own name.

    The key is NOT `calModelName`. Onshape's catalogue is keyed on three
    things — `HorizontalSlots` through the size letter, `CardsPerSlidingSlot`
    and `isSleeved` — and that is the 48 files in `individual/`: 8 bodies, 6
    expansions each.

    Those three do NOT fully determine the geometry, though. The topper's slant
    is the Holder's, which comes from `calHeightIncrement`, which comes from
    `RisingSliders`. Every Innovation row that gets toppers has 5 risers, so
    the name is sound in practice — but `Single Set` at 3 risers has the same
    three-part key as `3 Later Ages` and a slope of 2.727 against 2.130, which
    is a 5% difference in volume under one filename. `topper_catalogue`
    refuses that rather than letting whichever row came first win.
    """
    slv = "-Sl" if p.isSleeved else "-Un"
    return f"Topper {expansion} {d.calSizeLetter}{p.CardsPerSlidingSlot}{slv}.3mf"


def topper_shape_key(p, d):
    """Everything the topper's geometry actually depends on — which is one more
    thing than its FILENAME carries. See `topper_file`."""
    return (p.HorizontalSlots, p.CardsPerSlidingSlot, p.isSleeved,
            p.RisingSliders)


# A topper labels which expansion is in a slot, so a cascade that holds only
# ONE has no use for them (Allan) — and `individual/` bears that out: no cached
# topper for `Single Set` or `Single Mini`. `Set/Extension` is the column that
# says so, and it is free text, so this matches on the phrase rather than on an
# exact string. If a future single-set row words it differently it will get
# toppers built; `tests/test_topper_corpus.py` reports the catalogue against
# the cache, which is where that would show up.
SINGLE_SET = "one expansion"

# The Blank and the five marks — `tables.TOPPER_EXPANSIONS`, which
# `parts/topper.py` asserts is what `MARKS` draws.
TOPPER_EXPANSIONS = ("Blank",) + TB.TOPPER_EXPANSIONS


def topper_catalogue(csv=CSV, game=None, model=None):
    """[(folder, filename, Primary)] — every distinct topper.

    Innovation only, single-set cascades excluded: the blank and every
    expansion whose mark `topper.MARKS` has, which is all five. See
    spec/TOPPER.md.
    """
    out, shapes = {}, {}
    for row in params.load_rows(csv):
        if SINGLE_SET in (row.get("Set/Extension") or "").lower():
            continue
        for sleeved in (0, 1):
            p = params.from_row(row, sleeved)
            if p.GameName != "Innovation":
                continue
            if game and p.GameName.lower() != game.lower():
                continue
            d = D.derive(p)
            key = topper_shape_key(p, d)
            for expansion in TOPPER_EXPANSIONS:
                fn = topper_file(p, d, expansion)
                if model and model.lower() not in fn.lower():
                    continue
                seen = shapes.get(fn)
                if seen is not None and seen != key:
                    raise ValueError(
                        f"two parameter sets want to be {fn!r} and are not the "
                        f"same shape: {seen} vs {key}. The filename is "
                        f"Onshape's and carries no riser count; see "
                        f"build.topper_file.")
                shapes[fn] = key
                out.setdefault((p.GameName, fn),
                               (p.GameName, fn, p, expansion))
    return [out[k] for k in sorted(out)]


def build_topper(p, expansion, out_dir, folder, filename):
    """Build one topper and write the 3MF. One body, named as the corpus does."""
    from .parts import topper as topper_part
    part = topper_part.build(p, None, expansion)
    path = out_dir / folder / filename
    before = path.read_bytes() if path.exists() else None
    meshed = mesh3mf.write(path, [("Topper", part)])
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
    from .parts import box as box_part
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
    from .parts import token_holder
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
    from build123d import Location
    from .parts import pusher
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


# --- running a catalogue: stamps, a pool, and one loop for every kind --------
#
# A build is a list of SPECS — (kind, Primary, extra, targets) — run through
# `_job`, in a process pool by default. Each job builds once and writes every
# target: six holders are the same geometry under two names (the Mat twins),
# and the second name is a copy of the first's bytes, not a second build.
#
# A STAMP beside each written file records a digest of everything the file
# depends on — the Primary, the kind and its extra, and every source file
# under cad/, logos/ and fonts/ — so a rerun with nothing changed skips the
# build and says so, and any edit anywhere in cad/ invalidates every stamp.
# `--force` ignores them. The 3MF itself is still the thing compared: a
# rebuilt file is `changed` only when its bytes moved.

STAMP_DIR = ".stamps"


def source_hash():
    """One digest over everything a part can depend on besides its Primary."""
    h = hashlib.sha256()
    files = sorted(list((ROOT / "cad").rglob("*.py"))
                   + list((ROOT / "logos").rglob("*.dxf"))
                   + list((ROOT / "logos").rglob("*.brep"))
                   + list((ROOT / "fonts").glob("*.ttf")))
    for f in files:
        h.update(str(f.relative_to(ROOT)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def stamp_of(src, kind, p, extra):
    return hashlib.sha256(f"{src}|{kind}|{p!r}|{extra!r}".encode()).hexdigest()


def stamp_path(out_dir, folder, filename):
    return out_dir / STAMP_DIR / folder / (filename + ".sha256")


def _build(kind, p, extra, out_dir, folder, filename):
    if kind == "lid":
        return build_lid(p, out_dir, folder, filename)
    if kind == "holder":
        return build_holder(p, extra, out_dir, folder, filename)
    if kind == "tokenholder":
        return build_token_holder(p, extra, out_dir, folder, filename)
    if kind == "topper":
        return build_topper(p, extra, out_dir, folder, filename)
    if kind == "box":
        return build_box(p, out_dir, folder, filename)
    if kind == "pusher":
        return build_pusher(p, out_dir, folder, filename)
    raise ValueError(kind)


def _job(spec):
    """One unit of work, in a worker: build once, write every target."""
    kind, p, extra = spec["kind"], spec["p"], spec["extra"]
    out_dir, targets = spec["out_dir"], spec["targets"]
    if not spec["force"] and all(
            (out_dir / f / fn).exists()
            and stamp_path(out_dir, f, fn).exists()
            and stamp_path(out_dir, f, fn).read_text() == spec["stamp"]
            for f, fn in targets):
        return [{"path": out_dir / f / fn, "folder": f, "filename": fn,
                 "bytes": (out_dir / f / fn).stat().st_size,
                 "skipped": True, "changed": False, "new": False}
                for f, fn in targets]
    folder, fn = targets[0]
    t0 = time.perf_counter()
    r = _build(kind, p, extra, out_dir, folder, fn)
    r.update(folder=folder, filename=fn, skipped=False,
             seconds=time.perf_counter() - t0)
    out = [r]
    data = r["path"].read_bytes()
    for f, fn2 in targets[1:]:
        path = out_dir / f / fn2
        before = path.read_bytes() if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        out.append(dict(r, path=path, folder=f, filename=fn2, seconds=0.0,
                        changed=before is not None and before != data,
                        new=before is None))
    for f, fn2 in targets:
        sp = stamp_path(out_dir, f, fn2)
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(spec["stamp"])
    return out


def run_jobs(specs, jobs):
    """Every spec through `_job`, in catalogue order, `jobs` at a time."""
    if jobs <= 1 or len(specs) <= 1:
        return [_job(s) for s in specs]
    import concurrent.futures as cf
    import multiprocessing as mp
    with cf.ProcessPoolExecutor(max_workers=min(jobs, len(specs)),
                                mp_context=mp.get_context("spawn")) as ex:
        return list(ex.map(_job, specs))


def holder_key(p, first):
    """What a holder's geometry depends on: everything in its Primary but the
    front capacity and the Mat branch, which `holder_file` carries through
    `calModelName` and the part never reads. Two files with one key are one
    build — the six Mat twins, byte-identical before this deduplicated them."""
    return (p.GameName, p.HorizontalSlots, p.RisingSliders,
            p.CardsPerSlidingSlot, p.isFirstSlidingSlotOverride,
            p.FirstSlidingSlotCards, p.isSleeved, p.Version, first)


KINDS = ("lid", "holder", "tokenholder", "topper", "box", "pusher")
NOUN = {"lid": "lids", "holder": "holders", "tokenholder": "token holders",
        "topper": "toppers", "box": "boxes", "pusher": "pushers"}


def specs_for(kind, args, src):
    """[(folder, filename, Primary, extra)] for `--list`, and the job specs."""
    if kind == "lid":
        items = [(f, fn, p, None) for f, fn, p in
                 lid_catalogue(args.csv, args.game, args.model)]
    elif kind == "holder":
        items = holder_catalogue(args.csv, args.game, args.model)
    elif kind == "tokenholder":
        items = token_holder_catalogue(args.csv, args.game, args.model,
                                       args.legacy_names)
    elif kind == "topper":
        items = topper_catalogue(args.csv, args.game, args.model)
    elif kind == "box":
        items = [(f, fn, p, None) for f, fn, p in
                 box_catalogue(args.csv, args.game, args.model)]
    else:
        items = [(f, fn, p, None) for f, fn, p in
                 catalogue(args.csv, args.game, args.legacy_names)]
    groups = {}
    for folder, fn, p, extra in items:
        key = (holder_key(p, extra) if kind == "holder"
               else (folder, fn))
        g = groups.setdefault(key, {"kind": kind, "p": p, "extra": extra,
                                    "out_dir": args.out, "targets": [],
                                    "force": args.force,
                                    "stamp": stamp_of(src, kind, p, extra)})
        g["targets"].append((folder, fn))
    return items, list(groups.values())


def _row(kind, r):
    """One printed line per written file."""
    mark = ("skipped" if r["skipped"] else "new" if r["new"]
            else "changed" if r["changed"] else "")
    name = f"{r['folder']}/{r['filename']}"
    if r["skipped"]:
        return f"  {name:44s} {'':>11s} {r['bytes'] / 1024:6.0f}  {mark}"
    if kind == "pusher":
        return (f"  {name:44s} D {r['depth']:6.2f} rise {r['rise']:6.3f} "
                f"{r['cls']:>3s} {r['verts']:7d} {r['tris']:7d} "
                f"{r['bytes'] / 1024:6.0f}  {r['seconds']:5.1f}s  {mark}")
    bodies = f"{r['bodies']:4d}" if "bodies" in r else "    "
    return (f"  {name:44s} {r['volume']:11.1f} {bodies} {r['verts']:7d} "
            f"{r['tris']:7d} {r['bytes'] / 1024:6.0f}  {r['seconds']:5.1f}s  "
            f"{mark}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", help="Compile / Dominion / FCM / Innovation")
    ap.add_argument("--out", default=str(ROOT / "build"), type=Path)
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--legacy-names", action="store_true",
                    help="use plan_exports' names (drops the first-riser axis)")
    ap.add_argument("--list", action="store_true", help="print, do not build")
    ap.add_argument("--part", choices=KINDS + ("all",), default="pusher",
                    help="what to build; `all` is the lot, a few minutes with "
                         "the pool")
    ap.add_argument("--model", help="build only parts whose filename contains "
                                    "this, e.g. S2.40.12-30.45-Sl")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1,
                    help="parallel builds (default: every core); 1 is serial")
    ap.add_argument("--force", action="store_true",
                    help="rebuild even where the stamp says nothing changed")
    args = ap.parse_args(argv)

    kinds = KINDS if args.part == "all" else (args.part,)
    src = source_hash()
    t_all = time.perf_counter()
    for kind in kinds:
        items, specs = specs_for(kind, args, src)
        if args.list:
            for folder, fn, p, _extra in items:
                line = f"  {folder + '/' + fn}"
                if kind == "pusher":
                    d = D.derive(p)
                    line = (f"  {folder + '/' + fn:40s} D {d.calPusherTotalDepth:6.2f}  "
                            f"{L.lock_class(d.calPusherTotalDepth)[0]}")
                print(line)
            print(f"\n  {len(items)} {NOUN[kind]}\n")
            continue
        t0 = time.perf_counter()
        results = [r for group in run_jobs(specs, args.jobs) for r in group]
        results.sort(key=lambda r: (r["folder"], r["filename"]))
        for r in results:
            print(_row(kind, r))
        if kind == "lid":
            plain = sorted({r["folder"] for r in results
                            if not r["skipped"] and r.get("bodies") == 1})
            if plain:
                # Not silently: a lid without its logo is a lid that cannot
                # be printed in two filaments.
                print(f"\n  NO LOGO ARTWORK for {plain} — those lids built "
                      f"without a pattern (cad/tables.LID_LOGO)")
        built = sum(1 for r in results if not r["skipped"])
        print(f"\n  {len(results)} {NOUN[kind]}: {built} built "
              f"({sum(1 for r in results if r['new'])} new, "
              f"{sum(1 for r in results if r['changed'])} changed), "
              f"{len(results) - built} unchanged and skipped, "
              f"{sum(r['bytes'] for r in results) / 1e6:.1f} MB, "
              f"{time.perf_counter() - t0:.0f} s with {args.jobs} job(s), "
              f"in {args.out}\n")
    if not args.list and len(kinds) > 1:
        print(f"  all {len(kinds)} kinds in {(time.perf_counter() - t_all) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
