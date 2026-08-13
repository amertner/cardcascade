#!/usr/bin/env python3
"""Interactive end-to-end cascade refresh (pipeline Stages 1 -> 3).

Refreshes a filtered set of cascades:

    PLAN     compute_plan (offline, 0 API calls) — what's selected, what's stale
    EXPORT   re-export only stale/missing components from Onshape (budget-gated)
    ASSEMBLE make_cascade — by default --keep-layout (swap refreshed meshes into
             each cascade's project, preserving its hand-tuned plates). With
             --rebuild, --auto-plates instead: regenerate the layout from the
             box's own project as donor, bed chosen from parts.csv (Standard→P1,
             Large→H2C, Mixed→P1 unsleeved/H2C sleeved) — the general "auto-build"
             for first-building a box whose only project is stale/mislabeled.

Each step asks for confirmation. `--auto` skips the two OFFLINE prompts (PLAN and
ASSEMBLE) but the Onshape EXPORT step ALWAYS confirms before spending the tiny
~2500-calls/year API budget — even under --auto.

Filter the set with --game / --size / --sleeving / --name (AND-combined); with
no --game every game is in scope. --changed forces a component type to re-export
even when provenance calls it current, scoped to those same filters.

Usage:
    refresh_cascades.py --game Dominion --size M --sleeving sl
    refresh_cascades.py --game Innovation --auto
    refresh_cascades.py --size L                     # every game's Large cascades
    refresh_cascades.py --game Dominion --name 168 --sleeving sl --changed Lid
    refresh_cascades.py --standardize-names --game Dominion   # one-off rename
"""
import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import components as C
import onshape_config as OC
import plan_exports as P
import provenance as PROV

HERE = Path(__file__).parent          # automation/
ROOT = HERE.parent                    # repo root — cascades/ and individual/ live here


# ----------------------------------------------------------------- selection
def resolve_games(game_arg):
    """[(game, spec)] for the run: one resolved game, or every game."""
    if game_arg:
        game, spec = C.game_by_name(game_arg)
        if not spec:
            sys.exit(f"unknown game {game_arg!r}; known: {list(C.GAMES)}")
        return [(game, spec)]
    return list(C.GAMES.items())


def matches(casc, sizes, sleeving, name):
    ctx = casc["ctx"]
    if sizes and ctx["size"] not in sizes:
        return False
    if sleeving and casc["sleeved"] != sleeving:
        return False
    if name and name.lower() not in ctx["short_name"].lower():
        return False
    return True


def select(games, sizes, sleeving, name, labels, changed=frozenset()):
    """Per-game plan + the cascades that pass the filters. Returns
    [(game, spec, plan, [cascade, ...])] for games with at least one match.

    `changed` forces those component types to count as stale even when
    provenance says they are current — the only way to re-export a component
    whose version is right but whose FILE is not what you want (an adopted lid
    still embossing the previous version). The filters keep the blast radius to
    the selected cascades: stale_keys intersects the plan with them, so
    --changed Lid --name '168' re-exports one lid, not the game's twenty."""
    out = []
    for game, spec in games:
        plan = P.compute_plan(game, spec, str(HERE / "parts.csv"), labels,
                              changed)
        cs = [c for c in plan.cascades if matches(c, sizes, sleeving, name)]
        if cs:
            out.append((game, spec, plan, cs))
    return out


# ----------------------------------------------------------------- prompting
def confirm(msg, auto, default=True, always_ask=False):
    """Yes/no prompt. `auto` auto-approves unless `always_ask` (the API-spend
    gate). `default` is the answer for an empty reply."""
    if auto and not always_ask:
        print(f"{msg}  → auto-yes")
        return True
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        reply = input(f"{msg} {suffix} ").strip().lower()
    except EOFError:
        return default
    if not reply:
        return default
    return reply[0] == "y"


# ----------------------------------------------------------------- plan step
def stale_keys(plan, cascades):
    """Dedup keys among these cascades' components that the plan flags for
    export (missing on disk or below the current version)."""
    to_export = set(plan.to_export)
    keys = set()
    for c in cascades:
        for comp in c["components"]:
            if comp["key"] in to_export:
                keys.add(comp["key"])
    return keys


def report_plan(selection):
    total = sum(len(cs) for *_, cs in selection)
    print(f"\n● PLAN — {total} cascade(s) selected across "
          f"{len(selection)} game(s)\n")
    stale_total = 0
    for game, spec, plan, cs in selection:
        keys = stale_keys(plan, cs)
        stale_total += len(keys)
        print(f"  {game}  ({len(cs)} cascade(s), individual/{spec['folder']}/)")
        for c in sorted(cs, key=lambda c: c["name"]):
            print(f"    · {c['name']}")
        if keys:
            files = sorted(f for k in keys for f in plan.unique[k]["files"])
            print(f"    stale/missing components ({len(files)}): "
                  f"{', '.join(files)}")
        else:
            print("    components: all current")
        print()
    return stale_total


# --------------------------------------------------------------- export step
def run_exports(selection, auto):
    """Export stale/missing components for the selection. ALWAYS confirms the
    API spend (even under --auto). Returns True if it's safe to continue."""
    import export as E                       # lazy: pulls in onshape/requests

    PER = 3                                  # translate + poll + download estimate
    jobs = []                                # (game, spec, plan, batches, ops)
    ops_total = sets_total = 0
    for game, spec, plan, cs in selection:
        keys = stale_keys(plan, cs)
        if not keys:
            continue
        batches, _ = E.batch(cs, keys)
        ops = 0
        for _, bkeys in batches:
            asm = any(plan.unique[k]["type"] in OC.ASSEMBLY_SOURCED
                      for k in bkeys)
            studio = [k for k in bkeys
                      if plan.unique[k]["type"] in OC.STUDIO_SOURCED]
            ops += (1 if asm else 0) + len(studio)
        jobs.append((game, spec, plan, batches, ops))
        sets_total += len(batches)
        ops_total += ops

    if not jobs:
        print("● EXPORT — every selected component is already current; "
              "skipping Onshape.\n")
        return True

    est = sets_total + ops_total * PER
    ytd = E._ytd()
    print(f"● EXPORT — {sets_total} parameter set(s), {ops_total} translate "
          f"op(s) ≈ {est} API calls")
    for game, *_ , ops in jobs:
        print(f"    {game}: {ops} translate op(s)")
    print(f"    Year-to-date {ytd}/2500.\n")

    if not confirm(f"Spend ~{est} Onshape API calls?", auto,
                   default=False, always_ask=True):
        return confirm("Skip export and assemble with the components already "
                       "on disk?", auto, default=True)

    for game, spec, plan, batches, _ in jobs:
        E.run_export(game, spec, plan, batches, 0)
    return True


# ------------------------------------------------------------- assemble step
def object_specs(template_path):
    """[(object name, source_file)] for each top-level object in the template,
    in document order. `source_file` is the imported component mesh recorded on
    the object's first part (or "" if none) — the reliable role signal when the
    object name is uninformative (Dominion token holders are often left named
    'Part 1', or the half one named 'TokenHolder' like the full one)."""
    cfg = zipfile.ZipFile(template_path).read(
        "Metadata/model_settings.config").decode()
    out = []
    for om in re.finditer(r'<object id="\d+">(.*?)</object>', cfg, re.S):
        head = om.group(1).split("<part", 1)[0]
        nm = re.search(r'key="name" value="([^"]*)"', head)
        sf = re.search(r'key="source_file" value="([^"]*)"', om.group(1))
        out.append((nm.group(1) if nm else "", sf.group(1) if sf else ""))
    return out


def role_key(name):
    """A (role, discriminator) key that pairs a template object name with the
    component that should refill it. Templates suffix names by cascade/size
    (`Lid 360S`, `Topper Cities S-Un`) and Dominion calls its token holders
    `TokenHolder Full`/`Half`; the same function on a component's canonical
    object name yields the matching key. The stale size/sleeving suffix on
    toppers is ignored — only the expansion token discriminates."""
    if "TokenHolder" in name and "Half" in name:
        return ("HalfTokenHolder", None)
    if name.startswith("HalfTokenHolder"):
        return ("HalfTokenHolder", None)
    if name.startswith("TokenHolder"):                # incl. "TokenHolder Full"
        return ("TokenHolder", None)
    if name == "Topper" or name.startswith("Topper "):
        toks = name.split()
        return ("Topper", toks[1] if len(toks) > 1 else "Blank")   # bare = Blank
    for r in ("FirstHolder", "Box", "Lid", "Holder", "Pusher", "Label"):
        if name.startswith(r):
            return (r, None)
    return ("Other", name)


def object_role(name, src):
    """Role key for one template object. Token holders are identified by their
    source mesh first — their object names are unreliable (`Part 1`, or the half
    one named `TokenHolder`); everything else keys off the object name."""
    base = src.rsplit("/", 1)[-1]
    if "HalfTokenHolder" in base:
        return ("HalfTokenHolder", None)
    if "HalfTokenHolder" not in name and "TokenHolder" in base:
        return ("TokenHolder", None)
    return role_key(name)


def build_swap(template_path, components):
    """Pair each distinct template object NAME with a component file by role,
    using the object's name as the --part target. Returns
    (swap, unmatched, unused, conflicts): swap = {object name -> file};
    unmatched = template objects with no component (left as-is, non-fatal);
    unused = components with no slot (fatal — can't refresh them); conflicts =
    one object name carrying two different roles, so --part can't target them
    apart (needs a template rename). A clean refresh has all three empty."""
    comp_by_key = {}
    for c in components:
        comp_by_key.setdefault(role_key(c["object"]), c)
    name_roles = {}                       # object name -> set of role keys seen
    for name, src in object_specs(template_path):
        name_roles.setdefault(name, set()).add(object_role(name, src))
    swap, unmatched, conflicts, used = {}, [], [], set()
    for name, roles in name_roles.items():
        if len(roles) > 1:
            conflicts.append(name)
            continue
        (role,) = tuple(roles)
        c = comp_by_key.get(role)
        if c:
            swap[name] = c["file"]
            used.add(role)
        else:
            unmatched.append(name)
    unused = [c["object"] for k, c in comp_by_key.items() if k not in used]
    return swap, unmatched, unused, conflicts


def find_project(folder_dir, game, casc):
    """This cascade's project file, or None.

    The canonical name wins when it exists. Otherwise match on the MODEL CODE
    the filename carries, with '.' folded to '-' as project names write it.

    Not every game wants the canonical scheme. FCM's projects are named
    "FCM Occ 2S (180 Card L3-18-6-20-Sl).3mf" — the 2nd box for Occupations,
    sleeved — which is how Allan thinks about those boxes and which the
    canonical form can't express, so that naming is deliberate and kept. The
    model code is unique per cascade, so matching on it supports any naming
    that includes it, without a per-game rule to maintain."""
    canon = C.cascade_filename(game, casc["ctx"]["short_name"],
                               casc["sleeved"], casc["model"])
    if (folder_dir / canon).exists():
        return folder_dir / canon, canon
    tag = casc["model"].replace(".", "-")
    hits = sorted(p for p in folder_dir.glob("*.3mf") if tag in p.name)
    if len(hits) == 1:
        return hits[0], hits[0].name
    if hits:
        return None, (f"{canon!r} absent and {len(hits)} projects carry model "
                      f"{tag} ({', '.join(p.name for p in hits)})")
    return None, f"{canon!r} absent and no project carries model {tag}"


def assemble_one(game, spec, casc, dry):
    """Refresh one cascade in place with make_cascade --keep-layout. Returns
    (status, detail) where status is 'ok' | 'skip' | 'fail'."""
    folder = spec["folder"]
    template, canon = find_project(ROOT / "cascades" / folder, game, casc)
    if template is None:
        return "skip", f"no cascade project to swap into — {canon}"

    swap, unmatched, unused, conflicts = build_swap(template, casc["components"])
    if conflicts:
        return "skip", (f"template object(s) {conflicts} carry two roles — "
                        "rename one in the template so --part can target them")
    if unused:
        return "skip", f"components with no template slot: {unused}"

    missing = [f for f in swap.values()
               if not (ROOT / "individual" / folder / f).exists()]
    if missing:
        return "skip", f"components not on disk: {', '.join(sorted(missing))}"

    cmd = [sys.executable, str(HERE / "make_cascade.py"), str(template),
           "-o", str(template), "--keep-layout"]
    for obj, file in swap.items():
        cmd += ["--part", f"{obj}={ROOT / 'individual' / folder / file}"]
    note = f"  (left untouched: {unmatched})" if unmatched else ""
    if dry:
        return "ok", "would run: " + " ".join(
            f'"{a}"' if " " in a else a for a in cmd) + note
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        tail = (res.stderr or res.stdout).strip().splitlines()[-1:] or [""]
        return "fail", tail[0]
    return "ok", canon + note


def bed_for(casc):
    """make_cascade --bed for a cascade, from parts.csv's `3D printer` column:
    Standard→p1, Large→h2c, Mixed→p1 unsleeved / h2c sleeved (the sleeved box is
    deeper and needs the big bed), blank/unknown→auto (let make_cascade decide)."""
    kind = (casc["row"].get("3D printer") or "").strip().lower()
    if kind == "standard":
        return "p1"
    if kind == "large":
        return "h2c"
    if kind == "mixed":
        return "p1" if casc["sleeved"] == "Un" else "h2c"
    return "auto"


def th_canonical(role, merged):
    """The conventional object name for a (Half)TokenHolder: Mat boxes split the
    front pocket into Full + Half; a plain box has one bare `TokenHolder`."""
    if role == "HalfTokenHolder":
        return "TokenHolder Half"
    if role == "TokenHolder":
        return "TokenHolder Full" if merged else "TokenHolder"
    return None


def rebuild_one(game, spec, casc, dry):
    """Rebuild one cascade from its components with make_cascade --auto-plates,
    using its existing project as the layout donor. Unlike keep-layout this
    regenerates the plate layout — needed to first-build a box whose only project
    is stale/mislabeled. Swaps every mesh by role, normalises the token-holder
    object name (donors often leave it 'Part 1'), and picks the bed from
    parts.csv. Returns (status, detail): 'ok' | 'skip' | 'fail'."""
    folder = spec["folder"]
    donor, canon = find_project(ROOT / "cascades" / folder, game, casc)
    if donor is None:
        return "skip", f"no donor project to rebuild from — {canon}"

    swap, unmatched, unused, conflicts = build_swap(donor, casc["components"])
    if conflicts:
        return "skip", (f"donor object(s) {conflicts} carry two roles — "
                        "rename one so --part can target them apart")
    if unused:                            # --auto-plates can't ADD a missing slot
        return "skip", f"components with no donor slot: {unused}"
    missing = [f for f in swap.values()
               if not (ROOT / "individual" / folder / f).exists()]
    if missing:
        return "skip", f"components not on disk: {', '.join(sorted(missing))}"

    merged = casc["ctx"]["merged"]
    renames = {}
    for name, src in object_specs(donor):
        want = th_canonical(object_role(name, src)[0], merged)
        if want and name != want:
            renames[name] = want

    bed = bed_for(casc)
    cmd = [sys.executable, str(HERE / "make_cascade.py"), str(donor),
           "-o", str(donor), "--auto-plates", "--bed", bed]
    for obj, file in swap.items():
        cmd += ["--part", f"{obj}={ROOT / 'individual' / folder / file}"]
    for old, new in renames.items():
        cmd += ["--rename", f"{old}={new}"]
    note = f"  [bed {bed}]" + (f" (left: {unmatched})" if unmatched else "")
    if dry:
        return "ok", "would run: " + " ".join(
            f'"{a}"' if " " in a else a for a in cmd) + note
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        tail = (res.stderr or res.stdout).strip().splitlines()[-1:] or [""]
        return "fail", tail[0]
    return "ok", canon + note


def run_assemble(selection, auto, dry, rebuild=False):
    n = sum(len(cs) for *_, cs in selection)
    mode = "auto-plates rebuild" if rebuild else "keep-layout refresh"
    one = rebuild_one if rebuild else assemble_one
    print(f"● ASSEMBLE — {mode} of up to {n} cascade(s)"
          f"{' (dry run)' if dry else ''}\n")
    if not confirm("Assemble these cascade(s)?", auto, default=True):
        print("assemble skipped.")
        return
    tally = {"ok": 0, "skip": 0, "fail": 0}
    for game, spec, _, cs in selection:
        print(f"  {game}:")
        for c in sorted(cs, key=lambda c: c["name"]):
            status, detail = one(game, spec, c, dry)
            tally[status] += 1
            mark = {"ok": "✓", "skip": "·", "fail": "⚠"}[status]
            print(f"    {mark} {c['name']}  {detail}")
        print()
    print(f"assembled {tally['ok']}, skipped {tally['skip']}, "
          f"failed {tally['fail']}.")


# ----------------------------------------------------- standardize-names mode
def find_legacy(folder_dir, casc):
    """Locate a pre-standard cascade project for this cascade so it can be
    git-renamed. Matches the old Dominion 'CC <num><S|U> ...' form by short-name
    number + sleeving; returns a Path or None."""
    num = re.match(r"\d+", casc["ctx"]["short_name"])
    if not num:
        return None
    letter = "S" if casc["sleeved"] == "Sl" else "U"
    pat = re.compile(rf"^CC {num.group(0)}{letter}\b")
    hits = [p for p in folder_dir.glob("*.3mf") if pat.match(p.name)]
    return hits[0] if len(hits) == 1 else None


def standardize_names(selection, auto, dry):
    print("\n● STANDARDIZE NAMES — rename legacy cascade projects to "
          "'<Game> <Short> <Sleeved|Unsleeved> (<model>).3mf'\n")
    renames = []                             # (old Path, new Path)
    for game, spec, _, cs in selection:
        d = ROOT / "cascades" / spec["folder"]
        for c in cs:
            canon = C.cascade_filename(game, c["ctx"]["short_name"],
                                       c["sleeved"], c["model"])
            if (d / canon).exists():
                continue                     # already standard
            legacy = find_legacy(d, c)
            if legacy:
                renames.append((legacy, d / canon))

    if not renames:
        print("  nothing to rename — all selected projects already standard.\n")
        return
    for old, new in renames:
        print(f"    {old.name}\n      → {new.name}")
    print()
    if dry or not confirm(f"git mv {len(renames)} file(s)?", auto, default=True):
        print("standardize skipped (dry run or declined).")
        return
    for old, new in renames:
        subprocess.run(["git", "-C", str(ROOT), "mv", str(old), str(new)],
                       check=True)
    print(f"renamed {len(renames)} file(s).")


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--game", help="restrict to one game (name or folder code)")
    ap.add_argument("--size", help="comma-separated size classes: S,M,L")
    ap.add_argument("--sleeving", choices=["un", "sl"],
                    help="restrict to unsleeved or sleeved cascades")
    ap.add_argument("--name", help="substring match on Short name (e.g. '400')")
    ap.add_argument("--labels", action="store_true",
                    help="include Onshape-generated labels (Compile)")
    ap.add_argument("--changed", default="",
                    help="comma-separated component types to force re-export "
                         "even if provenance says they are current (e.g. 'Lid'); "
                         "scoped to the cascades the filters select")
    ap.add_argument("--auto", action="store_true",
                    help="skip the offline PLAN/ASSEMBLE prompts (the Onshape "
                         "EXPORT step still confirms before spending calls)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show the plan and the make_cascade commands without "
                         "exporting, assembling or renaming anything")
    ap.add_argument("--standardize-names", action="store_true",
                    help="one-off: git-rename legacy cascade projects to the "
                         "standard name, then exit")
    ap.add_argument("--rebuild", action="store_true",
                    help="ASSEMBLE via make_cascade --auto-plates (regenerate the "
                         "plate layout from the box's own project as donor, bed "
                         "from parts.csv) instead of the default keep-layout swap; "
                         "use to first-build a box whose only project is stale")
    args = ap.parse_args()

    sizes = {s.strip().upper() for s in (args.size or "").split(",") if s.strip()}
    sleeving = {"un": "Un", "sl": "Sl"}.get(args.sleeving)
    games = resolve_games(args.game)
    changed = {c.strip() for c in args.changed.split(",") if c.strip()}
    unknown = changed - set(OC.VERSIONS)
    if unknown:
        sys.exit(f"unknown component type(s) for --changed: "
                 f"{', '.join(sorted(unknown))}; known: {list(OC.VERSIONS)}")
    selection = select(games, sizes, sleeving, args.name, args.labels, changed)
    if not selection:
        sys.exit("no cascades match the given filters.")

    if args.standardize_names:
        standardize_names(selection, args.auto, args.dry_run)
        return

    stale = report_plan(selection)
    if args.dry_run:
        print("(dry run) — showing export need and assemble commands only.\n")
    elif not confirm("Proceed with this selection?", args.auto, default=True):
        print("aborted.")
        return

    if not args.dry_run:
        if not run_exports(selection, args.auto):
            print("aborted before assemble.")
            return
    elif stale:
        print(f"● EXPORT — {stale} component(s) would be re-exported "
              "(run without --dry-run to spend the calls).\n")

    run_assemble(selection, args.auto, args.dry_run, args.rebuild)


if __name__ == "__main__":
    main()
