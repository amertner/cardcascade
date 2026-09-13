#!/usr/bin/env python3
"""The description poster for every cascade: the 4000x3000 PNG MakerWorld
shows beside a project, generated from the same parts.csv row the project
is built from.

    .venv/bin/python make_posters.py                      # every cascade
    .venv/bin/python make_posters.py --game Dominion --name 246
    .venv/bin/python make_posters.py --model S5.10.10.32-Un --render
    .venv/bin/python make_posters.py --list

Every number on a poster comes from the CAD (`cad.cascade.catalogue` picks
the rows; `values()` reads the `Derived`): the model code, the card count,
the closed cascade's size, the slot sizes. What the CAD does not know — the
big-stat captions, the cell captions, the expansion band, which photo — is
`posters.json`, and so is the LAYOUT: every element's box, face and size,
so a design change is an edit to the spec and not to this file. This file
only interprets the spec; the drawing primitives are `postercommon`.

The picture is resolved in this order (`picture_for`):
  1. `photos/<Game>/<Short name> <Sleeved|Unsleeved>.<png|jpg|jpeg>`
  2. `photos/<Game>/<Short name>.<png|jpg|jpeg>` (one photo for both sleevings)
  3. the row's `photo` entry in the spec (any path — this is how a sleeved
     photo serves its unsleeved twin without a copy; `[path, threshold]`
     tunes the knockout)
  4. a cached render under `build/posters/<Game>/`
  5. with --render, a fresh render: `cad.scene` (the play-state assembly
     dressed with a lid colour, a front label and the game's cards) then
     Blender on render/cascade.py --transparent
  6. a grey placeholder saying so, never a refusal.
A photo with real transparency is used as it is; one on a plain white
background is knocked out (`knockout`).

Posters go beside the projects: `build/cascades/<Game>/<tracked name>.png`
(`cad.cascade.filename` with .png), and reach `cascades/` with a release.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))
import postercommon as PC                                            # noqa: E402
from cad import assembly as A, build as B, cascade as CC, derive as D  # noqa: E402
from cad.parts import box as BOX, lid as LID                         # noqa: E402
from cad.revisions import CURRENT, RELEASES                          # noqa: E402

W, H = 4000, 3000
SPEC = REPO / "posters.json"
PHOTOS = REPO / "photos"
GLYPHS = REPO / "logos" / "Dominion" / "sets"
RENDERS = REPO / "build" / "posters"
BLENDER = next((p for p in ("/opt/homebrew/bin/blender",
                            "/Applications/Blender.app/Contents/MacOS/Blender")
                if os.path.exists(p)), "blender")
PLACEHOLDER = (205, 203, 198)


class Refused(Exception):
    pass


# ---------- the spec ----------
def load_spec(path=SPEC):
    with open(path) as f:
        return json.load(f)


def row_keys(row, d):
    """The spec keys this row answers to: `<Game>/<Short name>` and, where
    the row has one, `<Game>/<Project label>` (FCM's names)."""
    keys = [f"{d.GameName}/{(row.get('Short name') or '').strip()}"]
    label = (row.get("Project label") or "").strip()
    if label:
        keys.append(f"{d.GameName}/{label}")
    return keys


def spec_for(spec, row, d):
    """The merged spec for one cascade: defaults, then the game, then the
    row. `layout` merges per element name; `hide` accumulates."""
    game = spec.get("games", {}).get(d.GameName, {})
    rows = spec.get("rows", {})
    r = {}
    for k in row_keys(row, d):
        if k in rows:
            r = rows[k]
    merged = {"cells": spec.get("cells_default", []), "stats": [], "hide": []}
    layout = {e["name"]: dict(e) for e in spec.get("layout", [])}
    order = [e["name"] for e in spec.get("layout", [])]
    for layer in (game, r):
        for k, v in layer.items():
            if k == "layout":
                for name, over in v.items():
                    if name not in layout:
                        raise Refused(f"layout override for unknown element {name!r}")
                    layout[name].update(over)
            elif k == "hide":
                merged["hide"] = list(merged["hide"]) + list(v)
            else:
                merged[k] = v
    merged["layout"] = [layout[n] for n in order if n not in merged["hide"]]
    merged["printer_phrases"] = spec.get("printer", {})
    merged["colours"] = spec.get("colours", {})
    merged["size_decimals"] = spec.get("size_decimals", [0, 1, 1])
    return merged


def fmt_num(x, decimals=1):
    """295.0 -> '295', 84.6 -> '84.6'; `decimals` caps the places shown
    (0 rounds to the millimetre, which is how a width is quoted)."""
    x = round(float(x), decimals)
    return str(int(x)) if x == int(x) else f"{x:.{decimals}f}"


PRIMARY = ("HorizontalSlots", "RisingSliders", "FrontPocketCardCapacity", "CardsPerSlidingSlot",
           "isFirstSlidingSlotOverride", "FirstSlidingSlotCards", "isSleeved", "MatPocket",
           "GameName", "Version")


def values(row, d, spec):
    """Everything a template may name. The derived variables as they are,
    plus the poster's own:
      ext_w/ext_d/ext_h  the closed cascade — the lid's outer width and depth
                         (`BoxWidth + lid.WIDTH_OVER_BOX`, `calLidDepth`, which
                         reproduce every parts.csv W/D) and its height, the box
                         with the lid inverted on it: the lid's floor sits at
                         `WallThickness + BoxHeight` (`assembly.lid_closed`)
      card_w/card_h      the card the CAD sizes the slot for
      card_size          the game's stated card size for this sleeving, else
                         derived
      slot_cards         '12/30' when the first riser is deeper, else '12'
      age_cards          Innovation's cards per age: '15', or '15/10' where the
                         front pocket and the risers differ (`age_cards_unit`
                         then reads 'base / expansion', else '')
      pocket_w           the back pocket's width in mm — the empty run of the
                         rear storage right of the pusher slots (`box.rear_pocket`)
      slots              every slot, front pockets included (Compile's protocols)
      grid               'columns x rows', the front pocket a row (FCM)
      model_ref          the model code with middle dots
      printer            the phrase for the bed this sleeving needs
      sleeving           'Sl' / 'Un'
    """
    v = dict(d._v)
    for k in PRIMARY:
        v[k] = getattr(d, k)
    v.update({k: (row.get(k) or "").strip() for k in row})
    slv = "Sl" if d.isSleeved else "Un"
    v["sleeving"] = slv
    dw, dd, dh = spec.get("size_decimals", [0, 1, 1])
    v["ext_w"] = fmt_num(d.BoxWidth + LID.WIDTH_OVER_BOX, dw)
    v["ext_d"] = fmt_num(d.calLidDepth, dd)
    v["ext_h"] = fmt_num(D.WallThickness + d.BoxHeight, dh)
    v["card_w"] = fmt_num(d.calCardwidth)
    v["card_h"] = fmt_num(A.card_height(d))
    stated = spec.get("card_size") or {}
    v["card_size"] = stated.get(slv) or f"{v['card_w']} x {v['card_h']}"
    v["slot_cards"] = (f"{d.CardsPerSlidingSlot}/{d.FirstSlidingSlotCards}"
                       if d.isFirstSlidingSlotOverride else str(d.CardsPerSlidingSlot))
    fp, rs = d.FrontPocketCardCapacity, d.CardsPerSlidingSlot
    v["age_cards"] = str(fp) if fp == rs else f"{fp}/{rs}"
    v["age_cards_unit"] = "" if fp == rs else "base / expansion"
    x0, x1 = BOX.rear_pocket(d)
    v["pocket_w"] = fmt_num(x1 - x0, 1)
    # every slot, the front pockets included: Compile's "30 protocols" on L5
    v["slots"] = str(d.HorizontalSlots * (d.RisingSliders + 1))
    # FCM's "4x5": columns by ROWS, the front pocket being a row too
    v["grid"] = f"{d.HorizontalSlots}x{d.RisingSliders + 1}"
    v["model_ref"] = d.calModelName.replace(".", "·")
    bed = CC.bed_for(row, d) or "p1"
    kind = {"mini": "mini", "p1": "standard", "h2c": "large"}[bed]
    v["printer"] = spec["printer_phrases"].get(kind, f"{kind.upper()} 3D PRINTER")
    # the spec's own scalars (ages, expansions, kind, ...) are templatable too
    for k, val in spec.items():
        if isinstance(val, (str, int, float)) and k not in v:
            v[k] = val
    return v


class _Strict(dict):
    def __missing__(self, k):
        raise Refused(f"template names {k!r}, which nothing defines")


def T(template, v):
    return str(template).format_map(_Strict(v))


# ---------- the picture ----------
def has_alpha(im):
    return im.mode in ("RGBA", "LA") and im.getchannel("A").getextrema()[0] < 250


def knockout(path, thresh=40, max_w=2600):
    """A photo on a plain white background as RGBA cropped to its subject.
    Distance from white (the largest channel deficit) ramps to alpha around
    `thresh`, the edge is softened, and the JPEG's warm-white fringe goes
    with the background. A file that already carries transparency is only
    trimmed."""
    im = ImageOps.exif_transpose(Image.open(path))
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
    im = im.convert("RGBA")
    if has_alpha(im):
        return im.crop(im.getchannel("A").getbbox())
    rgb = np.asarray(im)[:, :, :3].astype(np.int16)
    dist = (255 - rgb).max(axis=2)
    lo, hi = thresh * 0.5, thresh * 1.5
    a = np.clip((dist - lo) / max(1.0, hi - lo), 0, 1) * 255
    alpha = Image.fromarray(a.astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(1.2))
    im.putalpha(alpha)
    box = alpha.point(lambda p: 255 if p > 24 else 0).getbbox()
    return im.crop(box) if box else im


def photo_path(row, d):
    """Steps 1 and 2 of the resolution: a photo named by convention."""
    game = PHOTOS / d.GameName
    names = [(row.get("Short name") or "").strip()]
    label = (row.get("Project label") or "").strip()
    if label:
        names.append(label)
    slv = "Sleeved" if d.isSleeved else "Unsleeved"
    for n in names:
        for stem in (f"{n} {slv}", n):
            for ext in ("png", "jpg", "jpeg", "PNG", "JPG", "JPEG"):
                p = game / f"{stem}.{ext}"
                if p.exists():
                    return p
    return None


def render_cache(d):
    return RENDERS / d.GameName / f"{B.model_stem(d.calModelName)}.png"


def render_picture(row, d, spec, samples=256, width=2400, spec_path=SPEC):
    """A fresh render: the cascade dressed for a poster (`cad.scene`: lid
    colour, front label, the game's cards in the slots), on nothing. Two
    subprocesses, each named when it starts so a run never looks hung."""
    dest = render_cache(d)
    dest.parent.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    label = f"{d.GameName}/{B.model_stem(d.calModelName)}"

    def stage(what):
        print(f"      {label}: {what} ...", flush=True)

    with tempfile.TemporaryDirectory() as tmp:
        glb = Path(tmp) / "cascade.glb"
        stage("building the scene (cad.scene)")
        cmd = [py, "-m", "cad.scene", "--model", d.calModelName, "--version", d.Version,
               "--spec", str(spec_path), "--glb", str(glb)]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if r.returncode or not glb.exists():
            raise Refused(f"cad.scene failed:\n{r.stdout[-1200:]}{r.stderr[-1200:]}")
        out = Path(tmp) / "out"
        stage(f"rendering in Blender ({samples} samples, {width} px)")
        cmd = [BLENDER, "-b", "-P", str(REPO / "render" / "cascade.py"), "--", str(glb),
               "--view", "hero", "--transparent", "--exposure", "-1.0",
               "--width", str(width), "--samples", str(samples), "--out", str(out)]
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=3600)
        hero = out / "hero.png"
        if r.returncode or not hero.exists():
            raise Refused(f"blender failed:\n{r.stdout[-1200:]}{r.stderr[-800:]}")
        shutil.move(str(hero), str(dest))
    return dest


def placeholder(text):
    im = Image.new("RGBA", (1600, 1000), PLACEHOLDER + (255,))
    dr = ImageDraw.Draw(im)
    f = PC.F(PC.MONO_R, 64)
    for i, line in enumerate(text.split("\n")):
        dr.text((800, 440 + i * 80), line, font=f, fill=PC.GREY, anchor="mm")
    return im


def picture_for(row, d, spec, do_render=False, force=False, spec_path=SPEC):
    """(image, note). See the module docstring for the order."""
    p = photo_path(row, d)
    if p is not None:
        return knockout(p), f"photo {p.relative_to(REPO)}"
    entry = (spec.get("photo") or {}).get("Sl" if d.isSleeved else "Un")
    if entry:
        path, thresh = (entry, 40) if isinstance(entry, str) else (entry[0], entry[1])
        path = REPO / path
        if not path.exists():
            raise Refused(f"spec photo {path} does not exist")
        return knockout(path, thresh), f"photo {entry}"
    cached = render_cache(d)
    if cached.exists() and not force:
        return knockout(cached), f"render (cached) {cached.relative_to(REPO)}"
    if do_render:
        return knockout(render_picture(row, d, spec, spec_path=spec_path)), f"render {cached.relative_to(REPO)}"
    return placeholder("no photo, no render\n(make_posters.py --render)"), "PLACEHOLDER"


# ---------- drawing ----------
def colour(name, spec, d):
    if name == "accent":
        name = spec["colours"].get("accent_Sl" if d.isSleeved else "accent_Un", "BLUE")
    if isinstance(name, (list, tuple)):
        return tuple(name)
    if name.startswith("#"):
        return tuple(int(name[i:i + 2], 16) for i in (1, 3, 5))
    return getattr(PC, name)


def font(name, size):
    return PC.F(getattr(PC, name), size)


def tracked(dr, xy, text, f, fill, tracking, anchor="ls"):
    """Text with letter spacing. `anchor` is 'ls' (left) or 'ms' (centred)."""
    widths = [dr.textlength(ch, font=f) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if anchor == "ms":
        x -= total / 2
    for ch, w in zip(text, widths):
        dr.text((x, y), ch, font=f, fill=fill, anchor="ls")
        x += w + tracking
    return total


def draw_icon(dr, kind, x, y, s, colour=PC.INK, img=None):
    """The cell icons, each inside an `s` x `s` box at (x, y): the file in
    `logos/icons/<kind>.svg|png` where one exists, else drawn in lines."""
    icon = PC.icon_image(kind, int(s), colour) if img is not None else None
    if icon is not None:
        img.paste(icon, (int(x + (s - icon.width) / 2), int(y + (s - icon.height) / 2)), icon)
        return
    lw = max(3, int(s * 0.045))
    if kind == "cards":
        w = s * 0.56
        dr.rounded_rectangle([x + s * 0.06, y + s * 0.14, x + s * 0.06 + w, y + s],
                             radius=int(s * 0.08), outline=colour, width=lw)
        dr.rounded_rectangle([x + s * 0.06 + w * 0.45, y, x + s * 0.06 + w * 1.45, y + s * 0.86],
                             radius=int(s * 0.08), fill=PC.CREAM, outline=colour, width=lw)
    elif kind == "pocket":
        # the back of the box seen from above: a wide tray with a width arrow under it
        dr.rounded_rectangle([x, y + s * 0.08, x + s, y + s * 0.62], radius=int(s * 0.06),
                             outline=colour, width=lw)
        dr.line([x + s * 0.12, y + s * 0.62, x + s * 0.12, y + s * 0.08], fill=colour, width=lw)
        ay = y + s * 0.86
        dr.line([x + s * 0.14, ay, x + s * 0.86, ay], fill=colour, width=lw)
        for ex, sgn in ((x + s * 0.14, 1), (x + s * 0.86, -1)):
            dr.line([ex, ay, ex + sgn * s * 0.12, ay - s * 0.1], fill=colour, width=lw)
            dr.line([ex, ay, ex + sgn * s * 0.12, ay + s * 0.1], fill=colour, width=lw)
    elif kind == "stack":
        # a card stack seen edge-on: a tall rounded box with two lines near the top
        dr.rounded_rectangle([x + s * 0.25, y, x + s * 0.75, y + s], radius=int(s * 0.08),
                             outline=colour, width=lw)
        for t in (0.2, 0.32):
            dr.line([x + s * 0.25, y + s * t, x + s * 0.75, y + s * t], fill=colour, width=lw)
    elif kind == "fan":
        n, cw, chh = 5, s * 0.42, s * 0.6
        for i in range(n):
            ox, oy = x + i * s * 0.14, y + i * s * 0.1
            dr.rounded_rectangle([ox, oy, ox + cw, oy + chh], radius=int(s * 0.06),
                                 fill=PC.CREAM, outline=colour, width=lw)
    elif kind == "size":
        # a cube in the top right, a vertical ruler down the left and a
        # horizontal one along the bottom, ticks alternating long and short
        cx, top, r = x + s * 0.64, y + s * 0.02, s * 0.3
        pts = [(cx, top), (cx + r, top + r * 0.5), (cx + r, top + r * 1.5), (cx, top + r * 2),
               (cx - r, top + r * 1.5), (cx - r, top + r * 0.5)]
        dr.polygon(pts, outline=colour, width=lw)
        dr.line([(cx - r, top + r * 0.5), (cx, top + r), (cx + r, top + r * 0.5)], fill=colour, width=lw)
        dr.line([(cx, top + r), (cx, top + r * 2)], fill=colour, width=lw)
        rw = s * 0.2
        dr.rectangle([x, y, x + rw, y + s * 0.74], outline=colour, width=lw)
        for i in range(1, 8):
            yy = y + s * 0.74 * i / 8
            dr.line([x + rw, yy, x + rw - s * (0.11 if i % 2 else 0.06), yy], fill=colour, width=lw)
        dr.rectangle([x + s * 0.26, y + s - rw, x + s, y + s], outline=colour, width=lw)
        for i in range(1, 8):
            xx = x + s * 0.26 + s * 0.74 * i / 8
            dr.line([xx, y + s - rw, xx, y + s - rw + s * (0.11 if i % 2 else 0.06)], fill=colour, width=lw)
    else:
        raise Refused(f"no such icon {kind!r}")


def load_glyph(name):
    p = GLYPHS / f"{name}.png"
    if not p.exists():
        raise Refused(f"no glyph for {name!r}: expected {p} (fetch_set_icons.py)")
    return PC.load_logo(p)


def draw_band(dr, img, e, spec, v, d):
    band = spec.get("band")
    if not band:
        return
    y, h = e["y"], e["h"]
    xt, xb = e["right"]
    dr.polygon([(0, y), (xt, y), (xb, y + h), (0, y + h)], fill=colour(e["colour"], spec, d))
    title = T(band["title"], v)
    size, f = e["title_size"], font("MONO_B", e["title_size"])
    room = xb - e["title_x"] - e["title_size"] * 0.5      # the slant's inner end
    while size > 60 and dr.textlength(title, font=f) > room:
        size -= 6
        f = font("MONO_B", size)
    dr.text((e["title_x"], y + h / 2), title, font=f, fill=PC.WHITE, anchor="lm")
    gh = e["glyph_h"]
    fc = font("INTER_B", e["caption_size"])
    fb = font("INTER_B", int(gh * e["badge"] * 0.62))
    entries = [(list(entry) + [None, None])[:3] for entry in band.get("sets", [])]
    captions = [(caption or name) + {"half": " (½)", "x2": " (x2)"}.get(mod, "")
                for name, mod, caption in entries]
    # a wide caption pushes the whole row apart rather than into its neighbour
    widest = max((dr.textlength(c, font=fc) for c in captions), default=0)
    pitch = max(band.get("pitch", e["pitch"]), widest + e.get("caption_gap", 40))
    x0 = max(e["x0"], widest / 2 + e["title_x"])         # the first keeps the margin
    for i, (name, mod, caption) in enumerate(entries):
        cx = x0 + i * pitch
        g = PC.fit(load_glyph(name), int(gh * 1.3), gh)
        gx, gy = int(cx - g.width / 2), int(e["glyph_top"] + (gh - g.height) / 2)
        img.paste(g, (gx, gy), g)
        cap = caption or name
        if mod == "half":
            r = gh * e["badge"] / 2
            bx, by = cx, e["glyph_top"] + gh / 2
            dr.ellipse([bx - r, by - r, bx + r, by + r], outline=PC.ORANGE, width=max(4, int(r * 0.12)))
            dr.text((bx, by), "½", font=fb, fill=PC.ORANGE, anchor="mm")
            cap += " (½)"
        elif mod == "x2":
            cap += " (x2)"
        elif mod:
            raise Refused(f"unknown set modifier {mod!r} on {name!r}")
        dr.text((cx, e["caption_y"]), cap, font=fc, fill=PC.INK, anchor="ms")


def draw_cells(dr, e, spec, v, img=None):
    x, y, w, h = e["box"]
    cells = spec["cells"]
    n = len(cells)
    if not n:
        return
    cw = w / n
    dr.rectangle([x, y, x + w, y + 3], fill=PC.RULE)
    fcap, fval, funit = (font("MONO_B", e["caption_size"]), font("MONO_R", e["value_size"]),
                         font("MONO_R", e["unit_size"]))
    for i, (icon, caption, value, unit) in enumerate(cells):
        cx = x + i * cw
        if i:
            dr.rectangle([cx, y + 40, cx + 3, y + h - 20], fill=PC.RULE)
        draw_icon(dr, icon, cx + e["inset"], y + 55, e["icon"], img=img)
        tx = cx + e["text_dx"]
        dr.text((tx, y + 50), T(caption, v), font=fcap, fill=PC.GREEN_D, anchor="la")
        dr.text((tx, y + 150), T(value, v), font=fval, fill=PC.INK, anchor="la")
        if unit and T(unit, v):
            dr.text((tx, y + 250), T(unit, v), font=funit, fill=PC.GREY, anchor="la")


def draw_stats(dr, e, spec, v, d):
    """The big stats, each centred vertically in its own band: `bands`
    ([y0, y1] per stat) when the layout gives them, else the box split
    evenly, so a stat sits between the rules drawn around it."""
    x, y, w, h = e["box"]
    stats = spec.get("stats") or []
    if not stats:
        return
    fv, fc = font("MONO_B", e["value_size"]), font("MONO_B", e["caption_size"])
    col = colour(e["colour"], spec, d)
    cx = x + w / 2
    bands = e.get("bands") or [[y + i * h / len(stats), y + (i + 1) * h / len(stats)]
                               for i in range(len(stats))]
    for (value, caption), (b0, b1) in zip(stats, bands):
        text = T(value, v)
        f, size = fv, e["value_size"]
        if e.get("fit"):
            while size > 60 and dr.textlength(text, font=f) > w:
                size -= 10
                f = font("MONO_B", size)
        vh = size * 0.72                            # a cap-high numeral
        ch = e["caption_size"] * 0.72 if caption else 0
        block = vh + (e["gap"] + ch if caption else 0)
        top = (b0 + b1) / 2 - block / 2
        dr.text((cx, top + vh), text, font=f, fill=col, anchor="ms")
        if caption:
            tracked(dr, (cx, top + vh + e["gap"] + ch), T(caption, v), fc, col,
                    e["tracking"], "ms")


def draw_model(dr, e, spec, v, d):
    x, y = e["xy"]
    col = colour(e["colour"], spec, d)
    dr.text((x, y), e["label"], font=font("MONO_B", e["label_size"]), fill=col, anchor="lt")
    y += e["label_size"] + e["gap"]
    size, f = e["code_size"], font("MONO_B", e["code_size"])
    while size > 60 and dr.textlength(v["model_ref"], font=f) > e.get("max_w", W):
        size -= 6
        f = font("MONO_B", size)
    dr.text((x, y), v["model_ref"], font=f, fill=col, anchor="lt")
    y += e["code_size"] * 0.78 + e.get("printer_gap", e["gap"])
    fp = font("MONO_R", e["printer_size"])
    if e.get("plate"):
        # Compile's design: the printer line reversed out of a coloured plate
        # `plate` [x0, w, h], the text keeping the block's x
        px, pw, ph = e["plate"]
        dr.rectangle([px, y - (ph - e["printer_size"]) / 2, px + pw,
                      y - (ph - e["printer_size"]) / 2 + ph], fill=col)
        dr.text((x, y), v["printer"], font=fp, fill=PC.WHITE, anchor="lt")
    else:
        dr.text((x, y), v["printer"], font=fp, fill=PC.GREY, anchor="lt")


def place_picture(picture, x, y, bw, bh, anchor, avoid, step=40):
    """The picture fitted into the box and anchored; where `avoid` lists
    rectangles [x0, y0, x1, y1] the box is shortened, `step` px at a time,
    until no opaque pixel of the picture lands in any of them — a render
    with a sloping lid keeps the whole box, a straight-on photo backs off
    the band's bar."""
    h = bh
    while True:
        pic = PC.fit(picture, bw, h)
        px = x + {"l": 0, "c": (bw - pic.width) // 2, "r": bw - pic.width}[anchor[0]]
        py = y + {"t": 0, "m": (h - pic.height) // 2, "b": h - pic.height}[anchor[1]]
        if h <= step or not any(_opaque_in(pic, px, py, r) for r in avoid):
            return pic, px, py
        h -= step


def _opaque_in(pic, px, py, rect):
    x0, y0, x1, y1 = rect
    box = (max(x0, px) - px, max(y0, py) - py, min(x1, px + pic.width) - px, min(y1, py + pic.height) - py)
    if box[0] >= box[2] or box[1] >= box[3]:
        return False
    alpha = pic.getchannel("A") if pic.mode == "RGBA" else None
    return alpha is None or alpha.crop(box).getextrema()[1] > 16


def draw_poster(row, d, spec, picture, debug=False):
    v = values(row, d, spec)
    img = Image.new("RGB", (W, H), PC.CREAM)
    dr = ImageDraw.Draw(img)
    for e in spec["layout"]:
        t = e["type"]
        if t == "wordmark":
            PC.wordmark(dr, *e["xy"], e["scale"])
        elif t == "text":
            dr.text(tuple(e["xy"]), T(e["text"], v), font=font(e["font"], e["size"]),
                    fill=colour(e["colour"], spec, d), anchor=e.get("anchor", "la"))
        elif t == "logo":
            path = spec.get("logo") or PC.GAME_LOGOS.get(d.GameName)
            x, y, bw, bh = e["box"]
            if path and os.path.exists(str(REPO / path)):
                lg = PC.fit(PC.load_logo(str(REPO / path)), bw, bh)
                img.paste(lg, (x, y), lg)
            else:
                dr.text((x, y), PC.GAME_DISPLAY.get(d.GameName, d.GameName),
                        font=font("MONO_B", 110), fill=PC.INK, anchor="la")
        elif t == "banner":
            PC.corner_banner(dr, W, "SLEEVED" if d.isSleeved else "UNSLEEVED",
                             colour("accent", spec, d), 0, e["h"], e["x0"], e["slant"],
                             e["size"], e["pad_r"], e["icon"], img)
        elif t == "rules":
            for x0, yy, x1 in e["lines"]:
                dr.rectangle([x0, yy, x1, yy + e["width"]], fill=PC.RULE)
        elif t == "stats":
            draw_stats(dr, e, spec, v, d)
        elif t == "model":
            draw_model(dr, e, spec, v, d)
        elif t == "picture":
            x, y, bw, bh = e["box"]
            if e.get("crop") and picture.mode == "RGBA" and picture.getbbox():
                picture = picture.crop(picture.getbbox())   # the box bounds the CONTENT
            anchor = e.get("anchor", "cb")
            pic, px, py = place_picture(picture, x, y, bw, bh, anchor, e.get("avoid", ()))
            img.paste(pic, (px, py), pic)
        elif t == "band":
            draw_band(dr, img, e, spec, v, d)
        elif t == "cells":
            draw_cells(dr, e, spec, v, img)
        elif t == "footer":
            PC.footer(dr, W, H, d.Version, e["scale"], e["margin"])
        else:
            raise Refused(f"unknown layout element type {t!r}")
        if debug and "box" in e:
            x, y, bw, bh = e["box"]
            dr.rectangle([x, y, x + bw, y + bh], outline=(255, 0, 0), width=3)
            dr.text((x + 6, y + 4), e["name"], font=font("MONO_R", 36), fill=(255, 0, 0))
    return img


def output_path(row, d, out=CC.OUT):
    return Path(out) / d.GameName / (CC.filename(row, d)[:-len(".3mf")] + ".png")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game")
    ap.add_argument("--model", help="a model code or part of one")
    ap.add_argument("--sleeving", choices=("un", "sl"))
    ap.add_argument("--name", help="part of the row's Short name")
    ap.add_argument("--render", action="store_true",
                    help="render a cascade that has no photo and no cached render (Blender, minutes each)")
    ap.add_argument("--force-render", action="store_true", help="re-render even when cached")
    ap.add_argument("--out", type=Path, default=CC.OUT, help="default build/cascades/")
    ap.add_argument("--spec", type=Path, default=SPEC)
    ap.add_argument("--csv", type=Path, default=CC.CSV)
    ap.add_argument("--version", default=CURRENT, choices=RELEASES)
    ap.add_argument("--debug-boxes", action="store_true", help="outline every element's box")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)

    spec = load_spec(args.spec)
    rows = CC.catalogue(args.csv, args.game, args.model, None, args.sleeving, args.name, args.version)
    if args.list:
        for row, d in rows:
            s = spec_for(spec, row, d)
            p = photo_path(row, d)
            src = (f"photo {p.relative_to(REPO)}" if p else
                   f"spec photo" if (s.get("photo") or {}).get("Sl" if d.isSleeved else "Un") else
                   f"render (cached)" if render_cache(d).exists() else "render needed")
            print(f"  {d.GameName}/{output_path(row, d, args.out).name:70s} {src}")
        print(f"\n  {len(rows)} poster{'' if len(rows) == 1 else 's'}")
        return 0
    failed = []
    for row, d in rows:
        try:
            s = spec_for(spec, row, d)
            pic, note = picture_for(row, d, s, args.render, args.force_render, args.spec)
            img = draw_poster(row, d, s, pic, args.debug_boxes)
            path = output_path(row, d, args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            img.save(path)
            print(f"  {d.GameName + '/' + path.name:72s} {note}", flush=True)
        except Refused as e:
            failed.append(f"{d.GameName}/{CC.title(row, d)}: {e}")
            print(f"  {d.GameName + '/' + CC.title(row, d):72s} REFUSED {e}")
    print(f"\n  {len(rows) - len(failed)} of {len(rows)} written to {args.out}")
    for f in failed:
        print(f"  refused  {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
