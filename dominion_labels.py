#!/usr/bin/env python3
"""Generate Dominion expansion-box labels as two-colour 3MF files.

Each label is a chamfered rectangular plate (white) with the expansion
name, a 3-step staircase logo in the bottom-left corner and a small
"cc" mark in the bottom-right corner raised on top (black).

Geometry replicated from the original Onshape design (SideLabel STEP
export). Font: Orbitron Bold (Google Fonts, OFL licence).

Usage:
    python3 dominion_labels.py                     # all names x all widths
    python3 dominion_labels.py --names "Seaside,Renaissance"
    python3 dominion_labels.py --widths 20,53
    python3 dominion_labels.py --step              # also export STEP files

Requires: pip install build123d
Font: put Orbitron-Bold.ttf next to this script.
"""

import argparse
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
WIDTHS = [20.0, 32.0, 53.0, 80.0, 156.4]

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


def read_names_file(path: Path) -> list:
    """Parse the NAMES file: one set per line, optionally ',<flags>' where
    flags is bit-based — bit 1: the plain label, bit 2: '<name> 1' and
    '<name> 2' labels for split boxes (so 0 skips, 3 makes all three).
    The special name '(BLANK)' is the blank label (logo + cc, no text).
    Blank lines and lines starting with '#' are ignored."""
    names = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, flags = line, 1
        if "," in line:
            head, tail = line.rsplit(",", 1)
            tail = tail.strip()
            if tail.lstrip("+-").isdigit():
                name, flags = head.strip(), int(tail)
        if not name or flags < 0:
            sys.exit(f"{path}:{lineno}: cannot parse {raw!r}")
        if name.upper() == "(BLANK)":
            name = ""
        if flags & 1:
            names.append(name)
        if flags & 2:
            names += [f"{name} 1", f"{name} 2"]
    return names


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
        self.xheight = self.render("c").bounding_box().size.Y

    def render(self, txt: str):
        return Text(txt, font_size=self.PROBE_SIZE, font_path=self.font_path,
                    align=(Align.MIN, Align.NONE))


def make_label(name: str, width: float, font: LabelFont):
    """Build one label; returns (base Solid (white), raised Compound (black))."""
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

    # expansion name: as large as fits its box — sides aligned with the
    # logo's left and the cc's right edge, bottom 2 mm above the logo, top
    # at least 3 mm below the label edge. Width-limited names span the box
    # exactly; height-limited ones fill it vertically, centred horizontally.
    if name:
        box_left, box_right = MARGIN, width - MARGIN
        box_bottom = MARGIN + LOGO_SIZE + TEXT_GAP_ABOVE_LOGO
        box_top = height - TEXT_TOP_MARGIN
        txt = font.render(name)
        bb = txt.bounding_box()
        factor = min((box_right - box_left) / bb.size.X,
                     (box_top - box_bottom) / bb.size.Y)
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
    vertices, triangles = Mesher._mesh_shape(copy_module.deepcopy(shape), 0.001, 0.1)
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


def bambu_model_settings(obj_id: int, obj_name: str, parts) -> str:
    """Bambu Studio / OrcaSlicer project metadata: assigns each part of the
    object to a filament slot (`extruder`). This is what makes the file open
    two-coloured — Bambu ignores standard 3MF material colours entirely.
    `parts` is a list of (mesh resource id, part name, extruder number)."""
    part_xml = "".join(
        f'    <part id="{pid}" subtype="normal_part">\n'
        f'      <metadata key="name" value="{pname}"/>\n'
        f'      <metadata key="matrix" value="{IDENTITY_4X4}"/>\n'
        f'      <metadata key="extruder" value="{extruder}"/>\n'
        f"    </part>\n"
        for pid, pname, extruder in parts
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<config>\n"
        f'  <object id="{obj_id}">\n'
        f'    <metadata key="name" value="{obj_name}"/>\n'
        f'    <metadata key="extruder" value="1"/>\n'
        f"{part_xml}"
        "  </object>\n"
        "  <plate>\n"
        '    <metadata key="plater_id" value="1"/>\n'
        '    <metadata key="plater_name" value=""/>\n'
        '    <metadata key="locked" value="false"/>\n'
        "    <model_instance>\n"
        f'      <metadata key="object_id" value="{obj_id}"/>\n'
        '      <metadata key="instance_id" value="0"/>\n'
        f'      <metadata key="identify_id" value="{100 + obj_id}"/>\n'
        "    </model_instance>\n"
        "  </plate>\n"
        "  <assemble>\n"
        f'    <assemble_item object_id="{obj_id}" instance_id="0" '
        f'transform="1 0 0 0 1 0 0 0 1 0 0 0" offset="0 0 0"/>\n'
        "  </assemble>\n"
        "</config>\n"
    )


def inject_bambu_metadata(path: Path, obj_id: int, obj_name: str, parts):
    """Rewrite the 3MF zip: add Metadata/model_settings.config and stamp the
    model file so Bambu Studio recognises the project metadata."""
    with zipfile.ZipFile(path) as zf:
        entries = {info.filename: zf.read(info.filename) for info in zf.infolist()}

    model = entries["3D/3dmodel.model"].decode("utf-8")
    stamp = (
        '<metadata name="Application">BambuStudio-02.00.03.54</metadata>\n\t'
        '<metadata name="BambuStudio:3mfVersion">1</metadata>\n\t'
    )
    entries["3D/3dmodel.model"] = model.replace(
        "<resources>", stamp + "<resources>", 1).encode("utf-8")
    entries["Metadata/model_settings.config"] = bambu_model_settings(
        obj_id, obj_name, parts).encode("utf-8")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)


def write_3mf(path: Path, name: str, base, raised, bambu: bool):
    """Export base + raised as ONE 3MF object with two component parts,
    optionally with Bambu Studio filament assignments (raised->1, base->2)."""
    m = Mesher()
    base_3mf = add_mesh_object(m, base, "base")
    raised_3mf = add_mesh_object(m, raised, "raised")
    assembly = m.model.AddComponentsObject()
    assembly.AddComponent(base_3mf, m.wrapper.GetIdentityTransform())
    assembly.AddComponent(raised_3mf, m.wrapper.GetIdentityTransform())
    assembly.SetName(name)
    m.model.AddBuildItem(assembly, m.wrapper.GetIdentityTransform())
    m.write(str(path))
    if bambu:
        inject_bambu_metadata(
            path, assembly.GetResourceID(), name,
            [(base_3mf.GetResourceID(), "base", 2),
             (raised_3mf.GetResourceID(), "raised", 1)])


def safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name) or "Blank"


def main():
    ap = argparse.ArgumentParser(description="Generate Dominion box labels")
    ap.add_argument("--names", help="comma-separated set names (default: built-in list)")
    ap.add_argument("--widths", help="comma-separated widths in mm (default: all)")
    ap.add_argument("--out", default="labels_out", help="output directory")
    ap.add_argument("--step", action="store_true", help="also export STEP files")
    ap.add_argument("--no-blank", action="store_true", help="skip the blank label")
    ap.add_argument("--plain", action="store_true",
                    help="vanilla 3MF without Bambu Studio filament metadata")
    args = ap.parse_args()

    if args.names:
        names = [n.strip() for n in args.names.split(",")]
    else:
        names_file = find_names_file()
        names = read_names_file(names_file) if names_file else list(NAMES)
    if not args.no_blank and "" not in names:
        names.append("")                    # blank label: logo + cc, no name
    widths = [float(w) for w in args.widths.split(",")] if args.widths else WIDTHS

    font = LabelFont(find_font())
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    for name in names:
        for width in widths:
            base, raised = make_label(name, width, font)
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
