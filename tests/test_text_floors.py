"""No engraved or embossed text in the catalogue is thinner than its floor.

`cad/text.py`, "floors": text CUT into a part is set no smaller than a
0.200 mm stroke, text that STANDS PROUD no smaller than 0.250 (Allan,
2026-09-04). This walks every text placement on every part in parts.csv —
the sizing functions are pure arithmetic, so it is seconds — and asserts,
from both ends as every divergence is:

  * the FINAL size of every line is at or above its floor;
  * the lines the floor RAISES are exactly the ones on record — four pusher
    version lines, one pusher detail line, nine box lines on five boxes, and
    the lettering on the two 10-card unsleeved topper sizes (a CUT floor:
    the inlay prints face down in a pocket) — so a floor that quietly
    started binding somewhere new, or stopped, fails here;
  * every raised line still fits the part's hard extent (`DoesNotFit` is
    never raised across the catalogue).

    .venv/bin/python tests/test_text_floors.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import build as B, derive as D, text as T          # noqa: E402
from cad.parts import box, lid, holder, token_holder, topper  # noqa: E402

fails = []


def check(label, got, want, tol=0.0):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok ' if ok else 'FAIL'}  {label:64s} {got} vs {want}")
    if not ok:
        fails.append(label)


placed = []         # (part, file, line, size, floor)
raised = []         # (part, file, line) where the fitted size was under it


def record(part, fn, line, fitted, final, font, proud):
    """A line is RAISED when its fitted size was under the floor and its
    final size is not; one the floor cannot reach is neither."""
    floor = T.floor_size(font, proud)
    placed.append((part, fn, line, final, floor))
    if fitted < floor - 1e-9 and final >= floor - 1e-9:
        raised.append((part, fn, line))


print("=== pushers ===")
for _folder, fn, p in B.catalogue():
    d = D.derive(p)
    (txt, sz, _x, _b), (_v, vsz, _x2, _b2) = T.logo_lines(p, d)
    cap_em, asc_em = T._metrics(T.LOGO_FONT)
    strip = d.calSliderDistance
    margin = T.LOGO_MARGIN * strip
    fitted = T.font_size_for_cap(
        min((strip - 2 * margin) / (asc_em / cap_em),
            (d.calPusherTotalHeight - 2.0 - d.calHeightIncrement)
            / (T._width_per_cap(d.ProductName, T.LOGO_FONT) + T._LSB_C / cap_em)),
        T.LOGO_FONT)
    record("Pusher", fn, "product", fitted, sz, T.LOGO_FONT, False)
    record("Pusher", fn, "version", fitted / 2, vsz, T.LOGO_FONT, False)
    check(f"{fn}: the version line never outgrows the product's cap",
          vsz <= sz + 1e-9, True)
    dt, dsz, _bx, _sy = T.detail_placement(p, d)
    dcap_em, dasc_em = T._metrics(T.DETAIL_FONT)
    band = d.calHeightIncrement - T.DETAIL_BASELINE_X
    depth = d.calPusherTotalDepth
    wpc = T._width_per_cap(dt, T.DETAIL_FONT)
    dfit = T.font_size_for_cap(
        min((band - T.LOGO_MARGIN * band) / (dasc_em / dcap_em),
            (depth - 2 * T.LOGO_MARGIN * depth) / wpc), T.DETAIL_FONT)
    record("Pusher", fn, "detail", dfit, dsz, T.DETAIL_FONT, False)

print("=== boxes ===")
for _folder, fn, p in B.box_catalogue():
    d = D.derive(p)
    y0, y1 = box.card_area(p, d)
    span = y1 - y0
    logo_len = span - box.LOGO_MARGIN - box.logo_margin(p, d)
    ms = T.fit_size(d.calModelName, span - box.MODEL_MARGIN)
    ls = T.fit_size(d.ProductName, logo_len)
    cs = T.fit_size(d.calCapacityLabel, logo_len)
    lsf = T.floored(ls)
    for line, txt, fitted, final in (
            ("model+game", d.calModelName, ms, T.floored(ms)),
            ("product", d.ProductName, ls, lsf),
            ("capacity", d.calCapacityLabel, cs, T.floored(cs)),
            ("version", d.calVersion, box.VERSION_CAP * ls,
             min(lsf, T.floored(box.VERSION_CAP * ls)))):
        record("Box", fn, line, fitted, final, T.LOGO_FONT, False)
        box._fits(txt, final, span)          # raises DoesNotFit if not

print("=== lids ===")
for _game, fn, p in B.lid_catalogue():
    d = D.derive(p)
    record("Lid", fn, "product", T.fit_size(d.ProductName, lid.logo_width(d)),
           lid.logo_size(d), T.LOGO_FONT, True)
    for line, cap in (("model", lid.CAP_MODEL), ("line", lid.CAP_LINE)):
        record("Lid", fn, line, cap / T.CAP, cap / T.CAP, T.LOGO_FONT, True)

print("=== holders ===")
for _folder, fn, p, first in B.holder_catalogue():
    d = D.derive(p)
    s = holder.text_size(p, d, first)
    record("Holder", fn, "name", s, s, T.LOGO_FONT, False)
    record("Holder", fn, "capacity", s, s, T.DETAIL_FONT, False)

print("=== token holders ===")
for item in B.token_holder_catalogue():
    _folder, fn, p, half = item[0], item[1], item[2], item[3]
    d = D.derive(p)
    s = token_holder.text_size(p, d, half)
    record("TokenHolder", fn, "model", s, s, T.LOGO_FONT, False)

print("=== toppers ===")
seen = set()
for item in B.topper_catalogue():
    _folder, fn, p = item[0], item[1], item[2]
    d = D.derive(p)
    key = fn.split(" ", 2)[-1]           # `M10-Un.3mf` — one per size
    if key in seen:
        continue
    seen.add(key)
    fitted = topper.cap_band(p, d) / topper.BAND_EM
    final = topper.font_size(p, d)
    record("Topper", key, "name", fitted, final, topper.FONT, False)
    _x, rear, front = topper.face_datum(p, d)
    check(f"Topper {key}: the cap band stays inside the flat",
          final * topper.BAND_EM <= (front - rear) + 1e-9, True)

print("\n=== every line is at or above its floor ===")
below = [(pt, fn, ln, round(sz, 3), round(fl, 3))
         for pt, fn, ln, sz, fl in placed if sz < fl - 1e-9]
check(f"{len(placed)} lines placed, none under its floor", below, [])

print("\n=== and the floor binds exactly where it is known to ===")
want = sorted([
    ("Pusher", "Pusher 2x12-30-Un.3mf", "version"),
    ("Pusher", "Pusher 2x12-30-Sl.3mf", "version"),
    ("Pusher", "Pusher 2x18-40-Un.3mf", "version"),
    ("Pusher", "Pusher 2x18-40-Sl.3mf", "version"),
    ("Pusher", "Pusher 3x6-Un.3mf", "detail"),
    ("Box", "Box S4.7.7.20-Un.3mf", "version"),
    ("Box", "Box S2.40.12-30.32-Un.3mf", "model+game"),
    ("Box", "Box S2.40.12-30.32-Un.3mf", "version"),
    ("Box", "Box L3.18.6.20-Sl.3mf", "version"),
    ("Box", "Box L3.18.6.20-Un.3mf", "model+game"),
    ("Box", "Box L3.18.6.20-Un.3mf", "product"),
    ("Box", "Box L3.18.6.20-Un.3mf", "capacity"),
    ("Box", "Box L3.18.6.20-Un.3mf", "version"),
    ("Box", "Box S3.15.10.20-Un.3mf", "version"),
    ("Topper", "M10-Un.3mf", "name"),
    ("Topper", "S10-Un.3mf", "name"),
])
got = sorted(set(raised))
check("the raised lines", got, want)
for line in sorted(set(got) - set(want)):
    print(f"      NEW: {line}")
for line in sorted(set(want) - set(got)):
    print(f"      GONE: {line}")

print("\nPASS" if not fails else "\nFAIL: " + ", ".join(fails))
sys.exit(1 if fails else 0)
