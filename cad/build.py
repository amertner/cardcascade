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
    .venv/bin/python -m cad.build --part all      # all six — about 3 min pooled
    .venv/bin/python -m cad.build --part all      # again: 0 s, all skipped
    .venv/bin/python -m cad.build --jobs 1        # serial; --force rebuilds

Builds run in a process pool, one part per job, and a stamp beside each file
records what it was built from, so a rerun with nothing changed skips it.
Look at the result with

    .venv/bin/python -m cad.render "build/Dominion/Box S2.40.12-30.45-Sl.3mf" \
        --box --contact tmp/box.png

Output is the interface Onshape's exports are (`cad/mesh3mf.py`), in the same
assembly position, written to `build/` and NEVER over `individual/` — that
corpus cost a year's API budget and cannot be re-fetched. A pusher's name
carries the `FirstSlidingSlotCards` axis the planner's key is missing;
`pusher_file(d, legacy=True)` gives the old name, which
`tests/test_pusher_regression.py` looks a cached twin up by.
"""
import argparse
import dataclasses
import hashlib
import os
import sys
import time
from pathlib import Path

from . import assembly as A
from . import derive as D
from . import mesh3mf
from . import params
from . import lock as L
from . import revisions as R
from . import tables as TB
from .refuse import Refused, refuse

# build123d is NOT imported here: it costs four seconds to load and the
# catalogue paths are pure arithmetic over parts.csv. The part modules are
# imported inside the builders, in the process that actually builds.

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "automation" / "parts.csv"


def model_stem(code):
    """A studio model code as the file names carry it: `S2.40.12-30.45-Sl` for
    `S2.40.12/30.45.Sl`, the dot before the sleeving and the `/` of a
    first-riser override both folded to `-`."""
    return code.replace(".Sl", "-Sl").replace(".Un", "-Un").replace("/", "-")


def model_matches(d, query):
    """Does `--model` — a code or part of one — pick this cascade?"""
    return not query or model_stem(query).lower() in model_stem(d.calModelName).lower()


def pusher_file(d, legacy=False):
    slv = "Sl" if d.isSleeved else "Un"
    first = ("" if legacy or not d.isFirstSlidingSlotOverride
             else f"-{d.FirstSlidingSlotCards}")
    return f"Pusher {d.RisingSliders}x{d.CardsPerSlidingSlot}{first}-{slv}.3mf"


def box_file(d):
    """`Box <model>.3mf`, the name `individual/` uses. `calModelName` IS the
    box's identity and the CAD is the authority on it."""
    # The two options the model code does not carry: no label holders, and
    # from 7.2g the back a variant box was built with. A row that ships
    # variants ships NO ordinary box, so the plain name is not written for it.
    suffix = "" if d.isLabelHoldersOnBox else " no label holders"
    suffix += {TB.BACK_STANDARD: "",
               TB.BACK_OPEN: " open back pocket",
               TB.BACK_NOTCHES: " pusher notches"}[d.BackPocket]
    return "Box " + model_stem(d.calModelName) + suffix + ".3mf"


def lid_file(d, variant=TB.LID_OWN):
    """`Lid <model>.3mf`, keyed on `calModelName` exactly as the Box is, so a
    Mat cascade gets its own lid. The alternate edition (7.1d) and the
    unmarked lid (7.2b) take a SUFFIX; it never goes on the lid the cascade
    carries, so the plain name stays what it has always been."""
    stem = "Lid " + model_stem(d.calModelName)
    if variant == TB.LID_ALTERNATE:
        stem += " " + TB.lid_edition_name(
            d.GameName, TB.lid_editions(d.GameName, d.calModelName)[1])
    elif variant == TB.LID_UNMARKED:
        stem += " " + TB.LID_UNMARKED_NAME
    elif variant != TB.LID_OWN:
        refuse(f"unknown lid variant {variant!r}; one of {TB.LID_VARIANTS}")
    return stem + ".3mf"


def lid_variants_built(d):
    """The lids this cascade's release ships, as `tables.LID_VARIANTS` members
    in project order. The ONLY place those two flags are asked — the part
    builds any variant at any release."""
    out = [TB.LID_OWN]
    if d.rev.both_lid_editions and TB.has_lid_alternate(d.GameName, d.calModelName):
        out.append(TB.LID_ALTERNATE)
    if d.rev.unmarked_lid:
        out.append(TB.LID_UNMARKED)
    return out


def lid_catalogue(csv=CSV, game=None, model=None, version=R.CURRENT):
    """[(folder, filename, Primary, variant)] — every distinct lid; `variant`
    (`tables.LID_VARIANTS`) is the builder's `extra`."""
    out = {}
    for _row, p in params.cascades(csv, game, version):
        d = D.derive(p)
        for variant in lid_variants_built(d):
            fn = lid_file(d, variant)
            if model and model.lower() not in fn.lower():
                continue
            out.setdefault((p.GameName, fn), (p.GameName, fn, p, variant))
    return [out[k] for k in sorted(out)]


def component_metadata(d, path):
    """What a written component says about ITSELF, in its 3MF metadata. The
    engraved `CC <v>` is read back by a signature over the digits' counters,
    which cannot tell one two-digit release from another, so the release goes
    in the file as TEXT too and `verify.check_stamp` holds the two to each
    other. `spec/REVISIONS.md`, "What a release moves besides its flags"."""
    return {"Title": path.stem,
            "Application": "Card Cascade cad.build",
            "Description": f"{d.calModelName} at {d.calVersion}",
            mesh3mf.VERSION_KEY: d.Version}


def write_component(path, bodies, d, **extra):
    """Mesh `bodies` [(name, shape)] into the component 3MF at `path` and
    report on it; the first body is the part, the rest its inlays. `d` is
    REQUIRED so no kind can write a part without saying which release wrote
    it."""
    before = path.read_bytes() if path.exists() else None
    meshed = mesh3mf.write(path, bodies, metadata=component_metadata(d, path))
    return {"path": path, "volume": bodies[0][1].volume, "bodies": len(bodies),
            "verts": sum(len(v) for _n, v, _t in meshed),
            "tris": sum(len(t) for _n, _v, t in meshed),
            "bytes": path.stat().st_size,
            "changed": before is not None and before != path.read_bytes(),
            "new": before is None, **extra}


def build_lid(d, extra, path):
    """Build one lid and write the 3MF; `extra` is its VARIANT. A Lid sits at
    the part studio's origin, which is the assembly's. It is MORE THAN ONE
    BODY — the logo inlays print in the second filament — and the order is
    fixed (largest first) to keep a rebuild byte-identical."""
    from .parts import lid as lid_part
    part, inlays = lid_part.build_all(d, variant=extra)
    bodies = [("Lid", part)]
    bodies += [(f"Part {i}", s) for i, s in enumerate(
        sorted(inlays, key=lambda s: (-round(s.volume, 6),
                                      round(s.bounding_box().min.X, 6),
                                      round(s.bounding_box().min.Y, 6))),
        start=2)]
    return write_component(path, bodies, d)


def holder_file(d, first=False, rear=False):
    """`Holder <model>.3mf`, `FirstHolder ...` for the deeper first-riser one,
    or `RearHolder ...` for the rearmost, lipless one (`rev.rear_holder`).
    Keyed on `calModelName` — wider than the geometry needs, so two rows can
    produce identical files under different names; the alternative is a name
    that cannot be looked up from a parts.csv row."""
    kind = "RearHolder" if rear else ("FirstHolder" if first else "Holder")
    return f"{kind} {model_stem(d.calModelName)}.3mf"


def holder_catalogue(csv=CSV, game=None, model=None, version=R.CURRENT):
    """[(folder, filename, Primary, (first, rear))] — every distinct holder;
    the kinds are `assembly.holder_kinds`."""
    out = {}
    for _row, p in params.cascades(csv, game, version):
        d = D.derive(p)
        for (first, rear), _js in A.holder_kinds(d):
            fn = holder_file(d, first, rear)
            if model and model.lower() not in fn.lower():
                continue
            out.setdefault((p.GameName, fn), (p.GameName, fn, p, (first, rear)))
    return [out[k] for k in sorted(out)]


def build_holder(d, extra, path):
    """Build one holder; `extra` is `(first, rear)`. The object name is the one
    `plan_exports` uses, so the file drops straight in."""
    from .parts import holder as holder_part
    first, rear = extra
    part = holder_part.build(d, first, rear=rear)
    role = "RearHolder" if rear else ("FirstHolder" if first else "Holder")
    return write_component(path, [(role, part)], d)


def topper_file(d, expansion="Blank"):
    """`Topper Blank M10-Un.3mf` — the cached corpus' own name. The key is NOT
    `calModelName` but Onshape's three, which do NOT fully determine the
    geometry: the slant follows `RisingSliders`, so two rows can share the key
    and not the rise and `topper_catalogue` REFUSES that."""
    slv = "-Sl" if d.isSleeved else "-Un"
    return f"Topper {expansion} {d.calSizeLetter}{d.CardsPerSlidingSlot}{slv}.3mf"


def topper_shape_key(d):
    """Everything the topper's geometry depends on — one more thing than its
    FILENAME carries (`topper_file`)."""
    return (d.HorizontalSlots, d.CardsPerSlidingSlot, d.isSleeved,
            d.RisingSliders)


# A topper labels which expansion is in a slot, so a single-expansion cascade
# has no use for them. `Set/Extension` says so and is free text, so this
# matches on the PHRASE.
SINGLE_SET = "one expansion"


def ships_toppers(row, d):
    """Does this row's cascade carry toppers? Innovation only, not a
    single-set cascade (`SINGLE_SET`), and not a row whose `Toppers` column
    says `none`; the catalogue, `cad.cascade` and `cad.assemble` all ask it
    HERE. The column exists because a row sharing `topper_file`'s three-key
    with another but not the rise would build over the other's file."""
    if (row.get("Toppers") or "").strip().lower() in ("none", "no", "false", "0"):
        return False
    return (d.GameName == "Innovation"
            and SINGLE_SET not in (row.get("Set/Extension") or "").lower())


def topper_catalogue(csv=CSV, game=None, model=None, version=R.CURRENT):
    """[(folder, filename, Primary, expansion)] — every distinct topper: the
    blank and all five expansions, where `ships_toppers`."""
    out, shapes = {}, {}
    for row, p in params.cascades(csv, game, version):
        d = D.derive(p)
        if not ships_toppers(row, d):
            continue
        key = topper_shape_key(d)
        for expansion in TB.TOPPERS:
            fn = topper_file(d, expansion)
            if model and model.lower() not in fn.lower():
                continue
            seen = shapes.get(fn)
            if seen is not None and seen != key:
                refuse(f"two parameter sets want to be {fn!r} and are not the "
                       f"same shape: {seen} vs {key}. The filename is "
                       f"Onshape's and carries no riser count; see "
                       f"build.topper_file.")
            shapes[fn] = key
            out.setdefault((p.GameName, fn), (p.GameName, fn, p, expansion))
    return [out[k] for k in sorted(out)]


def build_topper(d, expansion, path):
    """Build one topper and write the 3MF: the body named as the corpus does,
    and its lettering as `Part 2`, `Part 3`, ... — the second-filament inlays
    a print needs (`topper.inlays`)."""
    from .parts import topper as topper_part
    part, inlays = topper_part.build_all(d, expansion)
    bodies = [("Topper", part)] + [(f"Part {i}", s) for i, s in enumerate(inlays, start=2)]
    return write_component(path, bodies, d)


def box_catalogue(csv=CSV, game=None, model=None, version=R.CURRENT):
    """[(folder, filename, Primary)] — every distinct box, deduplicated.
    `calModelName` separates every axis that changes the geometry, so it is
    the whole key, plus the options it does not carry: a row that ships a
    plain box or variant backs yields the twins too, each under its own
    Primary, so `build_box` needs no variant."""
    out = {}
    for row, p in params.cascades(csv, game, version):
        d = D.derive(p)
        variants = back_pocket_variants_built(row, d)
        if variants:
            # IN PLACE OF the ordinary box, not beside it: the row ships the
            # variants and nothing else (`back_pocket_variants_built`).
            ds = [(back_pocket_twin(d, v), dataclasses.replace(p, BackPocket=v))
                  for v in variants]
        else:
            ds = [(d, p)]
        if ships_plain_box(row, d):
            ds.append((plain_box_twin(d), dataclasses.replace(p, LabelHolders=0)))
        for dd, pp in ds:
            fn = box_file(dd)
            if model and model.lower() not in fn.lower():
                continue
            out.setdefault((pp.GameName, fn), (pp.GameName, fn, pp))
    return [out[k] for k in sorted(out)]


def ships_plain_box(row, d):
    """Does this row's cascade ship a SECOND box, without label holders, on a
    plate of its own at the end of the project? From 7.2d, and only where
    parts.csv's `Plain box` column says so. The ONLY place the flag is
    asked."""
    if not d.rev.plain_box_plate:
        return False
    return (row.get("Plain box") or "").strip().lower() in ("true", "1", "yes")


def plain_box_twin(d):
    """The same cascade's Derived with the label holders OFF — what the plain
    box on the last plate is built from. Every Primary field rides on the
    Derived by name, so the Primary is rebuilt and re-derived; nothing else
    moves, the model code included. A row whose box already has no holders is
    REFUSED: the twin would be the same file."""
    if not d.isLabelHoldersOnBox:
        refuse(f"{d.calModelName}: the box already has no label holders, so a "
               f"plain twin would be the same box; drop `Plain box` or "
               f"`Label holders` FALSE from its row")
    p = params.Primary(**{f.name: getattr(d, f.name)
                          for f in dataclasses.fields(params.Primary)})
    return D.derive(dataclasses.replace(p, LabelHolders=0))


def back_pocket_variants_built(row, d):
    """The BACKS this row's cascade ships, as `tables.BACK_POCKET_VARIANTS`
    members in project order, or `()` for the ordinary box. From 7.2g, off
    parts.csv's `Back pocket` column, and the ONLY place the column and the
    flag are asked. They REPLACE the ordinary box, and the FIRST is the one
    plate 1 carries and the poster measures. `spec/BOX.md`."""
    want = [v.strip().lower()
            for v in (row.get("Back pocket") or "").replace(",", "+").split("+")
            if v.strip()]
    if not want:
        return ()
    # Checked at EVERY release, before the flag: a typo in the column is a
    # typo whether or not this release reads it.
    unknown = [v for v in want if v not in TB.BACK_POCKET_VARIANTS]
    if unknown:
        refuse(f"parts.csv row {(row.get('Short name') or '?').strip()!r}: "
               f"`Back pocket` names {unknown[0]!r}; one of "
               f"{', '.join(v for v in TB.BACK_POCKET_VARIANTS if v)}")
    if not d.rev.back_pocket_variants:
        return ()
    return tuple(want)


def back_pocket_twin(d, variant):
    """The same cascade's Derived built with one of the variant BACKS —
    `plain_box_twin`'s recipe on `BackPocket`. Nothing but the back moves,
    which is what lets one lid close either box of the pair."""
    if variant not in TB.BACK_POCKET_VARIANTS:
        refuse(f"unknown back pocket variant {variant!r}; one of "
               f"{', '.join(v for v in TB.BACK_POCKET_VARIANTS if v)}")
    p = params.Primary(**{f.name: getattr(d, f.name)
                          for f in dataclasses.fields(params.Primary)})
    return D.derive(dataclasses.replace(p, BackPocket=variant))


def build_box(d, _extra, path):
    """Build one box: NO assembly offset, the part studio's origin being the
    assembly's."""
    from .parts import box as box_part
    return write_component(path, [("Box", box_part.build(d))], d)


def pusher_catalogue(csv=CSV, game=None, model=None, version=R.CURRENT):
    """[(folder, filename, Primary)] — every distinct pusher, on the full key:
    game, risers, cards per slot, first-riser override, sleeving."""
    out = {}
    for _row, p in params.cascades(csv, game, version):
        fn = pusher_file(D.derive(p))
        if model and model.lower() not in fn.lower():
            continue
        key = (p.GameName, p.RisingSliders, p.CardsPerSlidingSlot,
               p.FirstSlidingSlotCards if p.isFirstSlidingSlotOverride else 0,
               p.isSleeved)
        out.setdefault(key, (p.GameName, fn, p))
    return [out[k] for k in sorted(out)]


def token_holder_file(d, half):
    """`TokenHolder <model>.3mf`, keyed on `calTokenHolderModel`, which is what
    the part has ENGRAVED on it. The planner's key is right about the geometry
    and wrong about the engraving, so two Dominion rows collide under it and
    this builder carries the size letter in the name."""
    kind = "HalfTokenHolder" if half else "TokenHolder"
    return f"{kind} {model_stem(d.calTokenHolderModel)}.3mf"


def ships_token_holder(row):
    """Does this row ask for a token holder? parts.csv's `TokenHolder` column,
    blank meaning none; the catalogue and both CLIs ask it HERE."""
    return (row.get("TokenHolder") or "").strip().lower() not in ("", "none")


def token_holder_catalogue(csv=CSV, game=None, model=None, version=R.CURRENT):
    """[(folder, filename, Primary, half)] — every distinct token holder, where
    `ships_token_holder`. The HALF is a Mat-box feature, so a merged row
    yields both."""
    out = {}
    for row, p in params.cascades(csv, game, version):
        if not ships_token_holder(row):
            continue
        d = D.derive(p)
        for half in ((False, True) if p.MatPocket else (False,)):
            fn = token_holder_file(d, half)
            if model and model.lower() not in fn.lower():
                continue
            out.setdefault((p.GameName, fn), (p.GameName, fn, p, half))
    return [out[k] for k in sorted(out)]


def build_token_holder(d, half, path):
    """Build one token holder. Like the Box and the Lid it sits at the part
    studio's origin, which is the assembly's."""
    from .parts import token_holder
    name = "HalfTokenHolder" if half else "TokenHolder"
    return write_component(path, [(name, token_holder.build(d, half))], d)


def build_pusher(d, _extra, path):
    """Build one pusher, place it in assembly position, write the 3MF."""
    from build123d import Location
    from .parts import pusher
    part = pusher.build(d).moved(Location(pusher.assembly_offset(d)))
    return write_component(path, [("Pusher", part)], d, depth=d.calPusherTotalDepth,
                           rise=d.calHeightIncrement,
                           cls=L.lock_class(d.calPusherTotalDepth)[0])


# A build is a list of SPECS — (kind, Primary, extra, targets) — run through
# `_job` in a process pool; each job builds once and writes every target, a
# second target being a copy of the first's bytes. A STAMP beside each file
# digests everything it depends on — the Primary, the kind and its extra, and
# every source under cad/, logos/ and fonts/ — so a rerun with nothing changed
# skips the build and any edit in cad/ invalidates every stamp.

STAMP_DIR = ".stamps"


def out_for(version):
    """Where a release's parts go: `build/` for the current one,
    `build/v<version>/` for any other. Filenames carry NO version (a NAME is
    an identity), so two releases in one tree would overwrite each other part
    for part."""
    R.check(version)
    return ROOT / "build" if version == R.CURRENT else ROOT / "build" / f"v{version}"


def source_hash():
    h = hashlib.sha256()         # all a part depends on but its Primary
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


# Every kind: its builder — `(Derived, extra, path) -> report` — and the
# noun the report uses. The order is the order --part all reports in.
BUILDERS = {"lid": build_lid, "holder": build_holder,
            "tokenholder": build_token_holder, "topper": build_topper,
            "box": build_box, "pusher": build_pusher}
KINDS = tuple(BUILDERS)
NOUN = {"lid": "lids", "holder": "holders", "tokenholder": "token holders",
        "topper": "toppers", "box": "boxes", "pusher": "pushers"}


def _job(spec):
    kind, p, extra = spec["kind"], spec["p"], spec["extra"]
    out_dir, targets = spec["out_dir"], spec["targets"]
    if not spec["force"] and all(
            (out_dir / f / fn).exists()
            and stamp_path(out_dir, f, fn).exists()
            and stamp_path(out_dir, f, fn).read_text() == spec["stamp"]
            for f, fn in targets):
        return [{"path": out_dir / f / fn, "folder": f, "filename": fn, "kind": kind,
                 "bytes": (out_dir / f / fn).stat().st_size,
                 "skipped": True, "changed": False, "new": False}
                for f, fn in targets]
    folder, fn = targets[0]
    t0 = time.perf_counter()
    r = BUILDERS[kind](D.derive(p), extra, out_dir / folder / fn)
    r.update(folder=folder, filename=fn, skipped=False, kind=kind,
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


# What a job costs, roughly, in seconds of one core — for ordering ONE pool
# over every kind longest first, so the last box or Compile lid is not
# started when nine cores are already idle. A lid costs what its mark costs.
COST = {"lid": 8.0, "box": 7.0, "pusher": 3.0, "holder": 1.5, "topper": 1.0,
        "tokenholder": 1.0}
LID_COST = {"Compile": 13.0, "Innovation": 7.0, "FCM": 4.0, "Dominion": 2.5}


def cost(spec):
    if spec["kind"] == "lid":
        return LID_COST.get(spec["p"].GameName, COST["lid"])
    return COST[spec["kind"]]


def run_jobs(specs, jobs):
    """Every spec through `_job`, in the order given, `jobs` at a time — one
    worker per core by default, each meshing SINGLE-threaded
    (`mesh3mf.serial_meshing`): the workers are the parallelism."""
    if jobs <= 1 or len(specs) <= 1:
        return [_job(s) for s in specs]
    import concurrent.futures as cf
    import multiprocessing as mp
    with cf.ProcessPoolExecutor(max_workers=min(jobs, len(specs)),
                                mp_context=mp.get_context("spawn"),
                                initializer=mesh3mf.serial_meshing) as ex:
        return list(ex.map(_job, specs))


def holder_key(p, extra):
    """What a holder's geometry depends on: everything in its Primary but the
    front capacity and the Mat branch, plus its kind `(first, rear)`. Two
    files with one key are ONE build."""
    return (p.GameName, p.HorizontalSlots, p.RisingSliders,
            p.CardsPerSlidingSlot, p.isFirstSlidingSlotOverride,
            p.FirstSlidingSlotCards, p.isSleeved, p.Version,
            p.SleevedCardWidth, p.DeepSlotAtBack, tuple(extra))


# Every kind's catalogue, `(csv, game, model, version) -> items`. The Box's
# and the Pusher's have no `extra`; the rest yield one.
CATALOGUES = {"lid": lid_catalogue, "holder": holder_catalogue,
              "tokenholder": token_holder_catalogue, "topper": topper_catalogue,
              "box": box_catalogue, "pusher": pusher_catalogue}


def specs_for(kind, args, src):
    items = CATALOGUES[kind](args.csv, args.game, args.model, args.version)
    if kind in ("box", "pusher"):
        items = [(f, fn, p, None) for f, fn, p in items]
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
    mark = ("skipped" if r["skipped"] else "new" if r["new"]
            else "changed" if r["changed"] else "")
    name = f"{r['folder']}/{r['filename']}"
    if r["skipped"]:
        return f"  {name:44s} {'':>11s} {r['bytes'] / 1024:6.0f}  {mark}"
    if kind == "pusher":
        return (f"  {name:44s} D {r['depth']:6.2f} rise {r['rise']:6.3f} "
                f"{r['cls']:>3s} {r['verts']:7d} {r['tris']:7d} "
                f"{r['bytes'] / 1024:6.0f}  {r['seconds']:5.1f}s  {mark}")
    return (f"  {name:44s} {r['volume']:11.1f} {r['bodies']:4d} {r['verts']:7d} "
            f"{r['tris']:7d} {r['bytes'] / 1024:6.0f}  {r['seconds']:5.1f}s  "
            f"{mark}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", help="Compile / Dominion / FCM / Innovation")
    ap.add_argument("--out", type=Path,
                    help="where the parts go (default: build/ for the current "
                         f"release, build/v<version>/ for any other, so two "
                         "releases cannot land in one tree under the same "
                         "filenames)")
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--list", action="store_true", help="print, do not build")
    ap.add_argument("--part", choices=KINDS + ("all",), default="pusher",
                    help="what to build; `all` is the lot, a few minutes with "
                         "the pool")
    ap.add_argument("--model", help="build only parts whose filename contains "
                                    "this, e.g. S2.40.12-30.45-Sl")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1,
                    help="parallel builds (default: every core); 1 is serial")
    ap.add_argument("--version", default=R.CURRENT, choices=R.RELEASES,
                    help=f"the release to build (default {R.CURRENT}); what "
                         "differs between releases is cad/revisions.py, and "
                         "--out follows the version unless you set it")
    ap.add_argument("--force", action="store_true",
                    help="rebuild even where the stamp says nothing changed")
    args = ap.parse_args(argv)
    args.out = args.out or out_for(args.version)
    try:
        return run(args)
    except Refused as e:
        print(f"  {e}")
        return 1


def run(args):
    kinds = KINDS if args.part == "all" else (args.part,)
    src = source_hash()
    catalogue = {kind: specs_for(kind, args, src) for kind in kinds}
    if args.list:
        for kind, (items, _specs) in catalogue.items():
            for folder, fn, p, _extra in items:
                line = f"  {folder + '/' + fn}"
                if kind == "pusher":
                    d = D.derive(p)
                    line = (f"  {folder + '/' + fn:40s} D {d.calPusherTotalDepth:6.2f}  "
                            f"{L.lock_class(d.calPusherTotalDepth)[0]}")
                print(line)
            print(f"\n  {len(items)} {NOUN[kind]}\n")
        return 0

    # ONE pool over every kind, longest jobs first: six pools in sequence each
    # paid ten worker start-ups and idled through its own tail.
    every = [spec for _items, specs in catalogue.values() for spec in specs]
    every.sort(key=cost, reverse=True)
    t0 = time.perf_counter()
    results = {kind: [] for kind in kinds}
    for group in run_jobs(every, args.jobs):
        for r in group:
            results[r["kind"]].append(r)
    for kind in kinds:
        report(kind, sorted(results[kind], key=lambda r: (r["folder"], r["filename"])), args)
    print(f"  {len(kinds)} kind{'' if len(kinds) == 1 else 's'} in "
          f"{(time.perf_counter() - t0) / 60:.1f} min: one pool of {args.jobs} over "
          f"{len(every)} jobs")
    return 0


def report(kind, results, args):
    for r in results:
        print(_row(kind, r))
    if kind == "lid":
        plain = sorted({r["folder"] for r in results
                        if not r["skipped"] and r["bodies"] == 1})
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
          f"{sum(r.get('seconds', 0.0) for r in results):.0f} s of build, in {args.out}\n")


if __name__ == "__main__":
    sys.exit(main())
