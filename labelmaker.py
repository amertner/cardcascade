#!/usr/bin/env python3
"""Generate board-game expansion-box labels as two-colour 3MF files.

Each label is a chamfered rectangular plate (white) with the expansion name,
a 3-step staircase logo in the bottom-left corner and a small "cc" mark in
the bottom-right corner raised on top (black). Geometry from the original
Onshape SideLabel STEP; font Orbitron Bold. Output goes to
cascades/<game>/labels/. README.md, "The cc.cfg configuration file", is the
reference for the set configuration.

    python3 labelmaker.py                     # one 3MF per set (default)
    python3 labelmaker.py --plates            # bulk multi-plate 3MFs
    python3 labelmaker.py --individual        # per-label files
    python3 labelmaker.py --game FCM --plates
    python3 labelmaker.py --names "Seaside,Renaissance" --widths 32,53
    python3 labelmaker.py --step              # also export STEP files
"""

import argparse
import json
import math
import re
import sys
import zipfile
from pathlib import Path

from build123d import (
    Align,
    Color,
    Compound,
    Face,
    Mesher,
    Polygon,
    Rectangle,
    Text,
    Vector,
    export_step,
    extrude,
    import_dxf,
    scale,
)

# Parameters (mm) — measured from the original Onshape STEP export
LABEL_HEIGHT = 22.2          # overall label height (STEP export measured 22.1)

# Per game: label widths, the split-set widths, the box-front width, and the
# standard capital height per width.
GAMES = {
    "Dominion": {
        "front": 156.4,
        "widths": [156.4, 62.0, 45.0, 32.0],
        "split_widths": [156.4, 62.0, 45.0, 32.0],
        "caps": {156.4: 6.5, 62.0: 5.0, 45.0: 4.5, 32.0: 3.5},
    },
    "FCM": {
        "front": 156.4,
        "widths": [156.4, 45.0, 32.0, 20.0],
        "split_widths": [156.4, 45.0, 32.0, 20.0],
        "caps": {156.4: 6.5, 45.0: 4.5, 32.0: 3.5, 20.0: 2.8},
    },
    "Compile": {
        "front": 156.4,
        "widths": [156.4, 45.0, 32.0, 20.0],
        "split_widths": [],
        "caps": {156.4: 6.5, 45.0: 4.5, 32.0: 3.5, 20.0: 2.8},
    },
    # The generic 86 mm "mini" cascades (cad/tables.HEIGHT_CLASS): BLANK
    # labels only, and 12 tall, the class's holder (spec/BOX.md, "Shorter
    # cards"). Fronts 156.4 (L, M) and 62 (S, XS); sides 32 (Un) and 45 (Sl).
    "MiniCards": {
        "front": 156.4,
        "widths": [156.4, 62.0, 45.0, 32.0],
        "split_widths": [],
        "caps": {},
        "height": 12.0,
        # what make_label_covers.py calls each width: two of them are fronts
        "captions": {156.4: "FRONT LABEL · L AND M BOXES",
                     62.0: "FRONT LABEL · S AND XS BOXES",
                     45.0: "SIDE LABEL · SLEEVED",
                     32.0: "SIDE LABEL · UNSLEEVED"},
    },
    "Innovation": {
        # 32 and 20 are the Single Set box's side widths (50.6/39.3 mm lids)
        "front": 156.4,
        "widths": [156.4, 62.0, 45.0, 32.0, 20.0],
        "split_widths": [156.4, 62.0, 45.0, 32.0, 20.0],
        "caps": {156.4: 6.5, 62.0: 5.0, 45.0: 4.5, 32.0: 3.5, 20.0: 2.8},
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
TEXT_SIDE_GAP = 2.0          # lowered text: clearance from the logo and "cc"
CC_XHEIGHT = 2.5             # height of the lowercase "cc" mark

# Capital heights for the LOWERED layout, where the name drops beside the
# logo and the "cc" and grows into that space.
BIG_CAPS = {156.4: 9.0}

# " / " in a name breaks a line; lines stack at this gap, and a stack of two
# or more may take the lowered layout at ANY width.
LINE_BREAK = " / "
LINE_GAP = 0.45

# Game artwork (logo=) printed instead of the name: <repo>/logos/<game>/<file>
ART_DIR = "logos"
ART_MARGIN = 2.5             # artwork inset from the label outline
ART_NUMBER_CAP = 0.55        # number beside the art, as a fraction of its height
ART_NUMBER_GAP = 0.18        # gap between art and number, likewise
NUMBER_BELOW_CAP = 4.5       # number under the art: as tall as the staircase
NUMBER_MIN_CAP = 3.0         # below this it goes beside the art instead

# The bottom of the label slides into a pocket on the box, so nothing may
# be printed within this distance of the bottom edge.
BOTTOM_CLEARANCE = 2.0

FONT_FILE = "Orbitron-Bold.ttf"
CONFIG_FILE = "cc.cfg"       # set/box configuration (see read_config_file)

BASE_COLOR = Color(1.0, 1.0, 1.0)
RAISED_COLOR = Color(0.0, 0.0, 0.0)

# Mesh tessellation (mm): invisible at print scale, and keeps the file small.
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

# Fallback set list when there is no cc.cfg and no --names
NAMES = [
    "Base Set 1",
]

# --------------------------------------------------------------------------


def find_font() -> str:
    here = Path(__file__).resolve().parent
    for base in (here / "fonts", here, Path.cwd() / "fonts", Path.cwd()):
        cand = base / FONT_FILE
        if cand.exists():
            return str(cand)
    sys.exit(
        f"Font file '{FONT_FILE}' not found in fonts/ or next to the script.\n"
        "Download Orbitron (Bold) from https://fonts.google.com/specimen/Orbitron"
    )


def find_art_file(game: str, filename: str) -> Path:
    here = Path(__file__).resolve().parent
    for base in (Path.cwd(), here):
        cand = base / ART_DIR / game / filename
        if cand.is_file():
            return cand
    sys.exit(f"logo file {filename!r} not found in {ART_DIR}/{game}/")


_ART_CACHE = {}


def load_art(path: Path) -> Compound:
    """The DXF in `path` as filled faces: a wire nested in an odd number of
    others is a hole, one in an even number a face."""
    key = str(path)
    if key in _ART_CACHE:
        return _ART_CACHE[key]
    faces = sorted((Face(w) for w in import_dxf(str(path))),
                   key=lambda f: -f.area)
    if not faces:
        sys.exit(f"{path}: no closed outlines to fill")

    def inner_point(face):
        centre = face.center()
        if face.is_inside(centre):
            return centre
        bb = face.bounding_box()
        for i in range(1, 20):
            for j in range(1, 20):
                p = (bb.min.X + bb.size.X * i / 20,
                     bb.min.Y + bb.size.Y * j / 20, 0)
                if face.is_inside(p):
                    return p
        raise RuntimeError(f"{path}: cannot find a point inside an outline")

    points = [inner_point(f) for f in faces]
    parent = [None] * len(faces)
    for i in range(len(faces)):
        for j in range(i - 1, -1, -1):        # smallest container wins
            if faces[j].is_inside(points[i]):
                parent[i] = j
                break
    depth = []
    for i in range(len(faces)):
        d, p = 0, parent[i]
        while p is not None:
            d, p = d + 1, parent[p]
        depth.append(d)
    filled = [Face(faces[i].outer_wire(),
                   [faces[j].outer_wire() for j in range(len(faces))
                    if parent[j] == i])
              for i in range(len(faces)) if depth[i] % 2 == 0]
    # a clockwise outline faces -Z and would extrude into the plate
    art = Compound(children=[f if f.normal_at().Z > 0 else -f for f in filled])
    _ART_CACHE[key] = art
    return art


def find_config_file():
    here = Path(__file__).resolve().parent
    for cand in (Path.cwd() / CONFIG_FILE, here / CONFIG_FILE):
        if cand.is_file():
            return cand
    return None


def parse_width(text: str, allowed, where: str, key: str) -> float:
    """A cc.cfg width against the game's standard widths; 0 = no label."""
    try:
        width = float(text)
    except ValueError:
        sys.exit(f"{where}: {key}={text!r} is not a number")
    if width == 0:
        return 0.0
    for std in allowed:
        if abs(std - width) < 0.01:
            return std
    sys.exit(f"{where}: {key}={text} is not a standard width for this game "
             f"(allowed: {', '.join(f'{w:g}' for w in allowed)})")


def parse_box(value: str, allowed, where: str, key: str) -> dict:
    """'U[/S][@<box>:<model>]' -> {"widths": (un, sl), "info": (box name,
    model) | None}; one width means both sleevings."""
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


def read_config_file(path: Path, game: str) -> list:
    """Parse the cc.cfg configuration and return set records for `game`.
    README.md, "The cc.cfg configuration file", is the reference for the line
    grammar and the keys. Returns dicts {"name": str, "box": parse_box() |
    None, "split": [half1, half2] | None, "side": str | None, "plates":
    [(title, [widths]), ...], "nsplits": [([widths], [labels], tag), ...],
    "names": [(full, short), ...], "name_widths": [widths], "logo": Path |
    None, "numbers": int}."""
    cfg = GAMES[game]
    records = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        where = f"{path.name}:{lineno}"
        # the rest split only on a comma that STARTS another key: a value
        # may hold one ("Ages Sp,1-3")
        head = [p.strip() for p in line.split(",", 2)]
        if len(head) < 2 or not head[0] or not head[1]:
            sys.exit(f"{where}: cannot parse {raw!r} "
                     f"(expected '<game>,<set name>[,box=U[/S]][,split=U[/S]]')")
        line_game, name = head[0], head[1]
        parts = head[:2] + [f.strip() for f in
                            re.split(r",(?=\s*[A-Za-z][A-Za-z0-9_]*\s*=)",
                                     head[2])] if len(head) > 2 else head
        if line_game.lower() != game.lower():
            continue
        if name.upper() == "(BLANK)":
            name = ""
        box, split, halves, side, plates = None, None, {}, None, []
        nsplits, logo, numbers = [], None, 0
        names, name_widths = [], []
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
            elif key == "side" and sep:
                side = value.strip()
                if not side:
                    sys.exit(f"{where}: side= needs a text value")
            elif key == "plate" and sep:
                title, tsep, width_list = value.partition(":")
                title, width_list = title.strip(), width_list.strip()
                if not tsep or not title or not width_list:
                    sys.exit(f"{where}: plate= must be "
                             f"'<title>:<w1>+<w2>+...', got {value!r}")
                try:
                    widths = [float(w) for w in width_list.split("+")]
                except ValueError:
                    sys.exit(f"{where}: bad width in plate={value!r}")
                if not widths or any(w <= 0 for w in widths):
                    sys.exit(f"{where}: plate= widths must be positive")
                plates.append((title, widths))
            elif key == "parts" and sep:
                # '#<tag>' qualifies the 3MF name, so two splits into the
                # SAME number of cascades can coexist
                before, hashed, tag = value.rpartition("#")
                if hashed and "@" in before:
                    value, tag = before, tag.strip()
                else:
                    tag = None
                widths_part, at, labels_part = value.partition("@")
                if not at:
                    sys.exit(f"{where}: parts= must be "
                             f"'<w1>+<w2>+...@<label1>|<label2>|...[#<tag>]', "
                             f"got {value!r}")
                widths = [parse_width(w, cfg["widths"], where, "parts")
                          for w in widths_part.split("+")]
                if not widths or any(w == 0 for w in widths):
                    sys.exit(f"{where}: parts= needs standard widths before '@'")
                labels = [t.strip() for t in labels_part.split("|")]
                if len(labels) < 2 or any(not t for t in labels):
                    sys.exit(f"{where}: parts= needs 2 or more non-empty labels")
                prof = parts_profile(labels, tag)
                if any(parts_profile(pl, pt) == prof
                       for _, pl, pt in nsplits):
                    # each grouping gets a 3MF named for its count and tag
                    sys.exit(f"{where}: two parts= groupings both named "
                             f"{prof!r}; give one a different #<tag>")
                nsplits.append((widths, labels, tag))
            elif key == "names" and sep:
                widths_part, at, labels_part = value.partition("@")
                if not at:
                    sys.exit(f"{where}: names= must be '<w1>+<w2>+...@"
                             f"<name1>[:<short>]|<name2>...', got {value!r}")
                name_widths = [parse_width(w, cfg["widths"], where, "names")
                               for w in widths_part.split("+")]
                if not name_widths or any(w == 0 for w in name_widths):
                    sys.exit(f"{where}: names= needs standard widths before '@'")
                for item in labels_part.split("|"):
                    full, _, short = item.partition(":")
                    full, short = full.strip(), short.strip()
                    if not full:
                        sys.exit(f"{where}: names= has an empty name")
                    if full.upper() == "(BLANK)":
                        full, short = "", ""
                    names.append((full, short))
                if len(names) < 2:
                    sys.exit(f"{where}: names= needs 2 or more names")
            elif key == "logo" and sep:
                logo = find_art_file(game, value.strip())
            elif key == "numbers" and sep:
                if not value.strip().isdigit() or int(value) < 1:
                    sys.exit(f"{where}: numbers= takes a count of 1 or more, "
                             f"got {value!r}")
                numbers = int(value)
            else:
                sys.exit(f"{where}: unknown field {field!r} (expected box=U[/S], "
                         f"split=U[/S], split1=/split2=, parts=<w>@<labels>, "
                         f"names=<w>@<names>, side=, plate=, logo= or "
                         f"numbers=)")
        if halves:
            if split is not None or set(halves) != {"split1", "split2"}:
                sys.exit(f"{where}: split1= and split2= must be given "
                         f"together (and not combined with split=)")
            split = [halves["split1"], halves["split2"]]
        if box is not None or split is not None or plates or nsplits or names:
            records.append({"name": name, "box": box, "split": split,
                            "side": side, "plates": plates, "nsplits": nsplits,
                            "logo": logo, "numbers": numbers,
                            "names": names, "name_widths": name_widths})
    return records


def staircase(size: float, steps: int) -> Polygon:
    s = size / steps
    pts = [(0.0, 0.0), (size, 0.0)]
    for i in range(steps):
        x, y = size - i * s, i * s
        pts += [(x, y + s), (x - s, y + s)]
    return Polygon(*pts, align=None)


class LabelFont:
    """Wraps Text() with empirical metrics (OCCT's baseline anchoring is
    font-dependent, so we probe it with a reference glyph)."""

    PROBE_SIZE = 100.0

    def __init__(self, font_path: str):
        self.font_path = font_path
        cap_box = self.render("H").bounding_box()
        self.cap = cap_box.size.Y
        self.baseline = cap_box.min.Y     # baseline in render() coordinates
        # deepest descender below the baseline (the deepest glyph in the font)
        self.descent = self.baseline - self.render("gjpqy").bounding_box().min.Y
        self.xheight = self.render("c").bounding_box().size.Y

    def render(self, txt: str):
        return Text(txt, font_size=self.PROBE_SIZE, font_path=self.font_path,
                    align=(Align.MIN, Align.NONE))


_MAIN_ROW_CACHE = {}


def art_main_row(art: Compound) -> Compound:
    """`art` cropped to its densest band and above: a device hung below the
    wordmark eats the height a box number needs."""
    if id(art) in _MAIN_ROW_CACHE:
        return _MAIN_ROW_CACHE[id(art)]
    bb = art.bounding_box()
    bands = 40
    step = bb.size.Y / bands
    ink = []
    for i in range(bands):
        strip = Rectangle(bb.size.X + 2, step, align=(Align.MIN, Align.MIN))
        strip = strip.translate(Vector(bb.min.X - 1, bb.min.Y + i * step, 0))
        area = 0.0
        for face in art.faces():
            overlap = face & strip
            if overlap is not None:
                area += overlap.area
        ink.append(area)
    peak = ink.index(max(ink))
    floor = peak
    while floor > 0 and ink[floor - 1] >= 0.25 * ink[peak]:
        floor -= 1
    cut = bb.min.Y + floor * step
    keep = Rectangle(bb.size.X + 2, bb.max.Y - cut + 1,
                     align=(Align.MIN, Align.MIN)).translate(
        Vector(bb.min.X - 1, cut, 0))
    faces = []
    for face in art.faces():
        overlap = face & keep
        if overlap is not None:
            faces += overlap.faces()
    cropped = Compound(children=faces)
    _MAIN_ROW_CACHE[id(art)] = cropped
    return cropped


def hits(shapes, box) -> bool:
    """Does any of `shapes` have ink inside the rectangle (x0, x1, y0, y1)?"""
    x0, x1, y0, y1 = box
    rect = Rectangle(x1 - x0, y1 - y0, align=(Align.MIN, Align.MIN)).translate(
        Vector(x0, y0, 0))
    for face in shapes.faces():
        bb = face.bounding_box()
        if bb.max.X < x0 or bb.min.X > x1 or bb.max.Y < y0 or bb.min.Y > y1:
            continue                       # bounding boxes miss: cheap reject
        overlap = face & rect               # None when they only touch
        if overlap is not None and overlap.area > 1e-6:
            return True
    return False


def fit_art(art: Compound, width: float, height: float, cc_left: float,
            group_w: float, group_h: float, keepouts: list):
    """Largest placement of `art` that puts no ink in a keep-out rectangle;
    the bounding box may overlap the staircase and the "cc" as long as no INK
    does, so boxes are tried largest first."""
    top = height - ART_MARGIN
    boxes = [(ART_MARGIN, width - ART_MARGIN, ART_MARGIN),         # whole label
             (MARGIN + LOGO_SIZE + TEXT_SIDE_GAP,                  # between the
              cc_left - TEXT_SIDE_GAP, ART_MARGIN),                #  two marks
             (ART_MARGIN, width - ART_MARGIN,                      # above them
              MARGIN + LOGO_SIZE + TEXT_GAP_ABOVE_LOGO)]
    for left, right, bottom in sorted(
            boxes, key=lambda b: -min((b[1] - b[0]) / group_w,
                                      (top - b[2]) / group_h)):
        if right <= left or top <= bottom:
            continue
        factor = min((right - left) / group_w, (top - bottom) / group_h)
        placed = scale(art, by=factor)
        bb = placed.bounding_box()
        placed = placed.translate(Vector(
            left + (right - left - group_w * factor) / 2 - bb.min.X,
            bottom + (top - bottom - group_h * factor) / 2 - bb.min.Y, 0))
        if not any(hits(placed, box) for box in keepouts):
            return placed, factor
    return None, 0.0


def art_placement(art: Compound, number: str, font: LabelFont, width: float,
                  height: float, cc_left: float):
    """Place game artwork, and any box number, on a label. A number goes
    beside the artwork where that costs it nothing (the front label), else
    underneath on the staircase's line, the artwork cropped to its wordmark;
    too narrow (20mm) and it goes beside, uncropped."""
    bb = art.bounding_box()
    art_w, art_h = bb.size.X, bb.size.Y          # artwork units
    marks = [(MARGIN - TEXT_SIDE_GAP, MARGIN + LOGO_SIZE + TEXT_SIDE_GAP,
              BOTTOM_CLEARANCE, MARGIN + LOGO_SIZE + TEXT_SIDE_GAP),
             (cc_left - TEXT_SIDE_GAP, width - MARGIN + TEXT_SIDE_GAP,
              BOTTOM_CLEARANCE, MARGIN + CC_XHEIGHT + TEXT_SIDE_GAP)]
    alone, alone_factor = fit_art(art, width, height, cc_left,
                                  art_w, art_h, marks)
    if not number:
        return [alone] if alone is not None else []

    num = font.render(number)
    num_ratio = num.bounding_box().size.X / font.cap     # width per cap height

    # beside the artwork: they scale together, so the number costs width only
    group_w = art_w + (ART_NUMBER_GAP + ART_NUMBER_CAP * num_ratio) * art_h
    beside, beside_factor = fit_art(art, width, height, cc_left,
                                    group_w, art_h, marks)

    def beside_shapes():
        """Artwork with the number to its right, cap on the label's centre."""
        scaled = scale(num, by=ART_NUMBER_CAP * art_h * beside_factor / font.cap)
        nb, ab = scaled.bounding_box(), beside.bounding_box()
        return [beside, scaled.translate(Vector(
            ab.max.X + ART_NUMBER_GAP * ab.size.Y - nb.min.X,
            (height - nb.size.Y) / 2 - nb.min.Y, 0))]

    if beside is not None and beside_factor >= alone_factor - 1e-9:
        return beside_shapes()

    # under the wordmark: a fixed-height number on the staircase's line
    left = MARGIN + LOGO_SIZE + TEXT_SIDE_GAP
    right = cc_left - TEXT_SIDE_GAP
    cap = min(NUMBER_BELOW_CAP, (right - left) / num_ratio)
    if cap >= NUMBER_MIN_CAP:
        under_number = scale(num, by=cap / font.cap)
        nb = under_number.bounding_box()
        under_number = under_number.translate(Vector(
            (left + right - nb.size.X) / 2 - nb.min.X, MARGIN - nb.min.Y, 0))
        nb = under_number.bounding_box()
        wordmark = art_main_row(art)
        wb = wordmark.bounding_box()
        under, _ = fit_art(
            wordmark, width, height, cc_left, wb.size.X, wb.size.Y,
            marks + [(nb.min.X - TEXT_SIDE_GAP, nb.max.X + TEXT_SIDE_GAP,
                      BOTTOM_CLEARANCE, nb.max.Y + TEXT_SIDE_GAP)])
        if under is not None:
            return [under, under_number]

    # stacked: no room beside the staircase (20mm), so wordmark and number
    # share the box above it
    box_left, box_right = ART_MARGIN, width - ART_MARGIN
    box_bottom = MARGIN + LOGO_SIZE + TEXT_GAP_ABOVE_LOGO
    box_top = height - ART_MARGIN
    cap = min(NUMBER_BELOW_CAP, (box_right - box_left) / num_ratio)
    wordmark = art_main_row(art)
    wb = wordmark.bounding_box()
    room = box_top - box_bottom - cap - TEXT_GAP_ABOVE_LOGO
    if cap >= NUMBER_MIN_CAP and room > 0:
        factor = min((box_right - box_left) / wb.size.X, room / wb.size.Y)
        stack = wb.size.Y * factor + TEXT_GAP_ABOVE_LOGO + cap
        bottom = box_bottom + (box_top - box_bottom - stack) / 2
        digit = scale(num, by=cap / font.cap)
        nb = digit.bounding_box()
        digit = digit.translate(Vector((width - nb.size.X) / 2 - nb.min.X,
                                       bottom - nb.min.Y, 0))
        placed = scale(wordmark, by=factor)
        ab = placed.bounding_box()
        placed = placed.translate(Vector(
            (width - ab.size.X) / 2 - ab.min.X,
            bottom + cap + TEXT_GAP_ABOVE_LOGO - ab.min.Y, 0))
        return [placed, digit]

    return beside_shapes() if beside is not None else []


def number_below(number: str, name: str, font: LabelFont, width: float,
                 height: float, cc_left: float, cap: float):
    """Set a box number under the name; returns (number shape, text floor). On
    the staircase's line, or its own line above it where the label is too
    narrow (20mm), the name's box floor rising to suit."""
    floor = MARGIN + LOGO_SIZE + TEXT_GAP_ABOVE_LOGO
    num = font.render(number)
    ratio = num.bounding_box().size.X / font.cap
    left, right = MARGIN + LOGO_SIZE + TEXT_SIDE_GAP, cc_left - TEXT_SIDE_GAP
    size = min(NUMBER_BELOW_CAP, (right - left) / ratio)
    if size >= NUMBER_MIN_CAP:
        digit = scale(num, by=size / font.cap)
        nb = digit.bounding_box()
        return digit.translate(Vector((left + right - nb.size.X) / 2 - nb.min.X,
                                      MARGIN - nb.min.Y, 0)), floor
    # its own line: the name keeps its height, the number takes the rest
    text_h = font.render(name).bounding_box().size.Y * cap / font.cap
    size = min(NUMBER_BELOW_CAP, (width - 2 * MARGIN) / ratio,
               height - TEXT_TOP_MARGIN - floor - text_h - TEXT_GAP_ABOVE_LOGO)
    if size < NUMBER_MIN_CAP:
        return None, floor
    digit = scale(num, by=size / font.cap)
    nb = digit.bounding_box()
    return (digit.translate(Vector((width - nb.size.X) / 2 - nb.min.X,
                                   floor - nb.min.Y, 0)),
            floor + size + TEXT_GAP_ABOVE_LOGO)


def text_lines(name: str):
    """The lines a name declares with LINE_BREAK; a plain name is one."""
    return [s.strip() for s in name.split(LINE_BREAK) if s.strip()] or [name]


def stack_metrics(lines, font: LabelFont):
    """The stack's lines and extents relative to the TOP baseline: (texts,
    widest, top, ink bottom, descender bottom)."""
    pitch = font.cap * (1 + LINE_GAP)
    texts = [font.render(line) for line in lines]
    boxes = [t.bounding_box() for t in texts]
    top = max(b.max.Y - font.baseline - i * pitch for i, b in enumerate(boxes))
    bottom = min(b.min.Y - font.baseline - i * pitch for i, b in enumerate(boxes))
    deepest = -(len(lines) - 1) * pitch - font.descent
    return texts, max(b.size.X for b in boxes), top, bottom, deepest


def fit_text(name: str, font: LabelFont, width: float, height: float,
             cc_left: float, cap: float, box_bottom: float, number: str):
    """Place a name's text, on one line or several, in the layout that renders
    it largest. STANDARD stands the stack on `box_bottom`, no taller than the
    width's `cap`; LOWERED drops it beside the logo and the cc, its deepest
    descender clearing the bottom margin — one line only at a BIG_CAPS width,
    and never with a box number, which wants that line."""
    box_left, box_right = MARGIN, width - MARGIN
    box_top = height - TEXT_TOP_MARGIN
    centre = (box_left + box_right) / 2
    gap = 2 * min(centre - (MARGIN + LOGO_SIZE + TEXT_SIDE_GAP),
                  cc_left - TEXT_SIDE_GAP - centre)
    lines = text_lines(name)
    texts, widest, top, bottom, deepest = stack_metrics(lines, font)
    factor = min((box_right - box_left) / widest,
                 (box_top - box_bottom) / (top - bottom))
    if cap is not None:
        factor = min(factor, cap / font.cap)
    floor = box_bottom
    big_cap = (BIG_CAPS.get(width) if len(lines) == 1 else cap) if not number else None
    if big_cap is not None:
        big = min(gap / widest, big_cap / font.cap,
                  (box_top - MARGIN) / (top - deepest))
        if big > factor:
            # a full-descender last line just touches the bottom margin
            factor, floor = big, MARGIN + (bottom - deepest) * big
    pitch = font.cap * (1 + LINE_GAP) * factor
    shapes = []
    for i, txt in enumerate(texts):
        txt = scale(txt, by=factor)
        bb = txt.bounding_box()
        # the top line's baseline lands `bottom` above the floor
        shapes.append(txt.translate(Vector(
            centre - bb.size.X / 2 - bb.min.X,
            floor - bottom * factor - font.baseline * factor - i * pitch, 0)))
    return shapes, factor * font.cap


def make_label(name: str, width: float, font: LabelFont, caps: dict = None,
               art: Compound = None, number: str = "", height: float = None):
    """Build one label: (base Solid (white), raised Compound (black)). `caps`
    maps width -> capital height (mm), else the text fills its box. `height`
    is LABEL_HEIGHT unless a game's holder is shorter (`GAMES[...]["height"]`)."""
    height = LABEL_HEIGHT if height is None else height
    z_top = Vector(0, 0, BASE_THICKNESS)

    base = extrude(Rectangle(width, height, align=(Align.MIN, Align.MIN)),
                   amount=BASE_THICKNESS, taper=TAPER)

    logo = staircase(LOGO_SIZE, LOGO_STEPS).translate(Vector(MARGIN, MARGIN, 0))
    raised = extrude(logo.translate(z_top), amount=RAISE_LOGO)

    cc = scale(font.render("cc"), by=CC_XHEIGHT / font.xheight)
    bb = cc.bounding_box()
    cc_left = width - MARGIN - bb.size.X
    cc = cc.translate(Vector(width - MARGIN - bb.max.X, MARGIN - bb.min.Y, 0))
    raised += extrude(cc.translate(z_top), amount=RAISE_LOGO)

    if art is not None:
        for shape in art_placement(art, number, font, width, height, cc_left):
            raised += extrude(shape.translate(z_top), amount=RAISE_TEXT)
    elif name:
        box_bottom = MARGIN + LOGO_SIZE + TEXT_GAP_ABOVE_LOGO
        cap = (caps or {}).get(width)
        if number:
            digit, box_bottom = number_below(number, name, font, width, height,
                                             cc_left, cap or LOGO_SIZE)
            if digit is not None:
                raised += extrude(digit.translate(z_top), amount=RAISE_TEXT)
        shapes, _ = fit_text(name, font, width, height, cc_left, cap,
                             box_bottom, number)
        for txt in shapes:
            raised += extrude(txt.translate(z_top), amount=RAISE_TEXT)

    # Normalise for export: a bare Solid for the base, one Compound for black.
    base_solid = base.solid()
    base_solid.color = BASE_COLOR
    base_solid.label = "base"
    raised_comp = Compound(raised.solids())
    low = raised_comp.bounding_box().min.Y
    if low < BOTTOM_CLEARANCE - 1e-6:        # the box pocket must stay clear
        sys.exit(f"{name or 'blank'} {width:g}mm: raised detail reaches "
                 f"{low:.2f}mm from the bottom edge, inside the "
                 f"{BOTTOM_CLEARANCE:g}mm pocket clearance")
    raised_comp.color = RAISED_COLOR
    raised_comp.label = "raised"
    return base_solid, raised_comp


def label_polygons(name: str, width: float, font: LabelFont, caps: dict = None,
                   art: Compound = None, number: str = "", segments: int = 10):
    """The label's raised detail as flat polygons, for previews: one entry per
    shape, largest first, each a list of rings in mm — what gets printed."""
    _, raised = make_label(name, width, font, caps, art, number)
    faces = [face for solid in raised.solids() for face in solid.faces()
             if face.bounding_box().size.Z < 1e-6
             and face.bounding_box().max.Z > BASE_THICKNESS + 1e-6]

    def ring(wire):
        points = []
        for edge in wire.order_edges():
            points += [tuple(edge @ (i / segments))[:2] for i in range(segments)]
        return points

    return [[ring(face.outer_wire())] + [ring(w) for w in face.inner_wires()]
            for face in sorted(faces, key=lambda f: -f.area)]


def add_mesh_object(mesher: Mesher, shape, part_number: str):
    """Mesh `shape` into the 3MF as ONE object and return the lib3mf object.
    Mesher.add_shape() splits a Compound into one object per solid and loses
    the per-shape colour, so slicers would see every letter as a separate
    part; this is its body (build123d 0.11) without the flattening.
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
    """Bambu Studio / OrcaSlicer project metadata: each part to a filament
    slot, each instance to a plate. This is what makes the file open
    two-coloured — Bambu ignores 3MF material colours."""
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
    """Rewrite the 3MF zip with the Metadata/*.config files, so Bambu Studio
    sees a project."""
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
    """Export base + raised as ONE 3MF object of two parts (raised->1)."""
    m = Mesher()
    assembly, entry = add_assembled_label(m, name, base, raised)
    m.model.AddBuildItem(assembly, m.wrapper.GetIdentityTransform())
    m.write(str(path))
    if bambu:
        inject_bambu_metadata(path, [entry], [
            {"name": name, "instances": [(entry["id"], 100 + entry["id"])]}])


# --plates: one Bambu multi-plate project with every label laid out


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
    """One set's labels as rows of widths (next-fit), identical for every set,
    shortest row at the bottom to clear the no-print corner."""
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
    """Place one block per set, bottom-up, plate by plate, every block of a
    game identical: the bottom row is indented past the no-print corner when
    it fits, else the block starts above it. Returns (placements, plates)."""
    indent = max(PLATE_MARGIN, PLATE_EXCLUDE[0] + LABEL_GAP)
    placements = []
    plate, y = 0, PLATE_MARGIN
    for display, labels in sets:
        widths = [w for _, w in labels]
        text_of = {w: t for t, w in labels}   # widths are unique per set
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
                placements.append((plate, x, row_y, text_of[width], display, width))
                x += width + LABEL_GAP
        y = start + height + SET_GAP
    return placements, plate + 1


def render_project_settings(n_plates: int):
    """Bambu printer/filament profile, one wipe tower position per plate."""
    template = Path(__file__).resolve().parent / PROJECT_SETTINGS_FILE
    if not template.is_file():
        print(f"warning: {PROJECT_SETTINGS_FILE} not found - the combined "
              "file will open without printer/filament profile")
        return None
    settings = json.loads(template.read_text(encoding="utf-8"))
    settings["wipe_tower_x"] = [str(WIPE_TOWER_XY[0])] * n_plates
    settings["wipe_tower_y"] = [str(WIPE_TOWER_XY[1])] * n_plates
    return json.dumps(settings, indent=4)


def parts_profile(labels, tag=None) -> str:
    """The 3MF a parts= grouping goes in: '<tag> Cascades' with a #<tag>, else
    '<part count> Cascades'. A tag is needed because the useful number — AGES
    per cascade — cannot be derived; counting labels gives BOXES, which reads
    as its opposite."""
    return f"{tag} Cascades" if tag else f"{len(labels)} Cascades"


def part_text(name: str, label: str, is_front: bool) -> str:
    """The text a parts= label prints: the set name and the label on the front
    (unless the label is stacked or starts with the name); on a side, the
    label with its ", " list stacked."""
    if not is_front:
        return label.replace(", ", LINE_BREAK)
    if LINE_BREAK in label or re.match(rf"{re.escape(name)}(?:$|,)", label):
        return label
    return f"{name} {label}"


def set_plate_specs(record: dict, cfg: dict) -> list:
    """Plates for one set's own 3MF, from its cc.cfg record: single cascade
    (unsleeved), single cascade (sleeved), split cascade (both) — collapsing
    pairs of the same widths — plus one plate per width per parts= grouping,
    one per names= entry holding every width, and the rest as spares.

    Returns {profile: [(plate name, labels), ...]}, one profile per 3MF: ""
    for the set's own file, "<n> Cascades" per parts= grouping (which replaces
    it and repeats the shared plates, so each is a complete print), and "Logo"
    for artwork. A label is (name, width, artwork | None, number)."""
    name = record["name"]
    display = name or "Blank"
    front = cfg.get("front")
    UNSLEEVED, SLEEVED = 0, 1
    TAG = {UNSLEEVED: "U", SLEEVED: "S"}
    SUFFIX = {UNSLEEVED: "-Un", SLEEVED: "-Sl"}

    side_base = record.get("side") or name   # short text for side labels

    def box_labels(front_text, side_text, side_width):
        labels = [(front_text, front, None)] if front else []
        if side_width and side_width != front:   # width 0 = no side label
            labels.append((side_text, side_width, None))
        return labels

    def boxes_title(entries, sleeving=None):
        """' 560 Card-U (...)'. A "/" is illegal in a plate name."""
        tag = f"-{TAG[sleeving]}" if sleeving is not None else ""
        model_suffix = SUFFIX[sleeving] if sleeving is not None else ""
        parts, seen = [], set()
        for info, width in entries:
            if not info or (info, width) in seen:
                continue
            seen.add((info, width))
            box_name, base_model = info
            model = f"{base_model}.{width:g}".replace("/", "-")
            parts.append(f"{box_name}{tag} ({model}{model_suffix})")
        if not parts:
            return tag
        return " " + "; ".join(parts)

    specs = []
    if record["box"]:
        info = record["box"]["info"]
        widths = record["box"]["widths"]
        plates = [
            (f"{display}{boxes_title([(info, widths[s])], s)}",
             box_labels(name, side_base, widths[s]))
            for s in (UNSLEEVED, SLEEVED)]
        if plates[0][1] == plates[1][1]:
            plates = [(f"{display}{boxes_title([(info, widths[UNSLEEVED])])}",
                       plates[0][1])]
        specs += plates
    if record["split"]:
        def split_labels(sleeving):
            labels = []
            for half_no, half in enumerate(record["split"], 1):
                labels += box_labels(f"{name} {half_no}", f"{side_base} {half_no}",
                                     half["widths"][sleeving])
            return labels
        def split_entries(sleeving):
            return [(half["info"], half["widths"][sleeving])
                    for half in record["split"]]
        plates = [
            (f"{display} split{boxes_title(split_entries(s), s)}", split_labels(s))
            for s in (UNSLEEVED, SLEEVED)]
        if plates[0][1] == plates[1][1]:
            plates = [(f"{display} split{boxes_title(split_entries(UNSLEEVED))}",
                       plates[0][1])]
        specs += plates
    # names=: one plate per NAME, each holding every width — the TRANSPOSE of
    # parts=. The short form goes on the NARROWEST width only, where a long
    # name is otherwise unprintable (1.61 mm capitals on a 20 mm label).
    name_widths = record.get("name_widths", [])
    narrowest = min(name_widths) if name_widths else None
    short_at = narrowest if narrowest != front else None
    for full, short in record.get("names", []):
        specs.append((full or "Blank",
                      [((short or full) if w == short_at else full, w, None)
                       for w in name_widths]))

    # Each parts= grouping is a separate print — three cascades or four, never
    # both — so it becomes a profile of its own, in cc.cfg order, with the
    # shared plates repeated.
    parts_at = len(specs)
    parts_groups = []
    for widths, labels, group_tag in record.get("nsplits", []):
        # one plate per width; the front prefixes the set name unless the
        # label is stacked or already starts with it
        plates = []
        for w in widths:
            wtag = "front" if w == front else f"{w:g}mm"
            rows = [(part_text(name, lab, w == front), w, None)
                    for lab in labels]
            plates.append((f"{display} {wtag} {len(labels)}-part", rows))
        parts_groups.append((parts_profile(labels, group_tag), plates))
    logo = record.get("logo")
    numbers = [""] + [str(i) for i in range(1, record.get("numbers", 0) + 1)]
    art_specs = []
    for title, widths in record.get("plates", []):
        title = title.replace("/", "-")
        for n in numbers:      # artwork instead of the name, in its own file
            if logo is None:
                break
            art_specs.append((f"{title} with logo{' ' + n if n else ''}",
                              [("", w, logo, n) for w in widths]))
        for n in numbers:
            # narrower labels have no room for "<name> <n>", so the number
            # goes on its own line
            specs.append((
                f"{title}{f' {n}' if n else ''}",
                [(f"{name} {n}".strip(), w, None, "") if w == front else
                 (side_base, w, None, n) for w in widths]))
    spares = []
    if record["box"]:
        used = {front, *record["box"]["widths"]}
        spares += [(side_base, w, None) for w in cfg["widths"] if w not in used]
    if record["split"]:
        for half_no, half in enumerate(record["split"], 1):
            used = {front, *half["widths"]}
            spares += [(f"{side_base} {half_no}", w, None)
                       for w in cfg["split_widths"] if w not in used]
    if spares:
        specs.append((f"{display} spares", spares))
    files = {prof: specs[:parts_at] + plates + specs[parts_at:]
             for prof, plates in parts_groups} or {"": specs}
    if art_specs:
        files["Logo"] = art_specs
    return files


PROJECT_PLATE_ROWS = 7    # rows a centred stack can hold below the wipe tower


def write_project_3mf(path: Path, plate_specs, font: LabelFont, caps: dict = None):
    """Write a Bambu project of fixed composition: one plate per (plate name,
    labels) spec, labels one per row below the wipe tower strip, overflowing
    past PROJECT_PLATE_ROWS."""
    pitch = LABEL_HEIGHT + LABEL_GAP
    expanded = []
    for plate_name, labels in plate_specs:
        rows = [[label] for label in labels]
        chunks = [rows[i:i + PROJECT_PLATE_ROWS]
                  for i in range(0, len(rows), PROJECT_PLATE_ROWS)]
        for chunk_no, chunk in enumerate(chunks, 1):
            title = plate_name if chunk_no == 1 else f"{plate_name} ({chunk_no})"
            expanded.append((title, chunk))

    n_plates = len(expanded)
    cols = plate_columns(n_plates)
    m = Mesher()
    objects, plates = [], []
    identify_id = 200
    for plate_no, (plate_name, rows) in enumerate(expanded):
        origin_x = (plate_no % cols) * PLATE_STRIDE
        origin_y = -(plate_no // cols) * PLATE_STRIDE
        plate = {"name": plate_name, "instances": []}
        stack_height = len(rows) * pitch - LABEL_GAP
        y_bottom = min((PLATE_SIZE - stack_height) / 2,
                       PLATE_TOP_LIMIT - stack_height)
        y_bottom = max(PLATE_MARGIN, y_bottom)
        for i, row in enumerate(rows):
            row_w = sum(e[1] for e in row) + LABEL_GAP * (len(row) - 1)
            x = (PLATE_SIZE - row_w) / 2
            y = y_bottom + (len(rows) - 1 - i) * pitch
            for entry_spec in row:
                label_name, width = entry_spec[0], entry_spec[1]
                art_file = entry_spec[2] if len(entry_spec) > 2 else None
                number = entry_spec[3] if len(entry_spec) > 3 else ""
                art = load_art(art_file) if art_file else None
                base, raised = make_label(label_name, width, font, caps, art,
                                          number)
                stem = " ".join(p for p in ("Logo" if art else "",
                                            label_name, number) if p)
                stem = f"{safe_filename(stem)}_{width:g}mm"
                assembly, entry = add_assembled_label(m, stem, base, raised)
                m.model.AddBuildItem(assembly,
                                     translation(m, origin_x + x, origin_y + y))
                objects.append(entry)
                plate["instances"].append((entry["id"], identify_id))
                identify_id += 1
                x += width + LABEL_GAP
        plates.append(plate)
    m.write(str(path))
    inject_bambu_metadata(path, objects, plates,
                          project_settings=render_project_settings(n_plates))
    print(f"  {path}: {len(objects)} labels on {n_plates} plates")


def write_plates_3mf(path: Path, sets, font: LabelFont, caps: dict = None):
    """Write labels into one Bambu project 3MF across plates: a block of rows
    per set, SET_GAP between blocks, wipe tower in the free top strip, plates
    in BambuStudio's grid (stride 1.2 x plate size)."""
    placements, n_plates = layout_sets(sets)
    cols = plate_columns(n_plates)

    m = Mesher()
    objects = []
    plates = [{"name": "", "instances": [], "sets": []} for _ in range(n_plates)]
    identify_id = 200
    for plate_no, x, y, text, display, width in placements:
        origin_x = (plate_no % cols) * PLATE_STRIDE
        origin_y = -(plate_no // cols) * PLATE_STRIDE
        base, raised = make_label(text, width, font, caps)
        stem = f"{safe_filename(text)}_{width:g}mm"
        assembly, entry = add_assembled_label(m, stem, base, raised)
        m.model.AddBuildItem(assembly, translation(m, origin_x + x, origin_y + y))
        objects.append(entry)
        plate = plates[plate_no]
        plate["instances"].append((entry["id"], identify_id))
        identify_id += 1
        if display not in plate["sets"]:
            plate["sets"].append(display)
        print(f"  plate {plate_no + 1}: {text or '(blank)'} {width:g}mm "
              f"@ ({x:g}, {y:g})")
    for plate in plates:
        # "/" (e.g. from "Innovation 1/3") is illegal in Bambu plate names.
        plate["name"] = ", ".join(plate["sets"]).replace("/", "-")
    m.write(str(path))
    inject_bambu_metadata(path, objects, plates,
                          project_settings=render_project_settings(n_plates))
    print(f"{path}: {len(objects)} labels on {n_plates} plates")


def label_file_name(record: dict, profile: str = "", suffix: str = ".3mf") -> str:
    """'<set> Labels.3mf', or '<set> <profile> Labels.3mf'."""
    name = f"{record['name'] or 'Blank'}{' ' + profile if profile else ''}"
    return "".join(c if c not in '\\/:*?"<>|' else "_"
                   for c in f"{name} Labels{suffix}")


def safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name) or "Blank"


def main():
    ap = argparse.ArgumentParser(description="Generate board game box labels")
    ap.add_argument("--game", default="Dominion",
                    help=f"game to generate labels for ({', '.join(GAMES)})")
    ap.add_argument("--names", help="comma-separated set names (default: cc.cfg)")
    ap.add_argument("--widths", help="comma-separated widths in mm "
                                     "(default: the game's width lists)")
    ap.add_argument("--step", action="store_true", help="also export STEP files")
    ap.add_argument("--no-blank", action="store_true", help="skip the blank label")
    ap.add_argument("--plain", action="store_true",
                    help="vanilla 3MF without Bambu Studio filament metadata")
    ap.add_argument("--plates", action="store_true",
                    help="write one multi-plate Bambu project 3MF "
                         "instead of the default per-set files")
    ap.add_argument("--individual", action="store_true",
                    help="write one 3MF per individual label instead of the "
                         "default per-set files")
    ap.add_argument("--version", default="6.5",
                    help="project version (default 6.5); no longer embedded "
                         "in file names, kept for reference")
    args = ap.parse_args()

    game = next((g for g in GAMES if g.lower() == args.game.lower()), None)
    if game is None:
        sys.exit(f"unknown game {args.game!r} (known: {', '.join(GAMES)})")
    cfg = GAMES[game]
    # A game whose holder is shorter makes every label, plate and pitch this
    # height; the layout functions read the module value.
    global LABEL_HEIGHT
    LABEL_HEIGHT = cfg.get("height", LABEL_HEIGHT)

    # entries: (front label text, side label text, is_split)
    records = None
    if args.names:
        entries = [(n.strip(), n.strip(), False) for n in args.names.split(",")]
    else:
        config_file = find_config_file()
        if config_file:
            records = read_config_file(config_file, game)
            entries = []
            for rec in records:
                side_base = rec["side"] or rec["name"]
                if rec["box"] is not None:
                    entries.append((rec["name"], side_base, False))
                if rec["split"]:
                    entries += [(f"{rec['name']} 1", f"{side_base} 1", True),
                                (f"{rec['name']} 2", f"{side_base} 2", True)]
                for _, labels, _ in rec.get("nsplits", []):
                    entries += [(f"{rec['name']} {lab}", lab, True)
                                for lab in labels]
        else:
            entries = [(n, n, False) for n in NAMES]
    if not args.no_blank and not any(f == "" for f, _, _ in entries):
        entries.append(("", "", False))     # blank label: logo + cc, no name

    override = [float(w) for w in args.widths.split(",")] if args.widths else None
    front = cfg.get("front")
    def widths_for(is_split):
        return override or cfg["split_widths" if is_split else "widths"]
    def label_list(front_text, side_text, widths):
        return [(front_text if w == front else side_text, w) for w in widths]
    labels = [label
              for front_text, side_text, is_split in entries
              for label in label_list(front_text, side_text,
                                      widths_for(is_split))]

    font = LabelFont(find_font())
    outdir = Path("cascades") / game / "labels"
    outdir.mkdir(parents=True, exist_ok=True)

    if not args.plates and not args.individual and records is not None:
        # default: one 3MF per set, and a second for its logo labels
        setdir = outdir
        setdir.mkdir(parents=True, exist_ok=True)
        for rec in records:
            for profile, specs in set_plate_specs(rec, cfg).items():
                if not specs:
                    continue
                write_project_3mf(setdir / label_file_name(rec, profile),
                                  specs, font, cfg["caps"])
        print("done")
        return

    if args.plates:
        # whole sets and split-box labels as separate projects for overview
        main_sets = [(f or "Blank", label_list(f, s, widths_for(False)))
                     for f, s, is_split in entries if not is_split]
        split_sets = [(f, label_list(f, s, widths_for(True)))
                      for f, s, is_split in entries if is_split]
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
