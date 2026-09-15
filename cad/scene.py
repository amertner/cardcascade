"""The poster scene of one cascade: the play-state assembly, DRESSED.

    .venv/bin/python -m cad.scene --model L5.7.7.45-Sl
    .venv/bin/python -m cad.scene --model S5.15.15.62-Sl --glb tmp/scene.glb

`cad.assemble --cards` shows the MECHANISM with numbered stacks; a poster
wants the cascade as Allan photographs it. This takes `cad.assemble`'s
assembly and adds what a photo has (`posters.json`, `render`): a LID COLOUR
per row with its inlays contrasting, a slide-in LABEL in the front holder,
CARD STACKS named and coloured per stack, and stacks under a topper CLIPPED to
its underside. It writes the poster 3MF and the `.glb` for
`render/cascade.py`, every colour decided HERE.
"""
import argparse
import json
import sys
from pathlib import Path

from . import assemble as AS, assembly as A, build as B, cascade as CC, gltf as G, mesh3mf
from .parts import box as box_part
from .revisions import CURRENT, RELEASES

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "posters.json"
WHITE, BLACK = "#F4F4F2", "#1B1B1B"
TEXT_MARGIN = 1.500        # a stack's name keeps this clear of the slot's sides
CLIP_UNDER_TOPPER = 0.500  # a riser stack stops this far below its topper's top edge
TOPPER_BAR = 5.000         # the topper's name bar: a stack's numeral sits below it


class Refused(Exception):
    pass


def load_spec(path=SPEC):
    with open(path) as f:
        return json.load(f)


def render_spec(spec, row, d):
    out = dict(spec.get("render", {}).get("games", {}).get(d.GameName, {}))
    rows = spec.get("render", {}).get("rows", {})
    for k in _row_keys(row, d):
        if k in rows:
            out.update(rows[k])
    out.setdefault("palette", spec.get("render", {}).get("palette", [WHITE]))
    out.setdefault("stacks", spec.get("render", {}).get("stacks", True))
    return out


def _row_keys(row, d):
    keys = [f"{d.GameName}/{(row.get('Short name') or '').strip()}"]
    label = (row.get("Project label") or "").strip()
    if label:
        keys.append(f"{d.GameName}/{label}")
    return keys


def luminance(hex_colour):
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def is_dark(hex_colour):
    return luminance(hex_colour) < 0.5


def lid_colour(rs, row, d, rows_in_game):
    """The row's lid: its own `lid` if the spec says, else the game's palette
    entry for its position."""
    if rs.get("lid"):
        return rs["lid"]
    palette = rs["palette"]
    key = (row.get("Short name") or "").strip()
    names = []
    for r in rows_in_game:
        n = (r.get("Short name") or "").strip()
        if n not in names:
            names.append(n)
    return palette[names.index(key) % len(palette)]


def scene_colours(lid, stacks):
    inlay = WHITE if is_dark(lid) else BLACK
    label_text = BLACK if not is_dark(lid) else lid
    parts = {"Lid": lid, "Lid Part": inlay, "Label": WHITE, "Label Part": label_text,
             "Topper": WHITE, "Topper Part": BLACK}
    for i, s in enumerate(stacks):
        parts[f"Cards {i} "] = s["colour"]
        parts[f"Cards Label {i} "] = WHITE if is_dark(s["colour"]) else BLACK
    return parts


def slots_row_major(d):
    """Every card slot front row first, left to right, as a photographed
    cascade reads; `assembly.card_slots` is column-major."""
    columns = [A.card_column(d, k) for k in range(d.HorizontalSlots)]
    depth = max(len(c) for c in columns)
    out = []
    for r in range(depth):
        for k, col in enumerate(columns):
            # a column without a front pocket (a mat slot) starts a row late
            i = r - (depth - len(col))
            if 0 <= i < len(col):
                riser, cap = col[i]
                out.append(((riser, k), cap))
    return out


def card_plan(d, rs):
    """`[{"slot", "text", "count", "colour"}]` — one entry per filled slot. An
    Innovation row with `columns` puts age `columns[k]` in column k, its slots
    front to back the `expansions` order; any other row fills from the game's
    `cards` list row by row, cycling if it runs short. `stacks: false` leaves
    every slot empty."""
    game = d.GameName
    if not rs.get("stacks", True):
        return []                        # render.stacks false: the cascade empty
    if game == "Innovation" and rs.get("columns"):
        cols = [str(c) for c in rs["columns"]]
        if len(cols) != d.HorizontalSlots:
            raise Refused(f"{d.calModelName} has {d.HorizontalSlots} columns; "
                          f"render.columns names {len(cols)}: {cols}")
        exps = rs.get("expansions") or ["Innovation", "Unseen", "Echoes", "Figures",
                                         "Artifacts", "Cities"]
        out = []
        for k, age in enumerate(cols):
            for i, (riser, cap) in enumerate(A.card_column(d, k)):
                exp = exps[i % len(exps)]
                size = 16 if age in ("A", "1") else 10
                out.append({"slot": (riser, k), "text": age, "count": min(size, cap),
                            "colour": G.CARD_COLOURS.get(exp, G.CARD_NEUTRAL),
                            "expansion": exp})
        return out
    if game == "Innovation":
        return [{"slot": slot, "text": A.card_set_label(n), "count": count,
                 "colour": G.CARD_COLOURS.get(name, G.CARD_NEUTRAL), "expansion": name}
                for slot, name, n, count in A.card_fill(d, rs.get("sets"))]
    cards = rs.get("cards")
    if not cards:
        raise Refused(f"no render.cards list for {game} in posters.json")
    out = []
    for i, (slot, cap) in enumerate(slots_row_major(d)):
        name, colour = cards[i % len(cards)]
        riser, _k = slot
        count = d.FrontPocketCardCapacity if riser is None else d.CardsPerSlidingSlot
        out.append({"slot": slot, "text": name, "count": min(count, cap), "colour": colour})
    return out


def topper_order(d, rs):
    """The expansion per riser, `j = 0` the BACK one, matching `card_plan`'s
    columns. Without `columns`, `cad.assemble`'s order."""
    if d.GameName != "Innovation" or not rs.get("columns"):
        return AS.TOPPERS
    exps = rs.get("expansions") or ["Innovation", "Unseen", "Echoes", "Figures",
                                     "Artifacts", "Cities"]
    risers = [exp for exp in exps[1:] if exp in AS.TOPPERS]   # the pocket's has none
    n = d.RisingSliders
    order = []
    for j in range(n):
        # riser j counts from the back; the front riser (j = n-1) is exps[1]
        i = n - 1 - j
        order.append(risers[i] if i < len(risers) else "Blank")
    return tuple(order)


def label_text(rs, row, d):
    if rs.get("label") is not None:
        return rs["label"]
    game = d.GameName
    if game == "Innovation":
        cols = [str(c) for c in rs.get("columns", [])]
        ages = [c for c in cols if c.isdigit()]
        if ages:
            return f"Innovation Ages {ages[0]}-{ages[-1]}"
        return "Innovation"
    if game == "FCM":
        return "Food Chain Magnate 1"
    if game == "Compile":
        return ""                                   # the logo label
    sets = (row.get("Set/Extension") or "").strip()
    first = sets.split(",")[0].strip()
    return first if first and len(first) < 24 else game


def label_shapes(rs, row, d):
    import labelmaker as LM
    font = LM.LabelFont(LM.find_font())
    width = A.label_width(d)
    game_key = "FCM" if d.GameName == "FCM" else d.GameName
    caps = LM.GAMES[game_key]["caps"]
    art = None
    if rs.get("label_logo"):
        art = LM.load_art(LM.find_art_file(d.GameName, rs["label_logo"]))
    base, raised = LM.make_label(label_text(rs, row, d), width, font, caps, art)
    loc = A.label_plate(d).location()
    return [("Label", base.moved(loc)), ("Label Part 2", raised.moved(loc))]


def topper_tops(d, parts, instances):
    import numpy as np
    out = {}
    risers = list(AS.topper_risers(d, True))
    topper_parts = [i for i, (n, _m) in enumerate(parts) if n == "Topper"]
    for (j, _first), i in zip(risers, topper_parts):
        verts, _tris = parts[i][1]
        pl = next(pl for pi, pl in instances if pi == i)
        v = np.asarray(verts, dtype=float)
        placed = np.stack([pl(p) for p in v]) if len(v) < 4 else np.column_stack([
            pl.origin[i] + v[:, 0] * pl.x_dir[i] + v[:, 1] * pl.y_dir[i] + v[:, 2] * pl.z_dir[i]
            for i in range(3)])
        # The cards stand INSIDE the pocket behind the topper, so a stack must
        # not stand proud of the topper's top edge.
        out[j] = float(placed[:, 2].max())
    return out


def stack_shapes(d, stacks, undersides):
    """`[(name, shape)]`: a box per stack and its name on the front face,
    `Cards <i>` / `Cards Label <i>`, which `scene_colours` keys on."""
    from build123d import Axis, Box, Location
    from . import text as T
    from .geom import text_solid

    out = []
    cap0 = A.card_label_cap(d)
    for i, s in enumerate(stacks):
        riser, k = s["slot"]
        x0, x1, y0, y1, z0, z1 = A.card_stack(d, s["slot"], s["count"], A.PLAY)
        drop = AS.CARD_LABEL_DROP
        cap = min(cap0, (z1 - z0) * 0.6)
        if riser is not None and riser in undersides:
            z1 = min(z1, undersides[riser] - CLIP_UNDER_TOPPER)
            # the numeral starts below this topper's name bar and may run a
            # little under the holder in front, as in a photo
            drop += TOPPER_BAR
        if z1 - z0 < 2.0:
            continue
        stack = Box(x1 - x0, y1 - y0, z1 - z0).moved(
            Location(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)))
        out.append((f"Cards {i} {s['text']}", stack))
        txt = str(s["text"]).upper() if len(str(s["text"])) > 2 else str(s["text"])
        size = cap / T.CAP
        adv, _lsb, _lo, _hi = T.metrics(txt, T.LOGO_FONT)
        room = (x1 - x0) - 2 * TEXT_MARGIN
        if adv * size > room:
            size = room / adv
            cap = size * T.CAP
        glyph = text_solid(txt, T.LOGO_FONT, size, AS.CARD_LABEL_PROUD)
        glyph = glyph.rotate(Axis.X, 90).moved(Location((
            (x0 + x1) / 2 - adv * size / 2, y0, z1 - drop - cap)))
        out.append((f"Cards Label {i} {s['text']}", glyph))
    return out


def build_scene(row, d, spec, rows_in_game, out_dir=ROOT / "build"):
    rs = render_spec(spec, row, d)
    toppers = B.ships_toppers(row, d)
    parts, instances = AS.assemble(d, A.PLAY, d.GameName, out_dir, toppers=toppers,
                                   topper_order=topper_order(d, rs))
    undersides = topper_tops(d, parts, instances) if toppers else {}
    stacks = card_plan(d, rs)
    for name, shape in stack_shapes(d, stacks, undersides) + label_shapes(rs, row, d):
        parts.append((name, shape))
        instances.append((len(parts) - 1, A.Place()))
    lid = lid_colour(rs, row, d, rows_in_game)
    return parts, instances, scene_colours(lid, stacks), stacks


def write_scene(row, d, spec, rows_in_game, out_dir=ROOT / "build", glb=None):
    parts, instances, colours, _stacks = build_scene(row, d, spec, rows_in_game, out_dir)
    stem = B.model_stem(d.calModelName)
    path = out_dir / "assemblies" / d.GameName / f"{stem} poster.3mf"
    mesh3mf.write_assembly(path, parts, instances, name=f"{stem} poster")
    objects = mesh3mf.read_assembly(path)
    glb = glb or path.with_suffix(".glb")
    G.write(glb, objects, (WHITE, BLACK), colours)
    return path, glb


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="a model code, e.g. L5.7.7.45-Sl")
    ap.add_argument("--spec", type=Path, default=SPEC)
    ap.add_argument("--csv", type=Path, default=CC.CSV)
    ap.add_argument("--out", type=Path, default=ROOT / "build")
    ap.add_argument("--glb", type=Path, help="default: beside the poster 3MF")
    ap.add_argument("--version", default=CURRENT, choices=RELEASES)
    args = ap.parse_args(argv)
    spec = load_spec(args.spec)
    rows = CC.catalogue(args.csv, None, args.model, None, None, None, args.version)
    rows = [(r, d) for r, d in rows if B.model_stem(d.calModelName).lower()
            == B.model_stem(args.model).lower()]
    if len(rows) != 1:
        print(f"--model {args.model} picks {len(rows)} cascades; it must pick one")
        return 2
    row, d = rows[0]
    game_rows = [r for r, _d in CC.catalogue(args.csv, d.GameName, None, None, None, None,
                                              args.version)]
    try:
        path, glb = write_scene(row, d, spec, game_rows, args.out, args.glb)
    except Refused as e:
        print(f"refused: {e}")
        return 1
    print(f"  {path}\n  {glb}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
