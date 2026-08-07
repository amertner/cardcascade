#!/usr/bin/env python3
"""Stage 2 exporter/planner: decide WHEN to set parameters and WHAT to request,
minimising Onshape API calls, and (with --execute) actually export.

Each cascade is one full Primary parameter set (one POST). Setting parameters is
the expensive gate, so we set it once per cascade that still contributes a
not-yet-exported component, and request only those new components under it;
cascades whose components are all already exported are skipped.

Default is a dry run (0 API calls) that prints the plan as an outline. --execute
performs it: per batch → set Primary → export each component's whole part studio
as one combined 3MF → strip imported parts → validate → write file + provenance.

Usage:
    export.py <Game> [--all] [--changed Box,Holder] [--labels]     # plan only
    export.py <Game> --execute [--sleeving un|sl] [--limit N]      # do it
      --all       ignore provenance (plan a full rebuild)
      --changed   force re-export of these component types
      --sleeving  restrict to unsleeved (un) or sleeved (sl) cascades
      --limit N   export at most N components (spend incrementally)
      --adopt     record present on-disk files as current, then exit
"""
import argparse
import datetime
import sys

import assembly_split as ASM
import components as C
import make_cascade as MC
import mesh
import onshape as O
import onshape_config as OC
import plan_exports as P
import provenance as PROV
import set_variables as SV

# One combined 3MF (grouping=true) with all parts as named objects, Z-up, mm.
MESH_BODY = {"formatName": "3MF", "storeInDocument": False, "notifyUser": False,
             "resolution": "medium", "units": "millimeter", "grouping": True,
             "yAxisIsUp": False, "flattenAssemblies": False,
             "excludeHiddenEntities": True, "includeExportIds": False}


def comp_config(comp):
    """Human-readable config for provenance (toppers select an expansion)."""
    return f"Expansion={comp['key'][1]}" if comp["type"] == "Topper" else ""


def api_config(comp):
    """Onshape configuration string for the export. A single list input encodes
    as 'parameterId=value', so we build it locally (no configurationencodings)."""
    if comp["type"] == "Topper":
        return f"{OC.TOPPER_CONFIG_PARAM}={comp['key'][1]}"
    return ""


def param_summary(ctx):
    s = [f"GameName={ctx['folder']}", f"HorizontalSlots={ctx['horizontal']}",
         f"RisingSliders={ctx['risers']}",
         f"CardsPerSlidingSlot={ctx['cards_per_slot']}",
         f"FrontPocket={ctx['front_capacity']}",
         f"isSleeved={1 if ctx['sleeved'] == 'Sl' else 0}",
         f"MatPocket={1 if ctx['merged'] else 0}"]
    if ctx["first_riser"]:
        s.append(f"FirstSlidingSlot={ctx['first_riser']}")
    return "  ".join(s)


def batch(cascades, to_export_keys):
    """Greedy: each cascade contributes the components still needing export that
    an earlier parameter set hasn't already claimed. Returns (batches, skipped)."""
    assigned, batches, skipped = set(), [], []
    for casc in cascades:
        keys, seen = [], set()
        for comp in casc["components"]:
            k = comp["key"]
            if k in seen:
                continue
            seen.add(k)
            if k in assigned or k not in to_export_keys:
                continue
            keys.append(k)
        if keys:
            batches.append((casc, keys))
            assigned |= set(keys)
        else:
            skipped.append(casc)
    return batches, skipped


# ----------------------------------------------------------------- execution
def set_primary(auth, row, sleeved, game_name):
    O.api(auth, "POST",
          f"/api/variables/d/{OC.DID}/w/{OC.WID}/e/{OC.PRIMARY}/variables",
          "set-primary", json=SV.build_primary(row, sleeved, game_name))


def _record(comp, game, element, mv, when):
    PROV.record(game, PROV.make_row(
        comp["file"], comp["type"], comp["key"], element, comp_config(comp),
        OC.VERSIONS.get(comp["type"], ""), mv, when))


def _write(data, comp, folder, game, element, mv, when):
    """Write export bytes to the component's file, validate, record provenance."""
    out = P.ROOT / "individual" / folder / comp["file"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    bodies = MC.load_export(str(out))            # validate it parses cleanly
    _record(comp, game, element, mv, when)
    return len(bodies)


def export_studio(auth, comp, folder, game, when):
    """One part-studio component (Lid, Topper, Label): translate -> strip imports
    -> file + provenance."""
    typ = comp["type"]
    body = dict(MESH_BODY)
    cfg = api_config(comp)
    if cfg:
        body["configuration"] = cfg
    data, mv = O.translate(
        auth, "partstudio", OC.DID,
        f"/api/partstudios/d/{OC.DID}/w/{OC.WID}/e/{OC.ELEMENTS[typ]}/translations",
        body, reason=typ.lower())
    clean, dropped = mesh.strip_objects(data, {t for t in OC.ELEMENTS if t != typ})
    n = _write(clean, comp, folder, game, OC.ELEMENTS[typ], mv, when)
    return n, dropped


def assembly_role(comp):
    """Which split role a cascade component maps to inside the assembly export."""
    if comp["type"] == "Holder" and comp.get("instance") == "first":
        return "Holder_first"
    return comp["type"]


def export_assembly(auth, ctx):
    """One assembly translation -> {role: clean 3mf bytes} (split locally),
    plus the shared documentMicroversion."""
    data, mv = O.translate(
        auth, "assembly", OC.DID,
        f"/api/assemblies/d/{OC.DID}/w/{OC.WID}/e/{OC.ASSEMBLY}/translations",
        dict(MESH_BODY), reason="assembly")
    card_mm = 0.64 if ctx["sleeved"] == "Sl" else 0.34
    parts = ASM.split(mesh.unwrap(data), cards_first=ctx.get("first_riser"),
                      cards_slot=ctx["cards_per_slot"], card_mm=card_mm)
    return parts, mv


def run_export(game, spec, plan, batches, limit):
    O.begin()
    auth = O.creds()
    when = datetime.datetime.now().isoformat(timespec="seconds")
    folder = spec["folder"]
    done = 0
    for casc, keys in batches:
        if limit and done >= limit:
            break
        bykey = {}
        for c in casc["components"]:
            bykey.setdefault(c["key"], c)
        needed = [bykey[k] for k in keys if k in bykey]
        asm = [c for c in needed if c["type"] in OC.ASSEMBLY_SOURCED]
        studio = [c for c in needed if c["type"] in OC.STUDIO_SOURCED]
        set_primary(auth, casc["row"], casc["sleeved"] == "Sl",
                    spec.get("onshape_name", spec["folder"]))
        print(f"● SET PARAMETERS  [{casc['name']}]")
        # ONE assembly export supplies every monochrome component of this cascade
        if asm and not (limit and done >= limit):
            parts, mv = export_assembly(auth, casc["ctx"])
            for comp in asm:
                if limit and done >= limit:
                    break
                role = assembly_role(comp)
                data = parts.get(role)
                if data is None:
                    print(f"    ⚠ {comp['file']} — role {role!r} absent from assembly")
                    continue
                n = _write(data, comp, folder, game, OC.ASSEMBLY, mv, when)
                print(f"    ✓ {comp['file']}  ({n} body, assembly)")
                done += 1
        # Lid / toppers / labels stay on the per-part-studio path
        for comp in studio:
            if limit and done >= limit:
                break
            if comp["type"] not in OC.ELEMENTS:
                print(f"    ⚠ skip {comp['file']} — no element id"); continue
            n, dropped = export_studio(auth, comp, folder, game, when)
            extra = f", stripped {dropped}" if dropped else ""
            print(f"    ✓ {comp['file']}  ({n} bodies, studio{extra})")
            done += 1
    print(f"\nexported {done} component(s).\n{O.budget_line()}")


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("game")
    ap.add_argument("--all", action="store_true",
                    help="ignore provenance (plan a full rebuild)")
    ap.add_argument("--changed", default="")
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--adopt", action="store_true",
                    help="record present on-disk files as current, then exit")
    ap.add_argument("--execute", action="store_true",
                    help="actually export (default is a 0-call dry run)")
    ap.add_argument("--sleeving", choices=["un", "sl"],
                    help="restrict to unsleeved or sleeved cascades")
    ap.add_argument("--name", help="restrict to one cascade (Short name, "
                                   "e.g. '360 Card')")
    ap.add_argument("--limit", type=int, default=0,
                    help="export at most N components")
    args = ap.parse_args()

    game, spec = C.game_by_name(args.game)
    if not spec:
        sys.exit(f"unknown game {args.game!r}; known: {list(C.GAMES)}")
    changed = {c.strip() for c in args.changed.split(",") if c.strip()}
    plan = P.compute_plan(game, spec, str(P.HERE / "parts.csv"),
                          args.labels, changed)
    prov = PROV.load(game)

    if args.adopt:
        when = datetime.datetime.now().isoformat(timespec="seconds")
        seen, n = set(), 0
        for casc in plan.cascades:
            for comp in casc["components"]:
                f = comp["file"]
                if f in seen:
                    continue
                seen.add(f)
                if f in plan.present and not PROV.is_current(
                        prov, f, OC.VERSIONS.get(comp["type"])):
                    prov[f] = PROV.make_row(
                        f, comp["type"], comp["key"],
                        OC.ELEMENTS.get(comp["type"], ""), comp_config(comp),
                        OC.VERSIONS.get(comp["type"], ""), "", when)
                    n += 1
        PROV.save(game, prov)
        print(f"Adopted {n} on-disk file(s) into provenance → "
              f"automation/state/{game}.csv")
        return

    to_export_keys = set(plan.unique) if args.all else set(plan.to_export)
    cascades = plan.cascades
    if args.sleeving:
        cascades = [c for c in cascades if c["sleeved"] == args.sleeving.capitalize()]
    if args.name:
        cascades = [c for c in cascades if c["ctx"]["short_name"] == args.name]
    batches, skipped = batch(cascades, to_export_keys)

    def classify(keys):
        """(assembly-sourced keys, studio-sourced keys) for one cascade."""
        asm = [k for k in keys if plan.unique[k]["type"] in OC.ASSEMBLY_SOURCED]
        studio = [k for k in keys if plan.unique[k]["type"] in OC.STUDIO_SOURCED]
        return asm, studio

    # translate operations per cascade: ONE assembly export covers all its
    # monochrome parts; each lid/topper/label is its own studio export.
    def translate_ops(keys):
        asm, studio = classify(keys)
        return (1 if asm else 0) + len(studio)

    PER = 3          # per translate op with adaptive polling: translate + 1 poll + download
    sets = len(batches)
    ops = sum(translate_ops(keys) for _, keys in batches)
    est = sets + ops * PER

    if args.execute:
        scope = f" [{args.sleeving}]" if args.sleeving else ""
        lim = f", limit {args.limit}" if args.limit else ""
        print(f"EXECUTE — {game}{scope}: {sets} parameter set(s), "
              f"{ops} translate op(s) ≈ {est} calls{lim}\n")
        run_export(game, spec, plan, batches, args.limit)
        return

    # ---- dry run ----
    cache = ("IGNORING cache (--all)" if args.all
             else f"{len(plan.all_files & plan.present)}/{len(plan.all_files)} "
                  "components already cached")
    scope = f", {args.sleeving} only" if args.sleeving else ""
    print(f"EXPORT PLAN — {game}   (dry run, 0 API calls; {cache}{scope})\n")
    for casc, keys in batches:
        asm, studio = classify(keys)
        ncalls = 1 + translate_ops(keys)
        print(f"● SET PARAMETERS  [{casc['name']}]   (~{1 + translate_ops(keys) * PER} calls)")
        print(f"      {param_summary(casc['ctx'])}")
        if asm:
            files = sorted(sorted(plan.unique[k]["files"])[0] for k in asm)
            nnew = sum(1 for f in files if f not in plan.present)
            st = "new" if nnew == len(files) else f"{nnew} new, {len(files) - nnew} stale"
            print(f"      ├─ 1 ASSEMBLY export → {len(asm)} monochrome part(s) "
                  f"[{st}]: {', '.join(files)}")
        toppers = [k for k in studio if plan.unique[k]["type"] == "Topper"]
        other = [k for k in studio if plan.unique[k]["type"] != "Topper"]
        for k in other:
            u = plan.unique[k]
            f = sorted(u["files"])[0]
            state = "new" if f not in plan.present else "stale"
            tag = "" if u["type"] in OC.ELEMENTS else "  ⚠ no element id"
            print(f"      ├─ studio export {f}   [{u['type']} · {state}]{tag}")
        if toppers:
            exps = [k[1] for k in toppers]
            files = [sorted(plan.unique[k]["files"])[0] for k in toppers]
            nnew = sum(1 for f in files if f not in plan.present)
            st = ("new" if nnew == len(files)
                  else f"{nnew} new, {len(files) - nnew} stale")
            print(f"      └─ {len(exps)} studio topper export(s) [{st}]: "
                  f"{', '.join(exps)}")
        print()

    if skipped:
        print(f"Skipped {len(skipped)} cascade(s) — every component already "
              f"exported, so NO parameter-set call:")
        for casc in skipped:
            print(f"  · {casc['name']}")
        print()

    unknown = sorted({plan.unique[k]["type"] for _, keys in batches for k in keys
                      if plan.unique[k]["type"] in OC.STUDIO_SOURCED
                      and plan.unique[k]["type"] not in OC.ELEMENTS})
    print(f"Parameter sets: {sets}   Translate ops: {ops}   "
          f"(1 assembly export replaces all of a cascade's monochrome parts)")
    print(f"Estimated API calls: {sets} set + {ops}×~{PER} = ~{est}")
    if unknown:
        print(f"  ⚠ no element id yet for {unknown}")
    print(f"\nYear-to-date {_ytd()}/2500.  Re-run with --execute to perform it.")


def _ytd():
    try:
        return O.read_cumulative()
    except Exception:
        return "?"


if __name__ == "__main__":
    main()
