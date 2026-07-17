#!/usr/bin/env python3
"""Generate MakerWorld cover images for the per-set label 3MFs.

One 4000x3000-style (2010x1500 px, 4:3) cover per cc.cfg record, matching
the cascade poster design language: Card Cascade wordmark, game logo,
stacked UNSLEEVED/SLEEVED corner banners, a size-graded stack of the
set's actual labels (front, box sides, split-box labels) with type/width
captions, FULL SET / PARTIAL SETS chips, and a bottom band naming the set.

    python3 make_label_covers.py [--out labels] [--version 6.2]
                                 [--sets "Renaissance,Base Set"]

Covers are written to <out>/<game>/sets/, next to the per-set .3mf files.

Requires: pillow (pip install pillow). Reads cc.cfg via labelmaker.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import labelmaker as dl

REPO = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(REPO, "fonts")
W, H = 2010, 1500

# ---------- palette sampled from the cascade posters ----------
CREAM   = (242, 240, 235)
INK     = (26, 26, 26)
GREEN   = (74, 124, 90)
GREEN_D = (56, 100, 70)
GREEN_L1 = (140, 199, 144)
GREEN_L2 = (86, 158, 100)
BAR      = (129, 197, 144)      # #81C590 — wordmark bars
BLUE    = (63, 107, 178)
GREY    = (120, 120, 118)
WHITE   = (255, 255, 255)
PLATE   = (250, 250, 247)
PLATE_E = (216, 214, 208)

ORB = os.path.join(FONTS, "Orbitron-Bold.ttf")
MONO_CANDIDATES_B = [
    os.path.join(FONTS, "DMMono-Medium.ttf"),
    os.path.expanduser("~/Library/Fonts/DMMono-Medium.ttf"),
    "/usr/share/fonts/truetype/dm-mono/DMMono-Medium.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    "/Library/Fonts/Courier New Bold.ttf",
]
MONO_CANDIDATES_R = [
    os.path.join(FONTS, "DMMono-Regular.ttf"),
    os.path.expanduser("~/Library/Fonts/DMMono-Regular.ttf"),
    "/usr/share/fonts/truetype/dm-mono/DMMono-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/Library/Fonts/Courier New.ttf",
]
MONO_B = next((p for p in MONO_CANDIDATES_B if os.path.exists(p)), None)
MONO_R = next((p for p in MONO_CANDIDATES_R if os.path.exists(p)), None)
if not (MONO_B and MONO_R):
    sys.exit("no monospace font found - edit MONO_CANDIDATES_* for this machine")

INTER_CANDIDATES = [
    os.path.join(FONTS, "Inter-Regular.ttf"),
    os.path.expanduser("~/Library/Fonts/Inter-VariableFont_opsz,wght.ttf"),
    "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
    "/Library/Fonts/Inter-Regular.ttf",
]
INTER_R = next((p for p in INTER_CANDIDATES if os.path.exists(p)), MONO_R)

GAME_LOGOS = {
    "Dominion": os.path.join(REPO, "logos", "dominion_logo_v1_0",
                             "dl2_full_1024px.png"),
}
GAME_DISPLAY = {"FCM": "Food Chain Magnate"}


def F(path, px):
    return ImageFont.truetype(path, int(px))


def cap_scale(px):
    """Orbitron sized so capital height ~= px (caps are ~0.72 em)."""
    return ImageFont.truetype(ORB, int(px / 0.72))


def load_logo(path):
    im = Image.open(path).convert("RGBA")
    alpha = im.getchannel("A")
    if alpha.getextrema()[0] < 250:                 # native transparency
        return im.crop(alpha.getbbox())
    grey = im.convert("L")
    alpha = grey.point(lambda v: max(0, min(255, (250 - v) * 4)))
    im.putalpha(alpha)
    return im.crop(alpha.getbbox())


# ---------- the printed label, top view ----------
LABEL_H_MM = 22.2


def draw_staircase(d, x, y, s, colour):
    step = s / 3.0
    for i in range(3):
        d.rectangle([x + i * step, y + (2 - i) * step,
                     x + (i + 1) * step, y + s], fill=colour)


def render_label(text, width_mm, scale, caps):
    w, h = int(width_mm * scale), int(LABEL_H_MM * scale)
    pad = int(0.35 * scale) + 6
    img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ox, oy = pad, pad
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [ox + 5, oy + 8, ox + w + 5, oy + h + 8],
        radius=int(0.5 * scale), fill=(0, 0, 0, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    d.rounded_rectangle([ox, oy, ox + w, oy + h],
                        radius=int(0.4 * scale), fill=PLATE_E)
    ch = int(0.6 * scale)
    d.rounded_rectangle([ox + ch, oy + ch, ox + w - ch, oy + h - ch],
                        radius=int(0.25 * scale), fill=PLATE)
    if text:
        caph = caps.get(width_mm, 4.5) * scale
        f = cap_scale(caph)
        tw = d.textlength(text, font=f)
        max_tw = w - 2 * 2.5 * scale
        if tw > max_tw:
            caph *= max_tw / tw
            f = cap_scale(caph)
            tw = d.textlength(text, font=f)
        asc, _ = f.getmetrics()
        baseline = oy + h - 10.1 * scale
        d.text(((img.width - tw) / 2, baseline - asc * 0.98),
               text, font=f, fill=INK)
    m, ls = 3.6 * scale, 4.5 * scale
    draw_staircase(d, ox + m, oy + h - m - ls, ls, INK)
    fcc = ImageFont.truetype(ORB, int(2.5 * scale / 0.5))
    ccw = d.textlength("cc", font=fcc)
    d.text((ox + w - m - ccw, oy + h - m - fcc.getmetrics()[0] * 0.78),
           "cc", font=fcc, fill=INK)
    return img


# ---------- shared chrome ----------
def wordmark(d, x, y, s=1.0):
    bs = int(90 * s)
    step = bs / 3
    for i in range(3):
        bh = bs * (0.45 + 0.275 * i)
        bx = x + i * step
        d.rounded_rectangle([bx, y + bs - bh, bx + step * 0.72, y + bs],
                            radius=int(6 * s), fill=BAR)
    # two stacked lines of Orbitron, block ~ as tall as the tallest bar
    tx = x + bs + int(24 * s)
    caph = bs * 0.44
    f = cap_scale(caph)
    d.text((tx, y + caph), "Card", font=f, fill=INK, anchor="ls")
    d.text((tx, y + bs), "Cascade", font=f, fill=INK, anchor="ls")


def card_icon(d, x, y, s, colour=WHITE):
    w = s * 0.62
    lw = max(3, int(s * 0.08))
    d.rounded_rectangle([x, y + s * 0.12, x + w, y + s * 1.02],
                        radius=int(s * 0.12), outline=colour, width=lw)
    d.rounded_rectangle([x + w * 0.42, y, x + w * 1.42, y + s * 0.9],
                        radius=int(s * 0.12), outline=colour, width=lw)


def corner_banners(d):
    bh = 108
    f = F(MONO_B, 62)
    for i, (txt, col) in enumerate(
            zip(("UNSLEEVED", "SLEEVED"), (GREEN, BLUE))):
        y0 = i * bh
        x0 = W - 760
        d.polygon([(x0 + 90, y0), (W, y0), (W, y0 + bh), (x0, y0 + bh)],
                  fill=col)
        tw = d.textlength(txt, font=f)
        d.text((W - 170 - tw, y0 + bh / 2 - 38), txt, font=f, fill=WHITE)
        card_icon(d, W - 135, y0 + 22, 60)


def footer(d, version):
    # thin grey divider above the bottom line, edge to edge
    d.rectangle([0, H - 108, W, H - 104], fill=(190, 190, 188))
    f = F(MONO_R, 30)
    ty = H - 78
    d.text((60, ty), "Free on MakerWorld", font=f, fill=GREEN_D)
    t = "© 2026 Allan & Mamta Mertner"
    d.text(((W - d.textlength(t, font=f)) / 2, ty), t, font=f, fill=GREY)
    # mini Card Cascade logo + version, right-aligned
    s = 0.52
    bs = int(90 * s)
    caph = bs * 0.44
    wf = cap_scale(caph)
    logo_w = bs + int(24 * s) + d.textlength("Cascade", font=wf)
    ver = f"v{version}"
    vw = d.textlength(ver, font=f)
    gap = 22
    x0 = W - 60 - logo_w - gap - vw
    y0 = H - 96
    wordmark(d, x0, y0, s)
    d.text((x0 + logo_w + gap, y0 + bs / 2 - 15), ver, font=f, fill=GREY)


# ---------- per-set label stack ----------
def stack_rows(rec, game_cfg):
    """[(caption, label text, width_mm)] for one cc.cfg record."""
    name = rec["name"] or "Blank"
    side_text = rec.get("side") or name
    rows = [("FRONT LABEL", "" if not rec["name"] else name,
             game_cfg["front"])]
    if rec.get("box"):
        u, s = rec["box"]["widths"]
        for wmm in sorted({w for w in (u, s) if w}, reverse=True):
            rows.append((f"SIDE LABEL · {wmm:g} MM", side_text, wmm))
    if rec.get("split"):
        halves = rec["split"]
        h1, h2 = halves[0], halves[-1]
        w1 = max(w for w in h1["widths"] if w) if any(h1["widths"]) else 0
        lo = [w for w in h2["widths"] if w]
        w2 = min(lo) if lo else 0
        if w1:
            rows.append((f"SPLIT BOX · {w1:g} MM", f"{side_text} 1", w1))
        if w2:
            rows.append((f"SPLIT BOX · {w2:g} MM", f"{side_text} 2", w2))
    if not rec.get("box") and not rec.get("split"):
        # blank/spares-style record: show the game's standard side widths
        for wmm in game_cfg["widths"][1:]:
            rows.append((f"SIDE LABEL · {wmm:g} MM",
                         "" if not rec["name"] else side_text, wmm))
    return rows


# right-hand label stack lives in this vertical band on every cover
STACK_TOP, STACK_BOTTOM = 350, H - 370


def row_height(scale):
    return 44 + int(LABEL_H_MM * scale) + 2 * (int(0.35 * scale) + 6) + 6


LABEL_SCALE_MAX = 6.4           # large default; shrinks only if rows overflow


def fit_scale(n_rows):
    """Largest label scale (0.2 steps) that fits n_rows in the stack band.

    Labels stay large by default and only scale down for busier sets; the
    22.2 mm height and width are always in proportion at whatever scale wins.
    """
    avail = STACK_BOTTOM - STACK_TOP
    scale = LABEL_SCALE_MAX
    while scale > 3.0 and n_rows * row_height(scale) > avail:
        scale -= 0.2
    return round(scale, 1)


def make_cover(rec, game, game_cfg, version, out_dir):
    display = rec["name"] or "Blank"
    game_disp = GAME_DISPLAY.get(game, game)
    caps = game_cfg["caps"]

    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    corner_banners(d)
    wordmark(d, 70, 60, 1.15)
    d.text((70, 240), "A store-and-play system for", font=F(INTER_R, 40),
           fill=GREY)
    logo_path = GAME_LOGOS.get(game)
    if logo_path and os.path.exists(logo_path):
        lg = load_logo(logo_path)
        r = min(470 / lg.width, 125 / lg.height)
        lg = lg.resize((int(lg.width * r), int(lg.height * r)), Image.LANCZOS)
        img.paste(lg, (70, 305), lg)
    else:
        d.text((70, 305), game_disp, font=F(MONO_B, 56), fill=INK)

    fb = F(MONO_B, 120)
    d.text((70, 560), "SLIDE-IN", font=fb, fill=GREEN)
    d.text((70, 690), "LABELS", font=fb, fill=GREEN)
    d.text((70, 850), "Two-colour 3D printable", font=F(MONO_R, 46), fill=INK)
    d.text((70, 910), "for every box size", font=F(MONO_R, 46), fill=INK)

    # right-hand stack: large labels by default, shrink to fit if many rows
    rows = stack_rows(rec, game_cfg)
    scale = fit_scale(len(rows))
    total_h = sum(row_height(scale) for _ in rows)
    x_right = W - 90
    y = STACK_TOP + max(0, (STACK_BOTTOM - STACK_TOP - total_h) // 2)
    fcap = F(MONO_B, 34)
    for caption, text, wmm in rows:
        lab = render_label(text, wmm, scale, caps)
        cw = d.textlength(caption, font=fcap)
        d.text((x_right - cw - 12, y), caption, font=fcap, fill=GREY)
        y += 44
        img.paste(lab, (x_right - lab.width, y), lab)
        y += lab.height + 6

    # bottom band
    d.polygon([(0, H - 340), (W * 0.72, H - 340), (W * 0.66, H - 200),
               (0, H - 200)], fill=GREEN)
    band = display if not rec["name"] else f"{game_disp}: {display}"
    fb2 = F(MONO_B, 84)
    while d.textlength(band, font=fb2) > 1160 and fb2.size > 40:
        fb2 = F(MONO_B, fb2.size - 4)
    d.text((70, H - 324 + (84 - fb2.size) // 2), band, font=fb2, fill=WHITE)
    footer(d, version)

    fname = f"{display} Labels {version.replace('.', '_')}.png"
    fname = "".join(c if c not in '\\/:*?"<>|' else "_" for c in fname)
    path = os.path.join(out_dir, fname)
    img.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(REPO, "labels"),
                    help="base labels dir; covers go to <out>/<game>/sets")
    ap.add_argument("--version", default="6.2")
    ap.add_argument("--sets", default=None,
                    help="comma-separated set names (default: all)")
    args = ap.parse_args()

    cfg_file = dl.find_config_file()
    if not cfg_file:
        sys.exit("cc.cfg not found")
    wanted = ([s.strip().lower() for s in args.sets.split(",")]
              if args.sets else None)

    n = 0
    for game, game_cfg in dl.GAMES.items():
        records = dl.read_config_file(cfg_file, game)
        if not records:
            continue
        set_dir = os.path.join(args.out, game, "sets")
        os.makedirs(set_dir, exist_ok=True)
        for rec in records:
            display = rec["name"] or "Blank"
            if wanted and display.lower() not in wanted:
                continue
            path = make_cover(rec, game, game_cfg, args.version, set_dir)
            print(f"  {path}")
            n += 1
    print(f"done: {n} cover(s)")


if __name__ == "__main__":
    main()
