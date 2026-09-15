"""LEGACY: stage built components under the planner's names for refresh_cascades.

`cad.build` names a file by what is ENGRAVED on it; `plan_exports.compose` by
its DEDUP KEY, and everything downstream knows only the planner's names. This
writes that root, so the Onshape pipeline can consume it for `individual/`:

    python -m cad.promote --model S4.16.10.32-Un        # one cascade
    python -m cad.promote --game Dominion               # a game
    python -m cad.promote                               # everything built

copying each `build/v7.0/<Game>/<cad name>.3mf` to
`build/components/<Game>/<planner name>.3mf`, and then

    automation/refresh_cascades.py --components build/components \\
        --out build/promoted --game Dominion --name 168 --auto

builds the project from them without touching `cascades/`, `individual/` or
`cad.cascade`'s own `build/cascades/`. The two collisions the planner's keys
carry (`spec/TOKENHOLDER.md`) are REFUSED, not resolved. Zero API calls.
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automation"))

import components as C                                  # noqa: E402
import plan_exports as P                                # noqa: E402
from . import build as B, derive as D, lock as L, params  # noqa: E402

# The tree promotion reads, and it is the LOCK GENERATION's and NOT the
# current release's. `cad.build --part all --version 7.0` first.
SOURCE = B.out_for(L.GENERATION)
DEFAULT_OUT = ROOT / "build" / "components"


def built_name(item, d):
    """The `build/` filename for one planner component, or None for a kind
    `cad/` does not make (a `Label`; `labelmaker.py` makes those)."""
    kind = item["type"]
    if kind == "Box":
        return B.box_file(d)
    if kind == "Lid":
        return B.lid_file(d)
    if kind == "Pusher":
        return B.pusher_file(d)
    if kind == "Holder":
        return B.holder_file(d, first=item.get("instance") == "first")
    if kind == "TokenHolder":
        return B.token_holder_file(d, half=False)
    if kind == "HalfTokenHolder":
        return B.token_holder_file(d, half=True)
    if kind == "Topper":
        return B.topper_file(d, expansion=item["key"][1])
    return None


def stage(games, out, model=None, name=None, dry=False):
    """Copy every matching cascade's components. Returns (staged, missing,
    collisions, unmade) — counts and lists for the caller to report."""
    plan_for = {}        # planner name -> (built path) per folder, for collisions
    staged, missing, collisions, unmade = [], [], [], []
    copied = set()
    for game, spec in games:
        plan = P.compute_plan(game, spec, str(B.CSV))
        folder = spec["folder"]
        for casc in plan.cascades:
            if model and model.lower() not in casc["model"].lower():
                continue
            if name and name.lower() not in casc["ctx"]["short_name"].lower():
                continue
            # PINNED to the lock generation, NOT the current release: a
            # promoted part lands in a cascade recorded as 7.0, so the current
            # release's stamp is the drift `verify.py --stamps` catches.
            p = params.from_row(casc["row"], 1 if casc["sleeved"] == "Sl" else 0,
                                version=L.GENERATION)
            d = D.derive(p)
            for item in casc["components"]:
                fn = built_name(item, d)
                if fn is None:
                    unmade.append(f"{folder}/{item['file']} ({casc['name']})")
                    continue
                src = SOURCE / folder / fn
                dst = out / folder / item["file"]
                prior = plan_for.get(dst)
                if prior is not None and prior != src:
                    # Two built files under one planner name. The Mat twins are
                    # byte-identical and no collision; the token holders differ
                    # in the engraved size letter and are.
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
        print(f"  {str(src.relative_to(SOURCE)):40s} -> {dst.relative_to(args.out)}")
    if unmade:
        print(f"\nnot built by cad/ ({len(unmade)}) — labels are labelmaker.py's:")
        for u in unmade:
            print(f"  {u}")
    if missing:
        print(f"\nMISSING in {SOURCE.relative_to(ROOT)}/ ({len(missing)}) — run "
              f"`python -m cad.build --part all --version {L.GENERATION}` first:")
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
