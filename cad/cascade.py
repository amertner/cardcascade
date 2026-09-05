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

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automation"))
import components as C                                   # noqa: E402
import filaments as FIL                                  # noqa: E402
import towers                                            # noqa: E402

BUILD = ROOT / "build"
OUT = BUILD / "cascades"
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
        for exp in TB.TOPPER_EXPANSIONS + ("Blank",):
            out.append((f"Topper {exp}", B.topper_file(p, d, exp)))
    return out


def objects(row, p, d, root=BUILD):
    """The parts as `project.Obj`s, read from `root/<Game>/`. A missing file
    is named rather than guessed around — build it first."""
    folder = root / p.GameName
    missing = sorted({fn for _n, fn in parts(row, p, d) if not (folder / fn).exists()})
    if missing:
        raise SystemExit(f"REFUSING: not built under {folder}: {missing} — "
                         f"run python -m cad.build --part all")
    cache = {}
    out = []
    for name, fn in parts(row, p, d):
        if fn not in cache:
            cache[fn] = PJ.Obj.from_file(name, folder / fn)
        obj = cache[fn]
        out.append(PJ.Obj(name, obj.parts))
    return out


def title(row, p, d):
    """The project's name, `components.cascade_filename` without the suffix:
    `Dominion 168 Card Unsleeved (S4.16.10.32-Un)`. The model code is the
    row's own per-sleeving column, as the shipped names have it."""
    model = (row.get("Sleeved model" if p.isSleeved else "Unsl Model") or "").strip()
    return C.cascade_filename((row.get("Game") or p.GameName).strip(),
                              (row.get("Short name") or "").strip(),
                              "Sl" if p.isSleeved else "Un", model)[:-len(".3mf")]


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


def catalogue(csv=CSV, game=None, model=None, size=None, sleeving=None, name=None):
    """[(row, p, d)] for the cascades selected, Parked rows skipped."""
    out = []
    for row in params.load_rows(csv):
        if (row.get("Status") or "").strip() == "Parked":
            continue
        if game and (row.get("Game") or "").strip() not in (game, params.GAME_NAME.get(game, game)) \
                and params.GAME_NAME.get((row.get("Game") or "").strip()) != game:
            continue
        if name and name.lower() not in (row.get("Short name") or "").lower():
            continue
        for sleeved in (0, 1):
            if sleeving and sleeving.lower()[:2] != ("sl" if sleeved else "un"):
                continue
            p = params.from_row(row, sleeved)
            d = D.derive(p)
            if model and model not in d.calModelName.replace(".Un", "-Un").replace(".Sl", "-Sl") \
                    and model not in d.calModelName:
                continue
            if size and d.calSizeLetter.upper() not in [x.strip().upper() for x in size.split(",")]:
                continue
            out.append((row, p, d))
    return out


def make(row, p, d, out_dir=OUT, bed=None, do_slice=False, root=BUILD):
    """One cascade's project, written and checked. Returns (path, notes)."""
    objs = objects(row, p, d, root)
    chosen, plates, places = LY.layout(objs, bed or bed_for(row, p))
    path = Path(out_dir) / p.GameName / (title(row, p, d) + ".3mf")
    PJ.write(path, chosen, objs, plates, places, title=title(row, p, d),
             metadata={"cardcascade:model": d.calModelName,
                       "cardcascade:source": source_stamp(),
                       "cardcascade:row": row_stamp(row),
                       "cardcascade:version": p.Version})
    ps = json.loads(zipfile.ZipFile(path).read("Metadata/project_settings.config"))
    blocking = [x for x in FIL.makerworld_problems(ps) if x[3]]
    if blocking:
        raise SystemExit(f"REFUSING: {path.name}: MakerWorld would reject it: {blocking}")
    bad = towers.problems(path)
    if bad:
        raise SystemExit(f"REFUSING: {path.name}: prime tower outside a nozzle's reach: {bad}")
    notes = [f"{chosen} x{len(plates)}"]
    if do_slice:
        if not STUDIO.exists():
            raise SystemExit("REFUSING: --slice needs BambuStudio.app")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([str(STUDIO), "--slice", "0", "--outputdir", tmp, str(path)],
                           capture_output=True, text=True, timeout=1800)
            result = Path(tmp) / "result.json"
            rc = json.loads(result.read_text()).get("return_code") if result.exists() else None
            if rc != 0:
                err = json.loads(result.read_text()).get("error_string") if result.exists() else "no result.json"
                raise SystemExit(f"REFUSING: {path.name}: slice return_code {rc}: {err}")
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
    ap.add_argument("--out", default=OUT, type=Path)
    ap.add_argument("--csv", default=CSV, type=Path)
    ap.add_argument("--components", default=BUILD, type=Path,
                    help="where the parts are (build/)")
    ap.add_argument("--build", action="store_true", help="run cad.build --part all first")
    ap.add_argument("--slice", action="store_true", help="slice every project with BambuStudio")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)

    rows = catalogue(args.csv, args.game, args.model, args.size, args.sleeving, args.name)
    if args.list:
        for row, p, d in rows:
            print(f"  {p.GameName}/{title(row, p, d)}  bed {bed_for(row, p) or 'auto'}")
        print(f"\n  {len(rows)} cascade{'' if len(rows) == 1 else 's'}")
        return 0
    if args.build:
        print("● cad.build --part all")
        rc = B.main(["--part", "all", "--csv", str(args.csv)])
        if rc:
            return rc
    print(f"  {'project':62s} {'layout':10s} notes")
    failed = []
    for row, p, d in rows:
        try:
            path, notes = make(row, p, d, args.out, args.bed, args.slice, args.components)
        except SystemExit as e:
            failed.append(f"{p.GameName}/{title(row, p, d)}: {e}")
            print(f"  {p.GameName + '/' + title(row, p, d):62s} {'REFUSED':10s} {e}")
            continue
        print(f"  {p.GameName + '/' + path.name:62s} {notes[0]:10s} {'; '.join(notes[1:])}")
    print(f"\n  {len(rows) - len(failed)} of {len(rows)} written to {args.out}")
    for f in failed:
        print(f"  refused  {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
