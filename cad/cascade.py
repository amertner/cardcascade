"""A cascade from its parts.csv row: its parts, its layout, its project.

    .venv/bin/python -m cad.cascade --model S4.16.10.32-Un        # one
    .venv/bin/python -m cad.cascade --game Dominion --sleeving un  # some
    .venv/bin/python -m cad.cascade --build --slice                # all, checked

Row in, project out, no donor and no plan: the parts are read from `build/`
by the names `cad.build` gives them — the names that ARE a part's identity,
being what is engraved on it, so two cascades that need the same holder ask
for the same file and nothing has to be deduplicated — the bed is the row's
`3D printer` column (or the smallest that fits), `cad.layout` places
everything, `cad.project` writes the file, and the two project guards run on
it before it counts. `--build` runs `cad.build --part all` first, which the
stamps make a no-op when nothing changed; `--slice` has BambuStudio slice
every plate and requires return_code 0, the only check that sees a tower in
unprintable space. Projects go to `build/cascades/<Game>/` unless `--out`
says otherwise — the parallel period's tree, beside `cascades/`.

`--publish` writes the set that LEAVES the repo, to `build/dist/<version>/`:
the same projects with the version in their file names. In the repo a name is
an identity and the version lives in the title and the engraving; on a
download the name is the first thing its owner reads. See `filename`.

The composition rules are `automation/PIPELINE.md`'s ("Component composition")
and `automation/components.py`'s per-game policy, restated in `parts`.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from . import build as B, derive as D, layout as LY, params, project as PJ, tables as TB
from .lock import GENERATION
from .refuse import Refused, refuse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automation"))
import components as C                                   # noqa: E402
import filaments as FIL                                  # noqa: E402
import towers                                            # noqa: E402

BUILD = ROOT / "build"
OUT = BUILD / "cascades"
DIST = BUILD / "dist"          # --publish; under build/, so already gitignored
CSV = ROOT / "automation" / "parts.csv"
STUDIO = Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")


def parts(row, p, d):
    """[(object name, filename under build/<Game>/)] — every printed thing
    the cascade `row` (with its sleeving already in `p`) is made of, in the
    order the plate scheme lists them.

    * one Box, `calPusherSlots` Pushers (`#calPusherSlots` is the studio's
      count of rear slots: 2 for Innovation and for S boxes, 3 for M and L);
    * `RisingSliders` Holders — one of them the deeper FirstHolder when the row
      overrides the first slot's capacity;
    * one Lid;
    * Dominion: a TokenHolder where the row's `TokenHolder` column says `full`,
      and a HalfTokenHolder as well on a merged (Mat) row — the two are
      alternatives for one pocket, and the cascade ships both;
    * Innovation: the six Toppers, one per expansion plus Blank, except on
      the rows `components.no_toppers` names (a box built for ONE set has
      nothing for a topper to say).
    """
    out = [("Box", B.box_file(d))]
    out += [("Pusher", B.pusher_file(p))] * d.calPusherSlots
    if p.isFirstSlidingSlotOverride:
        out.append(("FirstHolder", B.holder_file(d, first=True)))
        out += [("Holder", B.holder_file(d))] * (p.RisingSliders - 1)
    else:
        out += [("Holder", B.holder_file(d))] * p.RisingSliders
    out.append((PJ.object_name("Lid", p, d), B.lid_file(d)))
    if p.GameName == "Dominion" and (row.get("TokenHolder") or "").strip().lower() == "full":
        out.append(("TokenHolder", B.token_holder_file(d, half=False)))
        if p.MatPocket:
            out.append(("HalfTokenHolder", B.token_holder_file(d, half=True)))
    spec = C.GAMES.get(p.GameName) or {}
    short = (row.get("Short name") or "").strip()
    if p.GameName == "Innovation" and short not in spec.get("no_toppers", set()):
        for exp in TB.TOPPERS:
            out.append((f"Topper {exp}", B.topper_file(p, d, exp)))
    return out


def objects(row, p, d, root=BUILD):
    """The parts as `project.Obj`s, read from `root/<Game>/`. A missing file
    is named rather than guessed around — build it first."""
    folder = root / p.GameName
    wanted = parts(row, p, d)
    missing = sorted({fn for _n, fn in wanted if not (folder / fn).exists()})
    if missing:
        refuse(f"not built under {folder}: {missing} — run python -m cad.build --part all")
    cache = {}
    out = []
    for name, fn in wanted:
        if fn not in cache:
            cache[fn] = PJ.Obj.from_file(name, folder / fn)
        out.append(PJ.Obj(name, cache[fn].parts, cache[fn].source))
    return out


def _named(row, p, d, version):
    """`components.cascade_filename` for this row, at `version` (None: none)."""
    model = (row.get("Sleeved model" if p.isSleeved else "Unsl Model") or "").strip()
    return C.cascade_filename((row.get("Game") or p.GameName).strip(),
                              (row.get("Short name") or "").strip(),
                              "Sl" if p.isSleeved else "Un", model, version,
                              (row.get("Project label") or "").strip())


def filename(row, p, d, versioned=False):
    """The project's FILE name. No version in it by default.

    The version in a name serves one reader: someone holding a downloaded file,
    deciding whether the pusher in their hand matches the lid. In the repo there
    is no such reader — the tree is addressed by path — and it costs the whole
    catalogue a rename on every release, which `refresh_cascades.find_project`
    already records happening once: "every one of them did, the day the version
    went into it". Tags carry a release; a filename should carry an identity.

    So `build/cascades/` and `cascades/` hold the stable name, and `--publish`
    puts the version back for the tree that leaves the repo. What the file says
    about itself does NOT change with it — see `title` below."""
    return _named(row, p, d, p.Version if versioned else None)


def title(row, p, d):
    """The project's TITLE, which ALWAYS carries the version:
    `Dominion 168 Card Unsleeved v7.0 (S4.16.10.32-Un)`.

    A filename is the one identifier its owner can trivially change, so the
    version cannot live only there. `project.write` puts this in the 3MF's
    `Title` metadata and at the end of every plate name, where Studio shows it
    and no rename can touch it. The version is `p.Version` — what `cad.build`
    stamped every part with, and on this path that really is every part, so the
    title and the engraving say the same thing."""
    return _named(row, p, d, p.Version)[:-len(".3mf")]


def bed_for(row, p):
    """The bed parts.csv's `3D printer` column names — Mini, Standard, Large,
    or Mixed (P1 unsleeved, H2C sleeved: the sleeved box is deeper) — or None
    for the layout to pick the smallest that fits. `refresh_cascades.bed_for`."""
    kind = (row.get("3D printer") or "").strip().lower()
    if kind == "mini":
        return "mini"
    if kind == "standard":
        return "p1"
    if kind == "large":
        return "h2c"
    if kind == "mixed":
        return "h2c" if p.isSleeved else "p1"
    return None


def source_stamp():
    """`<git hash>[+dirty]` of the working tree — what produced the project."""
    try:
        h = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "cad", "logos",
                                "fonts", "automation/parts.csv", "automation/profiles"],
                               capture_output=True, text=True).stdout.strip()
        return h + ("+dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def row_stamp(row):
    return hashlib.sha1(json.dumps(sorted(row.items())).encode()).hexdigest()[:12]


def catalogue(csv=CSV, game=None, model=None, size=None, sleeving=None, name=None,
              version=GENERATION):
    """[(row, p, d)] for the cascades selected."""
    sizes = [x.strip().upper() for x in size.split(",")] if size else None
    out = []
    for row, p in params.cascades(csv, game, version):
        if name and name.lower() not in (row.get("Short name") or "").lower():
            continue
        if sleeving and sleeving.lower()[:2] != ("sl" if p.isSleeved else "un"):
            continue
        d = D.derive(p)
        if not B.model_matches(d, model):
            continue
        if sizes and d.calSizeLetter.upper() not in sizes:
            continue
        out.append((row, p, d))
    return out


def make(row, p, d, out_dir=OUT, bed=None, do_slice=False, root=BUILD,
         versioned=False):
    """One cascade's project, written and checked. Returns (path, notes)."""
    objs = objects(row, p, d, root)
    chosen, plates, places = LY.layout(objs, bed or bed_for(row, p))
    path = Path(out_dir) / p.GameName / filename(row, p, d, versioned)
    PJ.write(path, chosen, objs, plates, places, title=title(row, p, d),
             metadata={"cardcascade:model": d.calModelName,
                       "cardcascade:source": source_stamp(),
                       "cardcascade:row": row_stamp(row),
                       "cardcascade:version": p.Version})
    ps = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    blocking = [x for x in FIL.makerworld_problems(ps) if x[3]]
    if blocking:
        refuse(f"{path.name}: MakerWorld would reject it: {blocking}")
    bad = towers.problems(path)
    if bad:
        refuse(f"{path.name}: prime tower outside a nozzle's reach: {bad}")
    notes = [f"{chosen} x{len(plates)}"]
    if do_slice:
        if not STUDIO.exists():
            refuse("--slice needs BambuStudio.app")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([str(STUDIO), "--slice", "0", "--outputdir", tmp, str(path)],
                           capture_output=True, text=True, timeout=1800)
            result = Path(tmp) / "result.json"
            rc = json.loads(result.read_text()).get("return_code") if result.exists() else None
            if rc != 0:
                err = json.loads(result.read_text()).get("error_string") if result.exists() else "no result.json"
                refuse(f"{path.name}: slice return_code {rc}: {err}")
            notes.append(f"sliced {len(list(Path(tmp).glob('*.gcode')))} plates")
    return path, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", help="Compile / Dominion / FCM / Innovation")
    ap.add_argument("--model", help="a model code or part of one, e.g. S4.16.10.32-Un")
    ap.add_argument("--size", help="size letters, e.g. S,M")
    ap.add_argument("--sleeving", choices=("un", "sl"))
    ap.add_argument("--name", help="part of the row's Short name, e.g. 168")
    ap.add_argument("--bed", choices=tuple(PJ.BEDS), help="force the bed for every cascade")
    ap.add_argument("--out", type=Path,
                    help="default build/cascades/, or build/dist/<version>/ "
                         "with --publish")
    ap.add_argument("--publish", action="store_true",
                    help="the set to upload: the version goes into the file "
                         "NAME as well as the title, and the default --out "
                         "becomes build/dist/<version>/ — a tree outside git "
                         "that keeps the exact bytes you sent, which a "
                         "MakerWorld rejection needs (never re-save one in "
                         "Studio; automation/filaments.py --makerworld)")
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--components", default=BUILD, type=Path,
                    help="where the parts are (build/)")
    ap.add_argument("--version", default=GENERATION,
                    help="the version the parts are stamped with; the parts under "
                         "--components must have been built at it (cad.build --version)")
    ap.add_argument("--build", action="store_true", help="run cad.build --part all first")
    ap.add_argument("--slice", action="store_true", help="slice every project with BambuStudio")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)

    out = args.out or (DIST / args.version if args.publish else OUT)
    rows = catalogue(args.csv, args.game, args.model, args.size, args.sleeving, args.name,
                     args.version)
    if args.list:
        for row, p, d in rows:
            print(f"  {p.GameName}/{filename(row, p, d, args.publish)}"
                  f"  bed {bed_for(row, p) or 'auto'}")
        print(f"\n  {len(rows)} cascade{'' if len(rows) == 1 else 's'}")
        return 0
    if args.build:
        print("● cad.build --part all")
        rc = B.main(["--part", "all", "--csv", str(args.csv), "--version", args.version,
                     "--out", str(args.components)])
        if rc:
            return rc
    print(f"  {'project':62s} {'layout':10s} notes")
    failed = []
    for row, p, d in rows:
        try:
            path, notes = make(row, p, d, out, args.bed, args.slice,
                               args.components, args.publish)
        except Refused as e:
            failed.append(f"{p.GameName}/{title(row, p, d)}: {e.reason}")
            print(f"  {p.GameName + '/' + title(row, p, d):62s} {'REFUSED':10s} {e.reason}")
            continue
        print(f"  {p.GameName + '/' + path.name:62s} {notes[0]:10s} {'; '.join(notes[1:])}")
    print(f"\n  {len(rows) - len(failed)} of {len(rows)} written to {out}")
    for f in failed:
        print(f"  refused  {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
