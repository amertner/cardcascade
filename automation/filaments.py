#!/usr/bin/env python3
"""Filament-slot surgery on a Bambu project (project_settings.config).

A project's settings carry ~150 arrays that scale with the filament count,
mixed in with arrays that merely LOOK filament-sized, and no rule of shape
separates them:

  - filament_nozzle_map / filament_volume_map are 9 entries whatever the
    filament count, so at 9 filaments "len % n == 0" claims them;
  - nozzle_diameter and extruder_printable_area are per-NOZZLE, so on the
    dual-nozzle H2C they are 2 long — indistinguishable, at 2 filaments,
    from a real per-filament array. Permuting one corrupts the printer setup.

So membership decides: PER_FILAMENT below is the exact set of keys whose
length differed between the 9-filament and 2-filament halves of one project
(Compile 126, which differed in nothing else), and anything unlisted is left
alone. A listed key whose shape doesn't agree is reported, not reshaped.

The one primitive is `remap(ps, order)`: rebuild every per-filament array by
picking source slots in a new order. Dropping slots, reordering them, or both
are all just an `order`:

    trim 9 -> 2      order = [0, 1]
    swap the two     order = [1, 0]
    white-first      order = [white_slot, dark_slot]

Objects name their filament by 1-based slot in model_settings.config, so any
order that moves a slot must be paired with `remap_extruders`, or the print
comes out in the wrong colours.

Separately, `--makerworld` fixes what makes MakerWorld reject an upload with
"Uploading a 3mf file that contains custom printer types or filament types is
not allowed". See MAKERWORLD_NOTES below.

CLI:
    filaments.py --white-first <project.3mf>...   # two slots: white, then dark
    filaments.py --drop-unused <project.3mf>...   # shed trailing unused slots
    filaments.py --makerworld <project.3mf>...    # make presets stock again
    filaments.py --check <project.3mf>...         # report only, write nothing
"""
import argparse
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

PS = "Metadata/project_settings.config"
MS = "Metadata/model_settings.config"

WHITE = "#FFFFFF"

# Per-filament arrays, identified positively rather than by shape: this list
# is the exact set of keys whose length differed between the 9-filament and
# 2-filament halves of one project (Compile 126, which differed in nothing
# else). Shape alone cannot decide the question — at 2 filaments a per-NOZZLE
# array (nozzle_diameter, extruder_printable_area on the dual-nozzle H2C) is
# also 2 long, and permuting one of those would corrupt the printer setup.
PER_FILAMENT = {
    "activate_air_filtration", "additional_cooling_fan_speed",
    "additional_fan_full_speed_layer", "chamber_temperatures",
    "circle_compensation_speed", "close_additional_fan_first_x_layers",
    "close_fan_the_first_x_layers", "complete_print_exhaust_fan_speed",
    "cool_plate_temp", "cool_plate_temp_initial_layer",
    "cooling_perimeter_transition_distance", "cooling_slowdown_logic",
    "counter_coef_1", "counter_coef_2", "counter_coef_3", "counter_limit_max",
    "counter_limit_min", "default_filament_colour", "diameter_limit",
    "during_print_exhaust_fan_speed", "enable_overhang_bridge_fan",
    "enable_pressure_advance", "eng_plate_temp",
    "eng_plate_temp_initial_layer", "fan_cooling_layer_time", "fan_max_speed",
    "fan_min_speed", "filament_adaptive_volumetric_speed",
    "filament_adhesiveness_category", "filament_bridge_speed",
    "filament_change_length", "filament_change_length_nc", "filament_colour",
    "filament_colour_type", "filament_cooling_before_tower", "filament_cost",
    "filament_density", "filament_deretraction_speed",
    "filament_dev_ams_drying_ams_limitations",
    "filament_dev_ams_drying_heat_distortion_temperature",
    "filament_dev_ams_drying_temperature", "filament_dev_ams_drying_time",
    "filament_dev_chamber_drying_bed_temperature",
    "filament_dev_chamber_drying_time",
    "filament_dev_drying_cooling_temperature",
    "filament_dev_drying_softening_temperature", "filament_diameter",
    "filament_enable_overhang_speed", "filament_end_gcode",
    "filament_extruder_compatibility", "filament_extruder_variant",
    "filament_flow_ratio", "filament_flush_temp", "filament_flush_temp_fast",
    "filament_flush_volumetric_speed", "filament_ids", "filament_is_mixed",
    "filament_is_support", "filament_long_retractions_when_cut",
    "filament_map", "filament_max_volumetric_speed",
    "filament_metal_stickiness", "filament_minimal_purge_on_wipe_tower",
    "filament_mixed_components", "filament_mixed_gradient",
    "filament_mixed_gradient_curve", "filament_mixed_gradient_per_part",
    "filament_mixed_gradient_range", "filament_mixed_sublayer_ratios",
    "filament_multi_colour", "filament_overhang_1_4_speed",
    "filament_overhang_2_4_speed", "filament_overhang_3_4_speed",
    "filament_overhang_4_4_speed", "filament_overhang_totally_speed",
    "filament_pre_cooling_temperature", "filament_pre_cooling_temperature_nc",
    "filament_preheat_temperature_delta", "filament_prime_volume",
    "filament_prime_volume_nc", "filament_printable",
    "filament_ramming_travel_time", "filament_ramming_travel_time_nc",
    "filament_ramming_volumetric_speed",
    "filament_ramming_volumetric_speed_nc", "filament_retract_before_wipe",
    "filament_retract_length_nc", "filament_retract_restart_extra",
    "filament_retract_when_changing_layer",
    "filament_retraction_distances_when_cut", "filament_retraction_length",
    "filament_retraction_minimum_travel", "filament_retraction_speed",
    "filament_scarf_gap", "filament_scarf_height", "filament_scarf_length",
    "filament_scarf_seam_type", "filament_self_index", "filament_settings_id",
    "filament_shrink", "filament_soluble", "filament_start_gcode",
    "filament_tower_interface_pre_extrusion_dist",
    "filament_tower_interface_pre_extrusion_length",
    "filament_tower_interface_print_temp",
    "filament_tower_interface_purge_volume", "filament_tower_ironing_area",
    "filament_type", "filament_velocity_adaptation_factor", "filament_vendor",
    "filament_wipe", "filament_wipe_distance", "filament_z_hop",
    "filament_z_hop_types", "first_x_layer_fan_speed",
    "first_x_layer_part_fan_speed", "flush_volumes_vector",
    "full_fan_speed_layer", "hole_coef_1", "hole_coef_2", "hole_coef_3",
    "hole_limit_max", "hole_limit_min", "hot_plate_temp",
    "hot_plate_temp_initial_layer", "impact_strength_z", "ironing_fan_speed",
    "long_retractions_when_ec", "no_slow_down_for_cooling_on_outwalls",
    "nozzle_temperature", "nozzle_temperature_initial_layer",
    "nozzle_temperature_range_high", "nozzle_temperature_range_low",
    "overhang_fan_speed", "overhang_fan_threshold",
    "overhang_threshold_participating_cooling",
    "override_process_overhang_speed", "pre_start_fan_time",
    "pressure_advance", "reduce_fan_stop_start_freq", "required_nozzle_HRC",
    "retraction_distances_when_ec", "slow_down_for_layer_cooling",
    "slow_down_layer_time", "slow_down_min_speed", "supertack_plate_temp",
    "supertack_plate_temp_initial_layer", "temperature_vitrification",
    "textured_plate_temp", "textured_plate_temp_initial_layer",
    "volumetric_speed_coefficients",
}

# printer + process + one entry per filament.
PER_PRESET = {"different_settings_to_system", "inherits_group"}
# nozzles x n x n on a multi-nozzle printer (H2C), n x n on a single (P1S).
MATRIX = "flush_volumes_matrix"
# Values encode the slot number itself, so they are renumbered positionally
# after a permutation rather than carried along with their slot.
POSITIONAL = {"filament_self_index"}

MAKERWORLD_NOTES = """\
MakerWorld accepts only STOCK Bambu printer and filament presets. Three things
in this repo's projects trip that check:

1. printer_settings_id must be "<model> <variant> nozzle" — the form every P1
   project here uses, and the form these projects' own inherits_group names.
   The H2C profile was written as "Bambu Lab H2C 0.4", missing " nozzle", so
   every project built on the H2C bed inherited a printer id MakerWorld can't
   match to a stock preset.
2. filament_settings_id must not carry a "(<project>.3mf)" suffix. Bambu Studio
   appends that when a preset is edited inside a project, turning it into a
   project-LOCAL custom preset. Saving in Studio to work around (1) is what
   creates these — it gets the file past upload and then fails verification.
3. filament_nozzle_map / filament_volume_map are sized to the filament count by
   current Studio versions; older files carry 9 (or other stale lengths).

Clearing a filament's entry in different_settings_to_system + inherits_group is
what stops (2) coming back: those mark the filament as deviating from its
system preset, which is the seed Studio promotes into a named local preset. In
every project here the deviation is phantom — the flagged setting
(support_air_filtration) already holds the same value as the stock profile."""


def slots(ps):
    return len(ps.get("filament_colour", []))


def stock_printer_id(ps):
    """The stock preset name for this project's printer, e.g.
    "Bambu Lab H2C 0.4 nozzle"."""
    model, variant = ps.get("printer_model", ""), ps.get("printer_variant", "")
    return f"{model} {variant} nozzle" if model and variant else ""


def makerworld_problems(ps):
    """[(key, found, wanted, blocking)] for a MakerWorld upload.

    `blocking` marks what the evidence says actually causes a rejection. The
    stale nozzle/volume maps are reported but NOT blocking: Dominion 560 and
    650 carry maps of 3 and 7 entries for 2 filaments and upload fine, so the
    length mismatch is cosmetic drift from an older Studio, not a gate. Only
    the preset IDENTITY fields gate the upload."""
    out, n = [], slots(ps)
    stock = stock_printer_id(ps)
    if stock and ps.get("printer_settings_id") != stock:
        out.append(("printer_settings_id", ps.get("printer_settings_id"),
                    stock, True))
    for i, fid in enumerate(ps.get("filament_settings_id", [])):
        if "(" in fid:
            out.append((f"filament_settings_id[{i}]", fid,
                        fid.split("(")[0], True))
    for k in ("different_settings_to_system", "inherits_group"):
        v = ps.get(k, [])
        flagged = [x for x in v[2:] if x]          # [printer, process, filaments...]
        if flagged:
            out.append((f"{k} (filaments)", flagged,
                        "empty — no local deviation", True))
    for k in ("filament_nozzle_map", "filament_volume_map"):
        v = ps.get(k)
        if isinstance(v, list) and v and len(v) != n:
            out.append((k, f"{len(v)} entries", f"{n} (one per filament)", False))
    return out


def makerworld_fix(ps):
    """Settings with every BLOCKING makerworld_problems() issue corrected.

    Deliberately leaves the non-blocking maps alone: rewriting 16 published
    projects to chase something demonstrably not a gate is churn, not a fix."""
    out = dict(ps)
    stock = stock_printer_id(ps)
    if stock:
        out["printer_settings_id"] = stock
    out["filament_settings_id"] = [f.split("(")[0]
                                   for f in ps.get("filament_settings_id", [])]
    for k in ("different_settings_to_system", "inherits_group"):
        v = list(ps.get(k, []))
        if len(v) > 2:
            out[k] = v[:2] + [""] * (len(v) - 2)
    return out


def per_filament_keys(ps):
    """The keys `remap` will rewrite, plus any it cannot account for.

    Membership decides, not shape — but shape still has to agree, so a listed
    key whose length isn't a whole number of slots is reported rather than
    reshaped. `unknown` is what makes this safe against a future Bambu adding
    a per-filament key: remap() refuses instead of silently leaving it at the
    old slot count."""
    n = slots(ps)
    keys, unknown = [], []
    for k, v in ps.items():
        if not isinstance(v, list) or not v:
            continue
        if k == MATRIX:
            # n x n per nozzle: 4 on a P1S, 8 on the dual-nozzle H2C
            keys.append(k) if len(v) % (n * n) == 0 else unknown.append(k)
        elif k in PER_PRESET:
            keys.append(k) if len(v) == n + 2 else unknown.append(k)
        elif k in PER_FILAMENT:
            keys.append(k) if len(v) % n == 0 else unknown.append(k)
    return keys, unknown


def remap(ps, order):
    """Rebuild every per-filament array picking source slots in `order`.

    `order` holds 0-based source slot indices; the result has len(order) slots.
    Returns (new settings, list of (key, old length, new length))."""
    n = slots(ps)
    if not order or any(not 0 <= i < n for i in order):
        raise SystemExit(f"order {[i + 1 for i in order]} is out of range for a "
                         f"{n}-slot project (already normalised?)")
    keys, unknown = per_filament_keys(ps)
    if unknown:
        raise SystemExit(f"unclassified filament-sized keys {unknown} — refusing "
                         f"to guess; add them to filaments.py")
    out, notes = dict(ps), []
    for k in keys:
        v = ps[k]
        if k == MATRIX:
            # one n x n block per nozzle; permute each block's rows and columns
            new = []
            for base in range(0, len(v), n * n):
                new += [v[base + r * n + c] for r in order for c in order]
        elif k in PER_PRESET:
            new = v[:2] + [v[2 + i] for i in order]
        else:
            stride = len(v) // n
            if k in POSITIONAL:          # values are slot numbers: renumber
                new = [str(i + 1) for i in range(len(order))
                       for _ in range(stride)]
            else:
                new = [x for i in order for x in v[i * stride:(i + 1) * stride]]
        if new != v:
            notes.append((k, len(v), len(new)))
        out[k] = new
    return out, notes


def used_extruders(model_settings):
    return sorted({int(e) for e in
                   re.findall(r'key="extruder" value="(\d+)"', model_settings)})


def remap_extruders(model_settings, mapping):
    """Rewrite 1-based extruder references per {old: new}."""
    n = [0]

    def sub(m):
        old = int(m.group(2))
        n[0] += old in mapping
        return f"{m.group(1)}{mapping.get(old, old)}{m.group(3)}"

    return re.sub(r'(key="extruder" value=")(\d+)(")', sub, model_settings), n[0]


# ------------------------------------------------------------------ policies
def white_first_order(ps, used):
    """(order, mapping) putting white in slot 1 and the one dark slot in 2.

    Refuses rather than guessing when the project doesn't reduce to two: no
    white slot, more than one dark slot in use, or a slot in use that the new
    order would drop."""
    colours = [c.upper() for c in ps["filament_colour"]]
    if WHITE not in colours:
        return None, f"no {WHITE} slot among {colours}"
    white = colours.index(WHITE)
    dark = [i for i in range(len(colours)) if i != white and i + 1 in used]
    if len(dark) > 1:
        return None, f"{len(dark)} dark slots in use ({[colours[i] for i in dark]})"
    if not dark:                          # single-colour project: keep slot 2
        dark = [next((i for i in range(len(colours)) if i != white), None)]
        if dark[0] is None:
            return None, "only one slot and it is white"
    order = [white, dark[0]]
    dropped = [i + 1 for i in range(len(colours)) if i not in order]
    if any(d in used for d in dropped):
        return None, f"slots {dropped} would be dropped but are in use"
    return (order, {o + 1: i + 1 for i, o in enumerate(order)}), None


def drop_unused_order(ps, used, keep_min=2):
    """(order, mapping) shedding TRAILING unused slots only — never reorders,
    so it is always safe to apply unattended. A dead slot in the middle (560's
    lime) needs a real decision and is left for --white-first."""
    n = slots(ps)
    keep = max(max(used, default=1), keep_min)
    if keep >= n:
        return None, None
    order = list(range(keep))
    return (order, {i + 1: i + 1 for i in order}), None


# ------------------------------------------------------------------- rewrite
def write_settings(path, new_ps, new_ms=None):
    """Replace project_settings (and optionally model_settings) in place. Every
    other zip member is copied through byte-for-byte, so geometry is never
    touched by any operation here."""
    shutil.copy2(path, str(path) + ".bak")
    src = zipfile.ZipFile(str(path) + ".bak")
    blob = (json.dumps(new_ps, ensure_ascii=False, indent=4) + "\n").encode()
    with zipfile.ZipFile(path, "w") as out:
        for info in src.infolist():
            data = (blob if info.filename == PS else
                    new_ms.encode() if (new_ms is not None
                                        and info.filename == MS) else
                    src.read(info.filename))
            out.writestr(info, data, zipfile.ZIP_DEFLATED)
    src.close()
    Path(str(path) + ".bak").unlink()


def apply(path, order, mapping, dry=False):
    z = zipfile.ZipFile(path)
    ps = json.loads(z.read(PS))
    ms = z.read(MS).decode()
    n = slots(ps)

    new_ps, notes = remap(ps, order)
    new_ms, hits = remap_extruders(ms, mapping)
    before = [c.upper() for c in ps["filament_colour"]]
    after = [c.upper() for c in new_ps["filament_colour"]]
    print(f"  slots {n} -> {len(order)}   {before} -> {after}")
    print(f"  {len(notes)} per-filament keys rewritten, "
          f"{hits} extruder refs remapped {mapping}")
    if dry:
        return
    z.close()
    write_settings(path, new_ps, new_ms)


def explicit_order(spec, mapping_spec):
    """--order 3,1 --extruder-map 3=1,2=1,1=2 — 1-based, source slots.

    The escape hatch for cases the policies refuse, above all a MERGE (two
    source slots landing on one), which no permutation can express: Dominion
    560's lid body sits on a stray lime slot and has to join the white one."""
    order = [int(x) - 1 for x in spec.split(",")]
    mapping = {}
    for pair in mapping_spec.split(","):
        old, _, new = pair.partition("=")
        mapping[int(old)] = int(new)
    return order, mapping


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("projects", nargs="+")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--white-first", action="store_true",
                   help="two slots: white first, the dark one second")
    g.add_argument("--drop-unused", action="store_true",
                   help="shed trailing unused slots (never reorders)")
    g.add_argument("--check", action="store_true", help="report only")
    g.add_argument("--makerworld", action="store_true",
                   help="reset printer/filament presets to stock so MakerWorld "
                        "accepts the upload")
    g.add_argument("--order", help="explicit 1-based source slots, e.g. 3,1")
    ap.add_argument("--extruder-map", help="explicit old=new pairs, e.g. 3=1,1=2")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if bool(args.order) != bool(args.extruder_map):
        ap.error("--order and --extruder-map go together")

    changed = skipped = 0
    for p in args.projects:
        z = zipfile.ZipFile(p)
        ps = json.loads(z.read(PS))
        used = used_extruders(z.read(MS).decode())
        z.close()
        print(f"{Path(p).name}")
        if args.check:
            print(f"  slots {slots(ps)} {ps['filament_colour']}  used={used}")
            for key, found, want, block in makerworld_problems(ps):
                tag = "BLOCKS" if block else "stale "
                print(f"  {tag} {key} = {found!r}, wants {want!r}")
            continue
        if args.makerworld:
            issues = [i for i in makerworld_problems(ps) if i[3]]
            if not issues:
                print("  already stock")
                continue
            for key, found, want, _ in issues:
                print(f"  {key}: {found!r} -> {want!r}")
            if not args.dry_run:
                write_settings(p, makerworld_fix(ps))
            changed += 1
            continue
        if args.order:
            got, why = explicit_order(args.order, args.extruder_map), None
        else:
            pick = (white_first_order if args.white_first else drop_unused_order)
            got, why = pick(ps, used)
        if got is None:
            if why:
                print(f"  SKIP — {why}")
                skipped += 1
            else:
                print("  already normal")
            continue
        order, mapping = got
        # Nothing an object still points at may be left dangling: an unmapped
        # or out-of-range extruder renders as a different colour, or Bambu
        # refuses the file outright.
        stray = [e for e in used
                 if not 1 <= mapping.get(e, e) <= len(order)]
        if stray:
            print(f"  SKIP — extruder(s) {stray} in use would not land in "
                  f"1..{len(order)} under {mapping}")
            skipped += 1
            continue
        if order == list(range(slots(ps))) and all(k == v for k, v in mapping.items()):
            print("  already normal")
            continue
        apply(p, order, mapping, args.dry_run)
        changed += 1
    print(f"\n{changed} project(s) rewritten, {skipped} skipped"
          + (" (dry run)" if args.dry_run else ""))
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
