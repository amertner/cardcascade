"""Stage `build/` components under the planner's own names, so the existing
cascade pipeline can consume them in place of `individual/`.

`cad.build` names a file by what is engraved on it — `Holder S4.16.10.32-Un`,
`TokenHolder M21-Sl`, a pusher with its first-riser axis — where
`plan_exports.compose` names the same part by its dedup key — `Holder
S-16-r4-Un`, `TokenHolder 21-Sl`, `Pusher 6x10-Sl`. Everything downstream of
a component (`make_cascade`, `refresh_cascades`, `verify`) knows only the
planner's names, and `refresh_cascades` looks them up under one root. This
writes that root:

    python -m cad.promote --model S4.16.10.32-Un        # one cascade
    python -m cad.promote --game Dominion               # a game
    python -m cad.promote                               # everything built

copying each `build/<Game>/<cad name>.3mf` to
`build/components/<Game>/<planner name>.3mf`, and then

    automation/refresh_cascades.py --components build/components \\
        --out build/cascades --game Dominion --name 168 --auto

builds the project from them without touching `cascades/` or `individual/`.
Nothing here writes into `individual/`: that is a promotion of a different
kind, and the two collisions the planner's keys carry (`spec/TOKENHOLDER.md`,
`cad/README.md` decision 5) are refused rather than resolved — where two
cascades would put two different built files under one planner name, both are
named and neither is staged.

Zero Onshape API calls.
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automation"))

import components as C                                  # noqa: E402
import plan_exports as P                                # noqa: E402
from . import build as B, derive as D, params           # noqa: E402

BUILD = ROOT / "build"
DEFAULT_OUT = BUILD / "components"


def built_name(item, p, d):
    """The `build/` filename for one planner component, or None for a kind
    `cad/` does not make (the Onshape-drawn Compile label)."""
    kind = item["type"]
    if kind == "Box":
        return B.box_file(d)
    if kind == "Lid":
        return B.lid_file(d)
    if kind == "Pusher":
        return B.pusher_file(p)
    if kind == "Holder":
        return B.holder_file(d, first=item.get("instance") == "first")
    if kind == "TokenHolder":
        return B.token_holder_file(d, half=False)
    if kind == "HalfTokenHolder":
        return B.token_holder_file(d, half=True)
    if kind == "Topper":
        return B.topper_file(p, d, expansion=item["key"][1])
    return None


def stage(games, out, model=None, name=None, dry=False):
    """Copy every matching cascade's components. Returns (staged, missing,
    collisions, unmade) — counts and lists for the caller to report."""
    plan_for = {}        # planner name -> (built path) per folder, for collisions
    staged, missing, collisions, unmade = [], [], [], []
    copied = set()
    for game, spec in games:
        plan = P.compute_plan(game, spec, str(ROOT / "automation" / "parts.csv"))
        folder = spec["folder"]
        for casc in plan.cascades:
            if model and model.lower() not in casc["model"].lower():
                continue
            if name and name.lower() not in casc["ctx"]["short_name"].lower():
                continue
            p = params.from_row(casc["row"], 1 if casc["sleeved"] == "Sl" else 0)
            d = D.derive(p)
            for item in casc["components"]:
                fn = built_name(item, p, d)
                if fn is None:
                    unmade.append(f"{folder}/{item['file']} ({casc['name']})")
                    continue
                src = BUILD / folder / fn
                dst = out / folder / item["file"]
                prior = plan_for.get(dst)
                if prior is not None and prior != src:
                    # Two built files under one planner name. The Mat twins
                    # (`Holder M4.21.10.45-M-Sl` and `-Sl`) are byte-identical
                    # — the Mat branch does not touch a holder — and that is
                    # no collision. The token holders differ in the engraved
                    # size letter and are: spec/TOKENHOLDER.md.
                    if not (prior.exists() and src.exists()
                            and prior.read_bytes() == src.read_bytes()):
                        collisions.append(f"{dst.relative_to(out)}: "
                                          f"{prior.name} and {src.name}")
                    continue
                plan_for[dst] = src
                if not src.exists():
                    missing.append(f"{folder}/{fn} (for {item['file']})")
                    continue
                if dst in copied:
                    continue
                copied.add(dst)
                staged.append((src, dst))
                if not dry:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
    return staged, sorted(set(missing)), sorted(set(collisions)), sorted(set(unmade))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game", help="Compile / Dominion / FCM / Innovation")
    ap.add_argument("--model", help="only cascades whose model code contains this")
    ap.add_argument("--name", help="only cascades whose Short name contains this")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"component root to write (default {DEFAULT_OUT.relative_to(ROOT)})")
    ap.add_argument("--dry-run", action="store_true", help="report, copy nothing")
    args = ap.parse_args()

    if args.game:
        games = [C.game_by_name(args.game)]
    else:
        games = list(C.GAMES.items())
    staged, missing, collisions, unmade = stage(
        games, args.out, args.model, args.name, args.dry_run)

    verb = "would stage" if args.dry_run else "staged"
    print(f"{verb} {len(staged)} component(s) under {args.out}")
    for src, dst in staged:
        print(f"  {str(src.relative_to(BUILD)):40s} -> {dst.relative_to(args.out)}")
    if unmade:
        print(f"\nnot built by cad/ ({len(unmade)}) — these stay Onshape's:")
        for u in unmade:
            print(f"  {u}")
    if missing:
        print(f"\nMISSING in build/ ({len(missing)}) — run `python -m cad.build "
              f"--part all` first:")
        for m in missing:
            print(f"  {m}")
    if collisions:
        print(f"\nCOLLISIONS ({len(collisions)}) — two built files, one planner "
              f"name; neither staged:")
        for c in collisions:
            print(f"  {c}")
    sys.exit(1 if (missing or collisions) else 0)


if __name__ == "__main__":
    main()
