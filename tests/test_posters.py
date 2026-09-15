"""The description posters: the spec resolves for every cascade, every
asset it names exists, and a poster comes out at 4000x3000 under the tracked
name. No Blender: the picture is the placeholder.

    .venv/bin/python tests/test_posters.py
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import make_posters as MP                     # noqa: E402
import postercommon as PC                     # noqa: E402
from cad import cascade as CC                 # noqa: E402

fails = []


def check(label, got, want=True):
    ok = got == want
    print(f"  {'ok ' if ok else 'FAIL'}  {label}" + ("" if ok else f"  ({got!r} != {want!r})"))
    if not ok:
        fails.append(label)


print("=== assets ===")
for name in ("ORB", "MONO_B", "MONO_R", "INTER_R", "INTER_B"):
    check(f"face {name} exists", Path(getattr(PC, name)).exists())
for game, path in PC.GAME_LOGOS.items():
    check(f"{game} logo exists", Path(path).exists())

spec = MP.load_spec()
rows = CC.catalogue()
check("every parts.csv cascade is catalogued", len(rows) > 40)

print("\n=== the spec resolves for every cascade ===")
glyphs = set()
for row, d in rows:
    s = MP.spec_for(spec, row, d)
    v = MP.values(row, d, s)
    label = f"{d.GameName}/{CC.title(row, d)}"
    try:
        for value, caption in s.get("stats", []):
            MP.T(value, v), MP.T(caption, v)
        for _icon, caption, value, unit in s["cells"]:
            MP.T(caption, v), MP.T(value, v), MP.T(unit, v)
        if s.get("band"):
            MP.T(s["band"]["title"], v)
            for entry in s["band"].get("sets", []):
                glyphs.add(entry[0])
                check(f"{label}: set modifier {entry[1:2]} is known",
                      (list(entry) + [None])[1] in (None, "half", "x2"))
        for slv, entry in (s.get("photo") or {}).items():
            p = entry if isinstance(entry, str) else entry[0]
            check(f"{label}: spec photo {p} exists", (ROOT / p).exists())
        check(f"{label}: templates resolve", True)
    except MP.Refused as e:
        check(f"{label}: templates resolve", str(e), "")
    check(f"{label}: model_ref has no bare dots", "." not in v["model_ref"])
    check(f"{label}: printer phrase", v["printer"].endswith("3D PRINTER"))
for g in sorted(glyphs):
    check(f"glyph {g} exists", (MP.GLYPHS / f"{g}.png").exists())

print("\n=== the sizes are the CAD's ===")
by_name = {(r["Game"], r["Short name"], d.isSleeved): (r, d) for r, d in rows}
r, d = by_name[("Innovation", "4 Ages 5 Expansions", 1)]
v = MP.values(r, d, MP.spec_for(spec, r, d))
check("Innovation 4 Ages sleeved width", v["ext_w"], "295")
check("Innovation 4 Ages sleeved depth", v["ext_d"], "83.2")
check("Innovation 4 Ages sleeved model", v["model_ref"], "M5·15·15·62·Sl")
check("Innovation 4 Ages sleeved needs the large bed", v["printer"], "LARGE 3D PRINTER")
r, d = by_name[("Innovation", "4 Ages 5 Expansions", 0)]
v = MP.values(r, d, MP.spec_for(spec, r, d))
check("...and its unsleeved twin the standard one", v["printer"], "STANDARD 3D PRINTER")
r, d = by_name[("Dominion", "246 Card", 1)]
v = MP.values(r, d, MP.spec_for(spec, r, d))
check("Dominion 246 slot string carries the deeper first riser", v["slot_cards"], "12/30")
r, d = by_name[("Food Chain Magnate", "264 Card", 0)]
v = MP.values(r, d, MP.spec_for(spec, r, d))
check("FCM grid counts the front pocket as a row", v["grid"], "4x5")

print("\n=== knockout ===")
with tempfile.TemporaryDirectory() as tmp:
    im = Image.new("RGB", (400, 300), (252, 250, 246))
    im.paste((40, 60, 120), (100, 80, 300, 220))
    p = Path(tmp) / "white.jpg"
    im.save(p, quality=92)
    cut = MP.knockout(p)
    a = np.asarray(cut.getchannel("A"))
    check("knockout crops to the subject", abs(cut.width - 200) <= 6 and abs(cut.height - 140) <= 6)
    check("knockout: subject opaque", int(a[a.shape[0] // 2, a.shape[1] // 2]) == 255)

print("\n=== a poster per cascade ===")
with tempfile.TemporaryDirectory() as tmp:
    for row, d in rows:
        s = MP.spec_for(spec, row, d)
        img = MP.draw_poster(row, d, s, MP.placeholder("test"))
        check(f"{d.GameName}/{CC.title(row, d)}: 4000x3000 RGB",
              (img.size, img.mode), ((4000, 3000), "RGB"))
        out = MP.output_path(row, d, tmp)
        check(f"...named by the tracked name", out.name,
              CC.filename(row, d)[:-4] + ".png")



print("\n=== cad.scene: the card plan ===")
from cad import scene as SC, assembly as A, assemble as AS   # noqa: E402

for row, d in rows:
    label = f"{d.GameName}/{CC.title(row, d)}"
    rs = SC.render_spec(spec, row, d)
    try:
        plan = SC.card_plan(d, rs)
    except SC.Refused as e:
        check(f"{label}: card plan", str(e), "")
        continue
    slots = {s for s, _cap in SC.slots_row_major(d)}
    if not rs.get("stacks", True):
        check(f"{label}: stacks off leaves the slots empty", plan, [])
        rs = dict(rs, stacks=True)
        plan = SC.card_plan(d, rs)
    check(f"{label}: every slot filled once",
          sorted(str(p["slot"]) for p in plan), sorted(str(s) for s in slots))
    check(f"{label}: every stack named and counted",
          all(str(p["text"]) and p["count"] >= 1 for p in plan))
    if d.GameName == "Innovation" and rs.get("columns"):
        pocket = [p for p in plan if p["slot"][0] is None and p["slot"][1] == 0][0]
        check(f"{label}: Base in the front pocket", pocket["expansion"], "Innovation")
        order = SC.topper_order(d, rs)
        front = [p for p in plan if p["slot"][1] == 0 and p["slot"][0] is not None]
        by_riser = {p["slot"][0]: p["expansion"] for p in front}
        check(f"{label}: toppers match the cards behind them",
              all(order[j] == by_riser[j] for j in by_riser if order[j] != "Blank"))
    check(f"{label}: label text", isinstance(SC.label_text(rs, row, d), str))

print("\n=== cad.scene: lid colours ===")
by_game = {}
for row, d in rows:
    by_game.setdefault(d.GameName, []).append(row)
for game, game_rows in by_game.items():
    lids = {}
    for row in game_rows:
        d = [dd for r, dd in rows if r is row][0]
        rs = SC.render_spec(spec, row, d)
        lids.setdefault((row["Short name"]), set()).add(SC.lid_colour(rs, row, d, game_rows))
    check(f"{game}: twins share a lid", all(len(v) == 1 for v in lids.values()))
    distinct = [next(iter(v)) for v in lids.values()]
    palette = SC.render_spec(spec, game_rows[0], [dd for r, dd in rows if r is game_rows[0]][0])["palette"]
    check(f"{game}: rows differ while the palette lasts",
          len(set(distinct[:len(palette)])), min(len(distinct), len(palette)))
check("Compile's lid is white, its inlays black",
      SC.scene_colours("#F4F4F2", [])["Lid Part"], SC.BLACK)
check("a dark lid takes white inlays and lid-coloured label text",
      (SC.scene_colours("#1F7A8C", [])["Lid Part"], SC.scene_colours("#1F7A8C", [])["Label Part"]),
      (SC.WHITE, "#1F7A8C"))

print(f"\n{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
