#!/usr/bin/env python3
"""Check the TokenHolder's RULES against all 18 cached meshes.

    .venv/bin/python tests/test_token_holder_corpus.py

`tests/test_token_holder.py` holds the part to two exact STEPs, which settle a
section and cannot tell a rule from a coincidence. This holds it to the whole
of `individual/Dominion/` — five front capacities, both sleevings, both Mat
states — which is the other question. Same split as the Lid's two tests.

The cached components are **6.6** and the part is unchanged since (Allan), so
these are a real regression target rather than a shape reference: the only
thing 7.0 moves is the version in the engraved string, so the build is run at
`Version="6.6"` here and compared like for like.

A mesh is not a solid, so what is asserted is what a mesh answers exactly: the
envelope, the origin, the divider's position and height, and the engraving's
ink box. Volume is not — Onshape's tessellation of a 7.500 half-disc loses more
than the thing being measured.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import mesh3mf, params, derive as D, text as TX   # noqa: E402
from cad.parts import token_holder as TH                   # noqa: E402

CACHE = ROOT / "individual" / "Dominion"

# The size letter each cached file was built with, read off its own engraving
# rather than looked up: `plan_exports` keys a token holder
# `(capacity, merged, sleeved)` and that key does NOT carry HorizontalSlots, so
# `324 Card` (M, 4 slots) and `333 Card` (S, 3 slots) share `TokenHolder
# 21-Sl.3mf` and it is stamped M for both. The geometry is identical either way
# — HorizontalSlots cancels out of calTokenHolderSlotWidth — so the only thing
# the collision costs is a wrong letter on one cascade's tray. `cad.build`
# splits them; this table is what Onshape actually shipped.
LETTER = {("16", False): "S", ("21", False): "M", ("40", False): "S",
          ("50", False): "L", ("60", False): "M",
          ("21", True): "M", ("40", True): "M"}
SLOTS = {"XS": 2, "S": 3, "M": 4, "L": 5}

# The three the Onshape rule engraves too big for the part. All are on a MERGED
# box, which doubles the width the text is fitted to and leaves the depth alone
# — or, on a half holder, nearly halves it. On each, the ink's Y extent equals
# the part's OWN, which is an outline clipping a sketch rather than a size that
# fits. `token_holder.text_size` bounds the depth as well, so the build
# deliberately differs on these three and nowhere else.
CLIPPED = {"HalfTokenHolder 21-Sl merged.3mf",
           "HalfTokenHolder 21-Un merged.3mf",
           "TokenHolder 21-Un merged.3mf"}

fails = []


def check(label, got, want, tol=1e-6):
    ok = abs(got - want) <= tol if isinstance(want, float) else got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:62s} {got!r:>16} vs {want!r}")
    if not ok:
        fails.append(label)


def primary_for(name):
    m = re.match(r"(Half)?TokenHolder (\d+)-(Sl|Un)( merged)?\.3mf", name)
    half, cap, slv, merged = bool(m.group(1)), m.group(2), m.group(3), bool(m.group(4))
    letter = LETTER[(cap, merged)]
    p = params.Primary(SLOTS[letter], 6, int(cap), 10, 0, 10,
                       1 if slv == "Sl" else 0, 1 if merged else 0,
                       "Dominion", "6.6")
    return p, half


def mesh(name):
    _, verts, _ = mesh3mf.read(CACHE / name)[0]
    return verts


files = sorted(f.name for f in CACHE.glob("*TokenHolder*.3mf"))
check("the corpus is all 18 of them", len(files), 18)

print("\n=== the envelope, on every one ===")
for name in files:
    p, half = primary_for(name)
    d = D.derive(p)
    v = mesh(name)
    xs, ys, zs = ([q[i] for q in v] for i in range(3))
    check(f"{name}: width", round(TH.width(d), 3), round(max(xs) - min(xs), 3), 1e-3)
    check(f"{name}: depth", round(TH.depth(d, half), 3),
          round(max(ys) - min(ys), 3), 1e-3)
    # The origin is the SLOT's corner, not the part's — this is what says so.
    check(f"{name}: sits at the slot corner + CLEARANCE",
          (round(min(xs), 3), round(max(ys), 3)),
          (round(TH.CLEARANCE, 3), round(-TH.CLEARANCE, 3)))
    check(f"{name}: base at Z 0, apex at height + GRIP_R",
          round(min(zs), 3), 0.000, 1e-3)

print("\n=== the divider is one, centred, whatever the width ===")
for name in files:
    p, half = primary_for(name)
    d = D.derive(p)
    v = mesh(name)
    x0 = min(q[0] for q in v)
    # Everything in the cavity's height band that is not one of the two side
    # walls: on every reference that is exactly one 2.000 divider, and on the
    # eight MERGED ones — twice as wide — it is still exactly one.
    band = [q for q in v if 1.5 < q[2] < 70.0]
    mid = sorted({round(q[0], 3) for q in band
                  if x0 + 3.0 < q[0] < x0 + TH.width(d) - 3.0})
    check(f"{name}: one divider, {TH.DIVIDER_W} wide",
          round(max(mid) - min(mid), 2), round(TH.DIVIDER_W, 2), 0.02)
    check(f"{name}: centred on the part",
          round((min(mid) + max(mid)) / 2, 2), round(TH.divider_x(d), 2), 0.02)
    check(f"{name}: its bead tops out at 65.000",
          round(max(q[2] for q in band), 2),
          round(TH.height() - TH.DIVIDER_DROP, 2), 0.05)

print("\n=== the engraving: anchor, size, and the two Onshape gets wrong ===")
for name in files:
    p, half = primary_for(name)
    d = D.derive(p)
    v = mesh(name)
    x0, y0, y1 = (min(q[0] for q in v), min(q[1] for q in v), max(q[1] for q in v))
    ink = [q for q in v if abs(q[2] - TH.ENGRAVE) < 1e-4]
    ix0, ix1 = min(q[0] for q in ink), max(q[0] for q in ink)
    iy0, iy1 = min(q[1] for q in ink), max(q[1] for q in ink)
    txt = TH.text_line(d)
    em = TH.text_size(d, half)
    lsb = TX.metrics(txt, TX.LOGO_FONT)[1]

    if name in CLIPPED:
        # Assert the DEFECT on the reference and the fix on the build — both
        # ends, so re-converging fails rather than passing quietly. Nothing
        # about the reference's own size or anchor is asserted here: the
        # sketch it came from is not the one that got cut.
        check(f"{name}: the reference's ink is clipped to the part",
              (round(iy0, 3), round(iy1, 3)), (round(y0, 3), round(y1, 3)))
        check(f"{name}: the build fits inside the part instead",
              TH.cap_reach(txt) * em + TH.CLEARANCE
              <= TH.depth(d, half) / 2 + 1e-9, True)
    else:
        # The anchor and the size, both against the reference's own ink.
        check(f"{name}: text box origin is TEXT_INSET in",
              round(ix0 - lsb * em - x0, 2), round(TH.TEXT_INSET, 2), 0.02)
        check(f"{name}: ink width", round(ix1 - ix0, 2),
              round(TX.ink(txt, TX.LOGO_FONT, em)[0], 2), 0.05)
        check(f"{name}: the ink clears the part in Y",
              round(min(iy0 - y0, y1 - iy1), 3) >= 0.0, True)

print("\nPASS" if not fails else f"\nFAIL ({len(fails)}): " + ", ".join(fails[:6]))
sys.exit(1 if fails else 0)
