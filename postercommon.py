"""The Card Cascade poster chrome, shared by every generated picture.

`make_posters.py` and `make_label_covers.py` draw the same wordmark, banners,
footer and card icon, so a change to the brand is one edit and neither script
imports the other. Nothing here knows the canvas
size: every call takes its own position and scale. Pure Pillow.
"""
import os

from PIL import Image, ImageChops, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(REPO, "fonts")

# ---------- palette sampled from the cascade posters ----------
CREAM    = (242, 240, 235)
INK      = (26, 26, 26)
GREEN    = (74, 124, 90)
GREEN_D  = (56, 100, 70)
GREEN_L1 = (140, 199, 144)
GREEN_L2 = (86, 158, 100)
BAR      = (129, 197, 144)      # #81C590 — wordmark bars
BLUE     = (63, 107, 178)       # #3F6BB2 — the SLEEVED banner
BANNER_UN = (81, 124, 91)       # #517C5B — the UNSLEEVED banner (Figma)
BANNER_SL = (57, 105, 176)      # #3969B0 — the SLEEVED banner (Figma)
ORANGE   = (241, 143, 30)       # the "½" badge on a partial expansion
GREY     = (120, 120, 118)
RULE     = (190, 190, 188)      # the thin dividers
WHITE    = (255, 255, 255)
PLATE    = (250, 250, 247)
PLATE_E  = (216, 214, 208)

# ---------- faces ----------
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
    raise SystemExit("no monospace font found - edit MONO_CANDIDATES_* for this machine")

INTER_CANDIDATES = [
    os.path.join(FONTS, "Inter-Regular.ttf"),
    os.path.expanduser("~/Library/Fonts/Inter-VariableFont_opsz,wght.ttf"),
    "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
    "/Library/Fonts/Inter-Regular.ttf",
]
INTER_R = next((p for p in INTER_CANDIDATES if os.path.exists(p)), MONO_R)
# A bold humanist sans for the captions; OpenSans-Bold is the closest shipped.
INTER_B = next((p for p in (os.path.join(FONTS, "Inter-Bold.ttf"),
                            os.path.join(FONTS, "OpenSans-Bold.ttf"))
                if os.path.exists(p)), INTER_R)

# The raster logo each game's poster carries under "A store-and-play system for".
GAME_LOGOS = {
    "Dominion": os.path.join(REPO, "logos", "dominion_logo_v1_0", "dl2_full_1024px.png"),
    "Innovation": os.path.join(REPO, "logos", "Innovation", "logo.png"),
    "Compile": os.path.join(REPO, "logos", "Compile", "compile_logo.png"),
    "FCM": os.path.join(REPO, "logos", "FCM", "FCM round.png"),
}
# Where a game has no logo image the poster writes this; "\n" breaks a line.
GAME_DISPLAY = {"FCM": "Food Chain Magnate",
                "MiniCards": "Mini cards\n41 \u00d7 63 mm"}


def F(path, px):
    return ImageFont.truetype(path, int(px))


def cap_scale(px):
    """Orbitron sized so capital height ~= px (caps are ~0.72 em)."""
    return ImageFont.truetype(ORB, int(px / 0.72))


def load_logo(path):
    """A logo as RGBA cropped to its ink, white knocked out."""
    im = Image.open(path).convert("RGBA")
    alpha = im.getchannel("A")
    if alpha.getextrema()[0] < 250:
        return im.crop(alpha.getbbox())
    grey = im.convert("L")
    alpha = grey.point(lambda v: max(0, min(255, (250 - v) * 4)))
    im.putalpha(alpha)
    return im.crop(alpha.getbbox())


def fit(im, w, h):
    r = min(w / im.width, h / im.height)
    return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))),
                     Image.LANCZOS)


# ---------- the marks ----------
def wordmark(d, x, y, s=1.0):
    """The three green bars and "Card / Cascade"; returns its width."""
    bs = int(90 * s)
    step = bs / 3
    for i in range(3):
        bh = bs * (0.45 + 0.275 * i)
        bx = x + i * step
        d.rounded_rectangle([bx, y + bs - bh, bx + step * 0.72, y + bs],
                            radius=int(6 * s), fill=BAR)
    tx = x + bs + int(24 * s)
    caph = bs * 0.44
    f = cap_scale(caph)
    d.text((tx, y + caph), "Card", font=f, fill=INK, anchor="ls")
    d.text((tx, y + bs), "Cascade", font=f, fill=INK, anchor="ls")
    return bs + int(24 * s) + d.textlength("Cascade", font=f)


def card_icon(d, x, y, s, colour=WHITE):
    w = s * 0.62
    lw = max(3, int(s * 0.08))
    d.rounded_rectangle([x, y + s * 0.12, x + w, y + s * 1.02],
                        radius=int(s * 0.12), outline=colour, width=lw)
    d.rounded_rectangle([x + w * 0.42, y, x + w * 1.42, y + s * 0.9],
                        radius=int(s * 0.12), outline=colour, width=lw)


def corner_banner(d, W, text, colour, y0, bh, x0, slant, font_px, pad_r, icon, img=None):
    """One slanted banner in the top-right corner, `text` right-aligned with a
    card icon after it (the `cards` file where there is one, else drawn)."""
    f = F(MONO_B, font_px)
    d.polygon([(x0, y0), (W, y0), (W, y0 + bh), (x0 + slant, y0 + bh)], fill=colour)
    tw = d.textlength(text, font=f)
    d.text((W - pad_r - tw, y0 + bh / 2), text, font=f, fill=WHITE, anchor="lm")
    art = icon_image("cards", int(icon), WHITE) if img is not None else None
    if art is not None:
        img.paste(art, (int(W - pad_r + icon * 0.35), int(y0 + (bh - art.height) / 2)), art)
    else:
        card_icon(d, W - pad_r + icon * 0.35, y0 + (bh - icon * 1.02) / 2, icon)


def corner_banners(d, W):
    bh = 108
    for i, (txt, col) in enumerate(zip(("UNSLEEVED", "SLEEVED"), (GREEN, BLUE))):
        y0 = i * bh
        x0 = W - 760
        f = F(MONO_B, 62)
        d.polygon([(x0 + 90, y0), (W, y0), (W, y0 + bh), (x0, y0 + bh)], fill=col)
        tw = d.textlength(txt, font=f)
        d.text((W - 170 - tw, y0 + bh / 2 - 38), txt, font=f, fill=WHITE)
        card_icon(d, W - 135, y0 + 22, 60)


def footer(d, W, H, version, s=1.0, margin=60):
    """Divider, "Free on MakerWorld", the copyright and the mini wordmark."""
    d.rectangle([0, H - int(108 * s), W, H - int(104 * s)], fill=RULE)
    f = F(MONO_R, 30 * s)
    ty = H - int(78 * s)
    m = int(margin * s)
    d.text((m, ty), "Free on MakerWorld", font=f, fill=GREEN_D)
    t = "© 2026 Allan & Mamta Mertner"
    d.text(((W - d.textlength(t, font=f)) / 2, ty), t, font=f, fill=GREY)
    ws = 0.52 * s
    bs = int(90 * ws)
    caph = bs * 0.44
    wf = cap_scale(caph)
    logo_w = bs + int(24 * ws) + d.textlength("Cascade", font=wf)
    ver = f"v{version}" if version else ""
    vw = d.textlength(ver, font=f) if ver else 0
    gap = int(22 * s) if ver else 0
    x0 = W - m - logo_w - gap - vw
    y0 = H - int(96 * s)
    wordmark(d, x0, y0, ws)
    if ver:
        d.text((x0 + logo_w + gap, y0 + bs / 2 - 15 * s), ver, font=f, fill=GREY)


# ---------- SVG icons ----------
ICONS = os.path.join(REPO, "logos", "icons")


def _polys(spath, scale):
    out = []
    for sub in spath.as_subpaths():
        sp = type(spath)(sub)
        n = max(2, int(sp.length() * scale / 3))
        pts = [(q.x * scale, q.y * scale) for q in (sp.point(i / n) for i in range(n + 1))
               if q is not None]
        if len(pts) >= 3:
            out.append(pts)
    return out


def _mask(polys, size):
    """Even-odd fill of `polys` as a 1-bit mask (nonzero, for icons)."""
    mask = Image.new("1", size, 0)
    for pts in polys:
        one = Image.new("1", size, 0)
        ImageDraw.Draw(one).polygon(pts, fill=1)
        mask = ImageChops.logical_xor(mask, one)
    return mask


def svg_icon(path, size, colour=INK, oversample=4):
    """A simple SVG icon rasterised to RGBA, `size` px on its longer side. No
    SVG renderer is in the venv, so `svgelements` parses it and each shape is
    painted in document order — fill (a black fill takes `colour`), then
    stroke. Clips and defs are ignored."""
    from svgelements import SVG, Path as SPath, Rect, Shape, Color
    svg = SVG.parse(path)
    vb = svg.viewbox
    w, h = (vb.width, vb.height) if vb is not None else (svg.width, svg.height)
    scale = oversample * size / max(w, h)
    W_, H_ = int(round(w * scale)), int(round(h * scale))
    canvas = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))

    def rgb(c):
        if c is None or c.value is None:
            return None
        v = (c.red, c.green, c.blue)
        return colour if v == (0, 0, 0) else v

    def paint(mask, col):
        layer = Image.new("RGBA", (W_, H_), col + (255,))
        canvas.paste(layer, (0, 0), mask.convert("L"))

    for el in svg.elements():
        if not isinstance(el, Shape):
            continue
        fill, stroke = rgb(el.fill), rgb(el.stroke)
        sw = float(el.stroke_width or 0)
        if fill is not None:
            paint(_mask(_polys(SPath(el), scale), (W_, H_)), fill)
        if stroke is not None and sw > 0:
            if isinstance(el, Rect):
                r = float(el.rx or 0)
                outer = Rect(el.x - sw / 2, el.y - sw / 2, el.width + sw, el.height + sw,
                             rx=r + sw / 2, ry=r + sw / 2)
                inner = Rect(el.x + sw / 2, el.y + sw / 2, el.width - sw, el.height - sw,
                             rx=max(0, r - sw / 2), ry=max(0, r - sw / 2))
                ring = ImageChops.logical_xor(_mask(_polys(SPath(outer), scale), (W_, H_)),
                                              _mask(_polys(SPath(inner), scale), (W_, H_)))
                paint(ring, stroke)
            else:
                line = Image.new("1", (W_, H_), 0)
                ld = ImageDraw.Draw(line)
                for pts in _polys(SPath(el), scale):
                    ld.line(pts + pts[:1], fill=1, width=max(1, int(sw * scale)))
                paint(line, stroke)
    return canvas.resize((max(1, W_ // oversample), max(1, H_ // oversample)), Image.LANCZOS)


def png_icon(path, size, colour=INK):
    """A PNG silhouette icon (alpha is the shape) as RGBA in `colour`."""
    im = Image.open(path).convert("RGBA")
    k = size / max(im.size)
    im = im.resize((max(1, int(round(im.width * k))), max(1, int(round(im.height * k)))), Image.LANCZOS)
    out = Image.new("RGBA", im.size, colour + (255,))
    out.putalpha(im.getchannel("A"))
    return out


def icon_image(kind, size, colour=INK):
    """`logos/icons/<kind>.svg` or `.png` in `colour`, or None."""
    svg = os.path.join(ICONS, f"{kind}.svg")
    png = os.path.join(ICONS, f"{kind}.png")
    if os.path.exists(svg):
        return svg_icon(svg, size, colour)
    if os.path.exists(png):
        return png_icon(png, size, colour)
    return None
