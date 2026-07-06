#!/usr/bin/env python3
"""Generate board-game expansion-box labels as two-colour 3MF files.

Each label is a chamfered rectangular plate (white) with the expansion
name, a 3-step staircase logo in the bottom-left corner and a small
"cc" mark in the bottom-right corner raised on top (black).

Geometry replicated from the original Onshape design (SideLabel STEP
export). Font: Orbitron Bold (Google Fonts, OFL licence).

Usage:
    python3 dominion_labels.py                     # per-label files, Dominion
    python3 dominion_labels.py --plates            # bulk multi-plate 3MFs
    python3 dominion_labels.py --sets              # one 3MF per set
    python3 dominion_labels.py --game FCM --plates
    python3 dominion_labels.py --names "Seaside,Renaissance" --widths 32,53
    python3 dominion_labels.py --step              # also export STEP files

Requires: pip install build123d
Font: put Orbitron-Bold.ttf next to this script.
"""

import argparse
import json
import math
import sys
import zipfile
from pathlib import Path

from build123d import (
    Align,
    Color,
    Compound,
    Mesher,
    Polygon,
    Rectangle,
    Text,
    Vector,
    export_step,
    extrude,
    scale,
)

# --------------------------------------------------------------------------
# Parameters (mm) — measured from the original Onshape STEP export
# --------------------------------------------------------------------------
LABEL_HEIGHT = 22.2          # overall label height (STEP export measured 22.1)

# Label widths per game: "widths" for a set's labels, "split_widths" for the
# "<name> 1"/"<name> 2" labels of sets split across two boxes. "front" (if
# any) is the box-front width, included on every box's default plate in
# --sets mode. "caps" is the standard text size (capital height, mm) per
# label width — labels of the same width all use it, and long names shrink
# to fit. A width without an entry (e.g. via --widths) sizes its text to
# fill the label instead.
GAMES = {
    "Dominion": {
        "front": 156.4,
        "widths": [156.4, 80.0, 53.0, 32.0],
        "split_widths": [156.4, 53.0, 32.0],
        "caps": {156.4: 6.5, 80.0: 5.0, 53.0: 4.5, 32.0: 3.5},
    },
    "FCM": {
        "front": 156.4,
        "widths": [156.4, 45.0, 30.0, 20.0],
        "split_widths": [156.4, 45.0, 30.0, 20.0],
        "caps": {156.4: 6.5, 45.0: 4.5, 30.0: 3.5, 20.0: 2.8},
    },
}

BASE_THICKNESS = 0.6         # white base plate
RAISE_TEXT = 0.6             # how far the name text stands proud of the base
RAISE_LOGO = 0.4             # staircase + "cc": lower so the text stands out
TAPER = 45.0                 # chamfer angle all around the base

MARGIN = 3.6                 # logo/cc inset from the label outline
LOGO_SIZE = 4.5              # staircase bounding square
LOGO_STEPS = 3

TEXT_GAP_ABOVE_LOGO = 2.0    # gap between logo top and text bottom
TEXT_TOP_MARGIN = 3.0        # min gap between text top and label top edge
CC_XHEIGHT = 2.5             # height of the lowercase "cc" mark

FONT_FILE = "Orbitron-Bold.ttf"
NAMES_FILE = "NAMES"         # set list, one name per line (see read_names_file)

BASE_COLOR = Color(1.0, 1.0, 1.0)    # white
RAISED_COLOR = Color(0.0, 0.0, 0.0)  # black

# Mesh tessellation (mm). 0.01 is invisible at print scale and keeps the
# combined multi-plate file to a manageable size.
MESH_LINEAR_DEFLECTION = 0.01
MESH_ANGULAR_DEFLECTION = 0.2

# --plates mode: Bambu P1S multi-plate project layout
PLATE_SIZE = 256.0           # P1S bed
PLATE_MARGIN = 5.0           # keep-out border -> 246mm usable per row
PLATE_EXCLUDE = (18.0, 28.0)     # no-print corner (front-left) on P1 printers
LABEL_GAP = 2.0              # gap between labels in a row / between rows
SET_GAP = 4.0                # extra vertical gap between set blocks
WIPE_TOWER_XY = (210.0, 214.0)   # wipe tower in the free strip at the top
PLATE_TOP_LIMIT = WIPE_TOWER_XY[1] - 5.0     # labels stay below this line
PLATE_STRIDE = PLATE_SIZE * 1.2  # BambuStudio LOGICAL_PART_PLATE_GAP = 1/5
PROJECT_SETTINGS_FILE = "bambu_project_settings.config"

# Fallback set list when there is no NAMES file and no --names
NAMES = [
    "Base Set 1",
]

# --------------------------------------------------------------------------


def find_font() -> str:
    here = Path(__file__).resolve().parent
    for cand in (here / FONT_FILE, Path.cwd() / FONT_FILE):
        if cand.exists():
            return str(cand)
    sys.exit(
        f"Font file '{FONT_FILE}' not found next to the script.\n"
        "Download Orbitron (Bold) from https://fonts.google.com/specimen/Orbitron"
    )


def find_names_file():
    here = Path(__file__).resolve().parent
    for cand in (Path.cwd() / NAMES_FILE, here / NAMES_FILE):
        if cand.is_file():
            return cand
    return None


def parse_width(text: str, allowed, where: str, key: str) -> float:
    """A width from the NAMES file must be one of the game's standard
    widths; returns the canonical float."""
    try:
        width = float(text)
    except ValueError:
        sys.exit(f"{where}: {key}={text!r} is not a number")
    for std in allowed:
        if abs(std - width) < 0.01:
            return std
    sys.exit(f"{where}: {key}={text} is not a standard width for this game "
             f"(allowed: {', '.join(f'{w:g}' for w in allowed)})")


def parse_box(value: str, allowed, where: str, key: str) -> dict:
    """'U[/S][@<box name>:<box model>]' -> {"widths": (unsleeved, sleeved),
    "info": (box name, box model) | None}. One width means both sleevings."""
    width_part, _, info_part = value.partition("@")
    values = width_part.split("/")
    if len(values) not in (1, 2):
        sys.exit(f"{where}: {key} takes <unsleeved>[/<sleeved>], "
                 f"got {width_part!r}")
    widths = [parse_width(v, allowed, where, key) for v in values]
    if len(widths) == 1:
        widths *= 2
    info = None
    if info_part:
        box_name, sep, model = info_part.partition(":")
        if not sep or not box_name.strip() or not model.strip():
            sys.exit(f"{where}: {key} box info must be "
                     f"'@<box name>:<box model>', got {info_part!r}")
        info = (box_name.strip(), model.strip())
    return {"widths": tuple(widths), "info": info}


def read_names_file(path: Path, game: str) -> list:
    """Parse the NAMES file and return set records for `game`.

    Each line is '<game>,<set name>[,<key>=V]...' where every value V is
    '<unsleeved>[/<sleeved>][@<box name>:<box model>]' — label widths per
    sleeving (one value = both) plus the optional recommended-box identity
    shown in plate titles:
      box=V    the whole set's box; presence means whole-box labels
      split=V  both split half-boxes; presence means '<name> 1' and
               '<name> 2' labels
      split1=/split2=  like split= but for halves of different sizes
               (must be given together)
    Widths must be standard widths of the game (box= against `widths`,
    split*= against `split_widths`). A line with no keys is skipped.
    The special name '(BLANK)' is the blank label (logo + cc, no text).
    Blank lines and '#' comments are ignored. Returns dicts
    {"name": str, "box": parse_box() | None, "split": [half1, half2] | None}."""
    cfg = GAMES[game]
    records = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        where = f"{path.name}:{lineno}"
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            sys.exit(f"{where}: cannot parse {raw!r} "
                     f"(expected '<game>,<set name>[,box=U[/S]][,split=U[/S]]')")
        line_game, name = parts[0], parts[1]
        if line_game.lower() != game.lower():
            continue
        if name.upper() == "(BLANK)":
            name = ""
        box, split, halves = None, None, {}
        for field in parts[2:]:
            if not field:
                continue
            key, sep, value = field.partition("=")
            key = key.strip().lower()
            if key == "box" and sep:
                box = parse_box(value, cfg["widths"], where, "box")
            elif key == "split" and sep:
                half = parse_box(value, cfg["split_widths"], where, "split")
                split = [half, half]
            elif key in ("split1", "split2") and sep:
                halves[key] = parse_box(value, cfg["split_widths"], where, key)
            else:
                sys.exit(f"{where}: unknown field {field!r} (expected "
                         f"box=U[/S], split=U[/S] or split1=/split2=)")
        if halves:
            if split is not None or set(halves) != {"split1", "split2"}:
                sys.exit(f"{where}: split1= and split2= must be given "
                         f"together (and not combined with split=)")
            split = [halves["split1"], halves["split2"]]
        if box is not None or split is not None:
            records.append({"name": name, "box": box, "split": split})
    return records


def staircase(size: float, steps: int) -> Polygon:
    """3-step staircase logo, outer corner at (0,0), steps descending
    left-to-right, exactly as in the original label. Points listed
    counter-clockwise so the face normal is +Z (extrudes upward)."""
    s = size / steps
    pts = [(0.0, 0.0), (size, 0.0)]            # bottom edge, left to right
    for i in range(steps):                     # up the staircase, right to left
        x, y = size - i * s, i * s
        pts += [(x, y + s), (x - s, y + s)]    # riser up, then tread left
    return Polygon(*pts, align=None)


class LabelFont:
    """Wraps Text() with empirical metrics (OCCT's baseline anchoring is
    font-dependent, so we probe it with a reference glyph)."""

    PROBE_SIZE = 100.0

    def __init__(self, font_path: str):
        self.font_path = font_path
        self.cap = self.render("H").bounding_box().size.Y
        self.xheight = self.render("c").bounding_box().size.Y

    def render(self, txt: str):
        return Text(txt, font_size=self.PROBE_SIZE, font_path=self.font_path,
                    align=(Align.MIN, Align.NONE))


def make_label(name: str, width: float, font: LabelFont, caps: dict = None):
    """Build one label; returns (base Solid (white), raised Compound (black)).
    `caps` maps label width -> standard text capital height (mm); without an
    entry for `width` the text sizes to fill its box."""
    height = LABEL_HEIGHT
    z_top = Vector(0, 0, BASE_THICKNESS)

    # base plate: rectangle extruded with a 45-degree inward taper (chamfer)
    base = extrude(Rectangle(width, height, align=(Align.MIN, Align.MIN)),
                   amount=BASE_THICKNESS, taper=TAPER)

    # staircase logo, bottom-left corner
    logo = staircase(LOGO_SIZE, LOGO_STEPS).translate(Vector(MARGIN, MARGIN, 0))
    raised = extrude(logo.translate(z_top), amount=RAISE_LOGO)

    # "cc" mark, bottom-right corner, bottom-aligned with the logo
    cc = scale(font.render("cc"), by=CC_XHEIGHT / font.xheight)
    bb = cc.bounding_box()
    cc = cc.translate(Vector(width - MARGIN - bb.max.X, MARGIN - bb.min.Y, 0))
    raised += extrude(cc.translate(z_top), amount=RAISE_LOGO)

    # expansion name: standard capital height for this label width (caps),
    # shrunk to fit its box when the name is too long — the box runs from
    # the logo's left to the cc's right edge, from 2 mm above the logo to
    # 3 mm below the top edge. Centred horizontally, bottom-anchored.
    if name:
        box_left, box_right = MARGIN, width - MARGIN
        box_bottom = MARGIN + LOGO_SIZE + TEXT_GAP_ABOVE_LOGO
        box_top = height - TEXT_TOP_MARGIN
        txt = font.render(name)
        bb = txt.bounding_box()
        factor = min((box_right - box_left) / bb.size.X,
                     (box_top - box_bottom) / bb.size.Y)
        cap = (caps or {}).get(width)
        if cap is not None:
            factor = min(factor, cap / font.cap)
        txt = scale(txt, by=factor)
        bb = txt.bounding_box()
        txt = txt.translate(Vector(
            box_left + (box_right - box_left - bb.size.X) / 2 - bb.min.X,
            box_bottom - bb.min.Y, 0))
        raised += extrude(txt.translate(z_top), amount=RAISE_TEXT)

    # Normalise for export: a bare Solid for the base, and one Compound
    # holding every raised solid (letters, logo, cc) for the black body.
    base_solid = base.solid()
    base_solid.color = BASE_COLOR
    base_solid.label = "base"
    raised_comp = Compound(raised.solids())
    raised_comp.color = RAISED_COLOR
    raised_comp.label = "raised"
    return base_solid, raised_comp


def add_mesh_object(mesher: Mesher, shape, part_number: str):
    """Mesh `shape` into the 3MF as ONE object and return the lib3mf object.

    Mesher.add_shape() splits a Compound into one 3MF object per solid and
    loses the per-shape colour while doing so; slicers would then see every
    letter as a separate part. This replicates its body (build123d 0.11)
    without the flattening, and emits no build item — the caller assembles
    the meshes into a single components object instead.
    """
    import copy as copy_module

    from build123d.mesher import MeshType

    mesh_3mf = mesher.model.AddMeshObject()
    vertices, triangles = Mesher._mesh_shape(
        copy_module.deepcopy(shape),
        MESH_LINEAR_DEFLECTION, MESH_ANGULAR_DEFLECTION)
    vertices_3mf, triangles_3mf = Mesher._create_3mf_mesh(vertices, triangles)
    mesh_3mf.SetGeometry(vertices_3mf, triangles_3mf)
    mesh_3mf.SetType(Mesher._map_b3d_mesh_type_3mf[MeshType.MODEL])
    if shape.label:
        mesh_3mf.SetName(shape.label)
    mesh_3mf.SetPartNumber(part_number)
    mesher._add_color(shape, mesh_3mf)
    if not mesh_3mf.IsValid():
        raise RuntimeError("3mf mesh is invalid")
    mesher.meshes.append(mesh_3mf)
    return mesh_3mf


IDENTITY_4X4 = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"


def add_assembled_label(mesher: Mesher, stem: str, base, raised):
    """Add one label to the model as a single object with two component
    parts. Returns (components object, model_settings object entry)."""
    base_3mf = add_mesh_object(mesher, base, "base")
    raised_3mf = add_mesh_object(mesher, raised, "raised")
    assembly = mesher.model.AddComponentsObject()
    assembly.AddComponent(base_3mf, mesher.wrapper.GetIdentityTransform())
    assembly.AddComponent(raised_3mf, mesher.wrapper.GetIdentityTransform())
    assembly.SetName(stem)
    return assembly, {
        "id": assembly.GetResourceID(),
        "name": stem,
        "parts": [(base_3mf.GetResourceID(), "base", 2),      # white
                  (raised_3mf.GetResourceID(), "raised", 1)],  # black
    }


def bambu_model_settings(objects, plates) -> str:
    """Bambu Studio / OrcaSlicer project metadata: assigns each part of each
    object to a filament slot (`extruder`) and each object instance to a
    plate. This is what makes the file open two-coloured — Bambu ignores
    standard 3MF material colours entirely. `objects` is a list of entries
    from add_assembled_label(); `plates` is one dict per plate:
    {"name": plate name, "instances": [(object id, identify id), ...]}."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    for obj in objects:
        lines += [
            f'  <object id="{obj["id"]}">',
            f'    <metadata key="name" value="{obj["name"]}"/>',
            '    <metadata key="extruder" value="1"/>',
        ]
        for pid, pname, extruder in obj["parts"]:
            lines += [
                f'    <part id="{pid}" subtype="normal_part">',
                f'      <metadata key="name" value="{pname}"/>',
                f'      <metadata key="matrix" value="{IDENTITY_4X4}"/>',
                f'      <metadata key="extruder" value="{extruder}"/>',
                "    </part>",
            ]
        lines.append("  </object>")
    for plate_no, plate in enumerate(plates, 1):
        lines += [
            "  <plate>",
            f'    <metadata key="plater_id" value="{plate_no}"/>',
            f'    <metadata key="plater_name" value="{plate["name"]}"/>',
            '    <metadata key="locked" value="false"/>',
        ]
        for obj_id, identify_id in plate["instances"]:
            lines += [
                "    <model_instance>",
                f'      <metadata key="object_id" value="{obj_id}"/>',
                '      <metadata key="instance_id" value="0"/>',
                f'      <metadata key="identify_id" value="{identify_id}"/>',
                "    </model_instance>",
            ]
        lines.append("  </plate>")
    lines.append("  <assemble>")
    for plate in plates:
        for obj_id, _ in plate["instances"]:
            lines.append(
                f'    <assemble_item object_id="{obj_id}" instance_id="0" '
                f'transform="1 0 0 0 1 0 0 0 1 0 0 0" offset="0 0 0"/>')
    lines += ["  </assemble>", "</config>", ""]
    return "\n".join(lines)


def inject_bambu_metadata(path: Path, objects, plates, project_settings=None):
    """Rewrite the 3MF zip: add Metadata/model_settings.config (and, for
    multi-plate projects, Metadata/project_settings.config) and stamp the
    model file so Bambu Studio recognises the project metadata."""
    with zipfile.ZipFile(path) as zf:
        entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}

    model = entries["3D/3dmodel.model"].decode("utf-8")
    stamp = (
        '<metadata name="Application">BambuStudio-02.07.01.62</metadata>\n\t'
        '<metadata name="BambuStudio:3mfVersion">1</metadata>\n\t'
    )
    entries["3D/3dmodel.model"] = model.replace(
        "<resources>", stamp + "<resources>", 1).encode("utf-8")
    entries["Metadata/model_settings.config"] = bambu_model_settings(
        objects, plates).encode("utf-8")
    if project_settings is not None:
        entries["Metadata/project_settings.config"] = project_settings.encode("utf-8")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def write_3mf(path: Path, name: str, base, raised, bambu: bool):
    """Export base + raised as ONE 3MF object with two component parts,
    optionally with Bambu Studio filament assignments (raised->1, base->2)."""
    m = Mesher()
    assembly, entry = add_assembled_label(m, name, base, raised)
    m.model.AddBuildItem(assembly, m.wrapper.GetIdentityTransform())
    m.write(str(path))
    if bambu:
        inject_bambu_metadata(path, [entry], [
            {"name": name, "instances": [(entry["id"], 100 + entry["id"])]}])


# --------------------------------------------------------------------------
# --plates: one Bambu multi-plate project with every label laid out
# --------------------------------------------------------------------------


def plate_columns(n_plates: int) -> int:
    """Plate grid column count, replicating BambuStudio compute_colum_count."""
    value = math.sqrt(n_plates)
    return round(value) + 1 if value > round(value) else round(value)


def translation(mesher: Mesher, x: float, y: float):
    t = mesher.wrapper.GetIdentityTransform()
    t.Fields[3][0] = x
    t.Fields[3][1] = y
    return t


def row_width(row) -> float:
    return sum(row) + LABEL_GAP * (len(row) - 1)


def build_block(widths) -> list:
    """One set's labels as rows of widths (next-fit), identical for every
    set of the game. The shortest row goes at the bottom so the block can
    sit beside the no-print corner."""
    cap = PLATE_SIZE - 2 * PLATE_MARGIN
    rows, cur = [], []
    for width in widths:
        if cur and row_width(cur + [width]) > cap:
            rows.append(cur)
            cur = []
        cur.append(width)
    if cur:
        rows.append(cur)
    return sorted(rows, key=row_width)


def layout_sets(sets) -> tuple:
    """Place one block per set, bottom-up, plate by plate. Every block of a
    game gets identical geometry: the bottom row is indented past the
    no-print corner when it fits there (so the block may sit at the plate
    bottom); blocks whose bottom row is too wide for the indent start above
    the corner instead. `sets` is a list of (set name, widths). Returns
    (placements, plate count); each placement is (plate, x, y, name, width)."""
    indent = max(PLATE_MARGIN, PLATE_EXCLUDE[0] + LABEL_GAP)
    placements = []
    plate, y = 0, PLATE_MARGIN
    for set_name, widths in sets:
        rows = build_block(widths)
        height = len(rows) * LABEL_HEIGHT + (len(rows) - 1) * LABEL_GAP
        indent_ok = indent + row_width(rows[0]) <= PLATE_SIZE - PLATE_MARGIN
        start = y if indent_ok else max(y, PLATE_EXCLUDE[1])
        if start + height > PLATE_TOP_LIMIT:
            plate += 1
            start = PLATE_MARGIN if indent_ok else PLATE_EXCLUDE[1]
        for i, row in enumerate(rows):
            row_y = start + i * (LABEL_HEIGHT + LABEL_GAP)
            x = indent if i == 0 and indent_ok else PLATE_MARGIN
            for width in row:
                placements.append((plate, x, row_y, set_name, width))
                x += width + LABEL_GAP
        y = start + height + SET_GAP
    return placements, plate + 1


def render_project_settings(n_plates: int):
    """Bambu printer/filament profile for the combined file, with one wipe
    tower position per plate (the top strip above the label rows)."""
    template = Path(__file__).resolve().parent / PROJECT_SETTINGS_FILE
    if not template.is_file():
        print(f"warning: {PROJECT_SETTINGS_FILE} not found - the combined "
              "file will open without printer/filament profile")
        return None
    settings = json.loads(template.read_text(encoding="utf-8"))
    settings["wipe_tower_x"] = [str(WIPE_TOWER_XY[0])] * n_plates
    settings["wipe_tower_y"] = [str(WIPE_TOWER_XY[1])] * n_plates
    return json.dumps(settings, indent=4)


def set_plate_specs(record: dict, cfg: dict) -> list:
    """Plates for one set's own 3MF, from its NAMES record: single cascade
    (unsleeved), single cascade (sleeved), split cascade (unsleeved), split
    cascade (sleeved) — collapsing sleeved/unsleeved pairs that use the
    same widths — plus every other label as spares. Split plates always
    carry one front and one side label per half-box. Returns
    [(plate name, [(label name, width), ...]), ...]."""
    name = record["name"]
    display = name or "Blank"
    front = cfg.get("front")
    UNSLEEVED, SLEEVED = 0, 1
    TAG = {UNSLEEVED: "U", SLEEVED: "S"}
    SUFFIX = {UNSLEEVED: "-Un", SLEEVED: "-Sl"}

    def box_labels(label_name, side):
        labels = [(label_name, front)] if front else []
        if side != front:
            labels.append((label_name, side))
        return labels

    def boxes_title(infos, sleeving=None):
        """' 560 Card/U (L6.12.40-Un)' (/U-/S = sleevedness; omitted on
        plates that cover both). Slashes in models become dashes."""
        infos = [i for i in dict.fromkeys(infos) if i]
        tag = f"/{TAG[sleeving]}" if sleeving is not None else ""
        model_suffix = SUFFIX[sleeving] if sleeving is not None else ""
        parts = [f"{box_name}{tag} ({model.replace('/', '-')}{model_suffix})"
                 for box_name, model in infos]
        if not parts:
            return tag
        return " " + "; ".join(parts)

    specs = []
    if record["box"]:
        info = record["box"]["info"]
        plates = [
            (f"{display}{boxes_title([info], s)}",
             box_labels(name, record["box"]["widths"][s]))
            for s in (UNSLEEVED, SLEEVED)]
        if plates[0][1] == plates[1][1]:
            plates = [(f"{display}{boxes_title([info])}", plates[0][1])]
        specs += plates
    if record["split"]:
        def split_labels(sleeving):
            labels = []
            for half_no, half in enumerate(record["split"], 1):
                labels += box_labels(f"{name} {half_no}", half["widths"][sleeving])
            return labels
        infos = [half["info"] for half in record["split"]]
        plates = [
            (f"{display} split{boxes_title(infos, s)}", split_labels(s))
            for s in (UNSLEEVED, SLEEVED)]
        if plates[0][1] == plates[1][1]:
            plates = [(f"{display} split{boxes_title(infos)}", plates[0][1])]
        specs += plates
    spares = []
    if record["box"]:
        used = {front, *record["box"]["widths"]}
        spares += [(name, w) for w in cfg["widths"] if w not in used]
    if record["split"]:
        for half_no, half in enumerate(record["split"], 1):
            used = {front, *half["widths"]}
            spares += [(f"{name} {half_no}", w) for w in cfg["split_widths"]
                       if w not in used]
    if spares:
        specs.append((f"{display} spares", spares))
    return specs


def write_project_3mf(path: Path, plate_specs, font: LabelFont, caps: dict = None):
    """Write a Bambu project with a fixed plate composition: one plate per
    (plate name, labels) spec. Labels are stacked one above the other in
    list order (first label on top), centre-aligned, with the stack
    roughly centred on the plate."""
    n_plates = len(plate_specs)
    cols = plate_columns(n_plates)
    pitch = LABEL_HEIGHT + LABEL_GAP

    m = Mesher()
    objects, plates = [], []
    identify_id = 200
    for plate_no, (plate_name, labels) in enumerate(plate_specs):
        origin_x = (plate_no % cols) * PLATE_STRIDE
        origin_y = -(plate_no // cols) * PLATE_STRIDE
        plate = {"name": plate_name, "instances": []}
        stack_height = len(labels) * pitch - LABEL_GAP
        y_bottom = max(PLATE_MARGIN, (PLATE_SIZE - stack_height) / 2)
        for i, (label_name, width) in enumerate(labels):
            x = (PLATE_SIZE - width) / 2
            y = y_bottom + (len(labels) - 1 - i) * pitch
            base, raised = make_label(label_name, width, font, caps)
            stem = f"{safe_filename(label_name)}_{width:g}mm"
            assembly, entry = add_assembled_label(m, stem, base, raised)
            m.model.AddBuildItem(assembly, translation(m, origin_x + x, origin_y + y))
            objects.append(entry)
            plate["instances"].append((entry["id"], identify_id))
            identify_id += 1
        plates.append(plate)
    m.write(str(path))
    inject_bambu_metadata(path, objects, plates,
                          project_settings=render_project_settings(n_plates))
    print(f"  {path}: {len(objects)} labels on {n_plates} plates")


def write_plates_3mf(path: Path, sets, font: LabelFont, caps: dict = None):
    """Write labels into one Bambu project 3MF spread across plates: one
    block of rows per set (same structure for every set), SET_GAP between
    blocks, wipe tower in the free top strip, plates arranged in
    BambuStudio's grid (stride 1.2 x plate size). Plates are named after
    the full list of sets they carry."""
    placements, n_plates = layout_sets(sets)
    cols = plate_columns(n_plates)

    m = Mesher()
    objects = []
    plates = [{"name": "", "instances": [], "sets": []} for _ in range(n_plates)]
    identify_id = 200
    for plate_no, x, y, name, width in placements:
        origin_x = (plate_no % cols) * PLATE_STRIDE
        origin_y = -(plate_no // cols) * PLATE_STRIDE
        base, raised = make_label(name, width, font, caps)
        stem = f"{safe_filename(name)}_{width:g}mm"
        assembly, entry = add_assembled_label(m, stem, base, raised)
        m.model.AddBuildItem(assembly, translation(m, origin_x + x, origin_y + y))
        objects.append(entry)
        plate = plates[plate_no]
        plate["instances"].append((entry["id"], identify_id))
        identify_id += 1
        set_name = name or "Blank"
        if set_name not in plate["sets"]:
            plate["sets"].append(set_name)
        print(f"  plate {plate_no + 1}: {name or '(blank)'} {width:g}mm "
              f"@ ({x:g}, {y:g})")
    for plate in plates:
        plate["name"] = ", ".join(plate["sets"])
    m.write(str(path))
    inject_bambu_metadata(path, objects, plates,
                          project_settings=render_project_settings(n_plates))
    print(f"{path}: {len(objects)} labels on {n_plates} plates")


def safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name) or "Blank"


def main():
    ap = argparse.ArgumentParser(description="Generate board game box labels")
    ap.add_argument("--game", default="Dominion",
                    help=f"game to generate labels for ({', '.join(GAMES)})")
    ap.add_argument("--names", help="comma-separated set names (default: NAMES file)")
    ap.add_argument("--widths", help="comma-separated widths in mm "
                                     "(default: the game's width lists)")
    ap.add_argument("--out", default="labels_out", help="output directory")
    ap.add_argument("--step", action="store_true", help="also export STEP files")
    ap.add_argument("--no-blank", action="store_true", help="skip the blank label")
    ap.add_argument("--plain", action="store_true",
                    help="vanilla 3MF without Bambu Studio filament metadata")
    ap.add_argument("--plates", action="store_true",
                    help="write one multi-plate Bambu project 3MF "
                         "instead of individual label files")
    ap.add_argument("--sets", action="store_true",
                    help="write one 3MF per set (default / split boxes / "
                         "spares plates) into <out>/sets/")
    ap.add_argument("--version", default="6_0",
                    help="version tag in --sets file names "
                         "('<Set> Labels <version>.3mf', default 6_0)")
    args = ap.parse_args()

    game = next((g for g in GAMES if g.lower() == args.game.lower()), None)
    if game is None:
        sys.exit(f"unknown game {args.game!r} (known: {', '.join(GAMES)})")
    cfg = GAMES[game]

    records = None
    if args.names:
        entries = [(n.strip(), False) for n in args.names.split(",")]
    else:
        names_file = find_names_file()
        if names_file:
            records = read_names_file(names_file, game)
            entries = []
            for rec in records:
                if rec["box"] is not None:
                    entries.append((rec["name"], False))
                if rec["split"]:
                    entries += [(f"{rec['name']} 1", True),
                                (f"{rec['name']} 2", True)]
        else:
            entries = [(n, False) for n in NAMES]
    if not args.no_blank and ("", False) not in entries:
        entries.append(("", False))         # blank label: logo + cc, no name

    override = [float(w) for w in args.widths.split(",")] if args.widths else None
    def widths_for(is_split):
        return override or cfg["split_widths" if is_split else "widths"]
    labels = [(name, width)
              for name, is_split in entries
              for width in widths_for(is_split)]

    font = LabelFont(find_font())
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.sets:
        if records is None:
            sys.exit("--sets needs a NAMES file with box=/split= data")
        setdir = outdir / "sets"
        setdir.mkdir(parents=True, exist_ok=True)
        for rec in records:
            fname = f"{rec['name'] or 'Blank'} Labels {args.version}.3mf"
            fname = "".join(c if c not in '\\/:*?"<>|' else "_" for c in fname)
            write_project_3mf(setdir / fname,
                              set_plate_specs(rec, cfg), font, cfg["caps"])
        print("done")
        return

    if args.plates:
        # whole sets and split-box labels as separate projects for overview
        main_sets = [(n, widths_for(False)) for n, s in entries if not s]
        split_sets = [(n, widths_for(True)) for n, s in entries if s]
        write_plates_3mf(outdir / f"{safe_filename(game)}_sets_plates.3mf",
                         main_sets, font, cfg["caps"])
        if split_sets:
            write_plates_3mf(outdir / f"{safe_filename(game)}_splits_plates.3mf",
                             split_sets, font, cfg["caps"])
        return

    for name, width in labels:
        base, raised = make_label(name, width, font, cfg["caps"])
        stem = f"{safe_filename(name)}_{width:g}mm"
        path = outdir / f"{stem}.3mf"
        write_3mf(path, stem, base, raised, bambu=not args.plain)
        if args.step:
            export_step(Compound(children=[base, raised]),
                        str(outdir / f"{stem}.step"))
        print(f"  {path}")
    print("done")


if __name__ == "__main__":
    main()
