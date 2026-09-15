#!/usr/bin/env python3
"""One-slot cascades for PRINTING a prototype release change before the
catalogue moves — the 7.2f `ribs_forward` test.

    .venv/bin/python -m cad.testkit              # every kit, to build/testkits/
    .venv/bin/python -m cad.testkit --kit A

A kit is a real cascade at HorizontalSlots 1 with two or three risers, built
from the same part modules as the catalogue at `CURRENT`, so what it proves
is what the catalogue would print — cut down to what the lips need: no lattice
windows, they cost print time, and not the full height. It ships:

* the **Box** without label holders or lattice, SLICED: everything from
  `FLOOR_Z` up, standing on its own real floor — the box's floor with its
  pusher slot, lifted to `FLOOR_Z` — so the ribs, the divider panel, the
  lip and the rim are the catalogue's and the box is `BoxHeight - FLOOR_Z`
  tall. Its flat lip biting the front holder's wall by `box.LIP_BITE` is the
  thing to feel on the way in;
* the **Holder** and **RearHolder**, no lattice, no text, sliced at the
  height that puts their cut face on that floor exactly where their base
  would have been, so they ride the ribs and sit on the treads as the
  catalogue's do, with their lips, rests and finger scallops whole;
* the **Pusher**, whole — it stands in the stub below the box's floor;
* a **stub** of the lid: the lid's floor and rim cut off `STUB_H` above the
  floor, with the pusher sockets on it. The box stands in it as it stands in
  the lid, and the pusher stands in the socket and rises through the box's
  floor slot, so the tread fit is checked without a lid a one-slot cascade
  cannot build (its text and sockets do not fit) and does not need.

Everything is named with a catalogue role (`layout.ROLES`) and the whole kit
is packed onto ONE plate of the smallest bed it fits, with its prime tower
placed as `cad.layout` places a cascade's. What to look for on the print is
in `spec/BOX.md`, "The ribs move forward".
"""
import argparse
import math
import sys
from pathlib import Path

from build123d import Box, Location

from . import layout as LY
from . import mesh3mf
from . import params as P
from . import project as PJ
from . import revisions as R
from .parts import box as box_part
from .parts import holder as holder_part
from .parts import lid as lid_part
from .parts import pusher as pusher_part
from .refuse import refuse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "testkits"

STUB_H = 8.0        # the lid stub's rim, above the lid's outer floor
# Where the sliced box's floor goes (its underside), in the box's own Z.
# Above the lattice's top row (69.5 would be, but the lattice is off) and
# far enough below the front holder's wall top that the wall has 10+ mm
# below its rest on the flattest kit: kit A's front wall tops out at 28.9
# in the holder's frame, and the holder is cut at FLOOR_Z + 2 - 47.25.
FLOOR_Z = 60.0

# (label, why, Primary). LabelHolders 0: the label holders test nothing here.
KITS = {
    # The flattest one-slot cascade whose box builds: the height increment
    # is 16 at two or three risers, so the slope is 16/sd, and a one-slot
    # box's final edge round fails once the pusher is longer than about 20
    # (16 cards a slot at two risers, 10 or 12 at three). A slope of 1.67 is
    # steeper than Three Expansions' 1.22, but the lip's reach in Y and its
    # seat are the same at any slope; only its height on the ramp changes.
    "A": ("flat", "the flattest one-slot kit that builds: 12 sleeved cards a "
                  "slot, two risers, slope 1.67",
          dict(HorizontalSlots=1, RisingSliders=2, FrontPocketCardCapacity=12,
               CardsPerSlidingSlot=12, isFirstSlidingSlotOverride=0,
               FirstSlidingSlotCards=12, isSleeved=1, MatPocket=0,
               GameName="Dominion", LabelHolders=0)),
    "B": ("steep", "the tallest box lip and the shortest tread: Compile's 7 "
                   "unsleeved cards a slot, slope about 3.5",
          dict(HorizontalSlots=1, RisingSliders=3, FrontPocketCardCapacity=7,
               CardsPerSlidingSlot=7, isFirstSlidingSlotOverride=0,
               FirstSlidingSlotCards=7, isSleeved=0, MatPocket=0,
               GameName="Compile", LabelHolders=0)),
}


def primary(key, version=R.CURRENT):
    """The kit's Primary at `version`."""
    if key not in KITS:
        refuse(f"unknown kit {key!r}; one of {sorted(KITS)}")
    return P.Primary(**KITS[key][2], Version=version)


def _above(z):
    """A slab of everything above `z`."""
    return Box(2000.0, 2000.0, 1000.0).moved(Location((0, 0, z + 500.0)))


def _below(z):
    return Box(2000.0, 2000.0, 1000.0).moved(Location((0, 0, z - 500.0)))


def sliced_box(d):
    """The box from FLOOR_Z up, on its own floor: the real floor (the bottom
    `floor_top` of the box — floor, pusher slot, side floors, and the walls'
    lowest millimetres) lifted to FLOOR_Z under the rest. Stood on the bed
    at z 0."""
    box = box_part.build(d, lattice=False)
    ft = box_part.floor_top(d)
    floor = (box & _below(ft)).moved(Location((0, 0, FLOOR_Z)))
    upper = box & _above(FLOOR_Z + ft)
    return upper.fuse(floor).moved(Location((0, 0, -FLOOR_Z)))


def holder_cut_z(d):
    """Where a holder is cut, in its own frame: the sliced floor's top is
    where its base was, so `FLOOR_Z + floor_top` in the box is that Z."""
    from . import assembly as A
    return FLOOR_Z + box_part.floor_top(d) - A.holder_closed(d, 0).origin[2]


def sliced_holder(d, first, rear):
    """The holder from `holder_cut_z` up, stood on its cut face."""
    h = holder_part.build(d, first, text=False, rear=rear, lattice=False)
    z = holder_cut_z(d)
    return (h & _above(z)).moved(Location((0, 0, -z)))


def stub(d):
    """The lid's floor and sockets with its rim cut off STUB_H up, in the
    lid's own frame — what `lid.build` makes before its text, grooves and
    logo, kept to the part that locates a box and stands a pusher."""
    part = lid_part.sockets(d, lid_part.shell(d))
    keep = Box(1000.0, 1000.0, STUB_H).moved(Location((0, 0, STUB_H / 2)))
    return part & keep


def solids(d):
    """[(object name, shape)] — the kit's parts, each named with the role
    `layout.role` reads so the plates come out as a cascade's."""
    from . import derive as D
    return [("Box", sliced_box(d)),
            ("Holder", sliced_holder(d, False, False)),
            ("RearHolder", sliced_holder(d, False, True)),
            ("Pusher", pusher_part.build(d)),
            ("Lid stub", stub(d))]


def objects(d):
    """The kit as `project.Obj`s, meshed and checked closed."""
    objs = []
    for name, shape in solids(d):
        verts, tris = mesh3mf.triangulate(shape)
        bad = mesh3mf.faults(tris)
        if bad and bad[0]:
            refuse(f"{name}: open mesh ({bad})")
        objs.append(PJ.Obj(name, [PJ.Part(name, verts, tris, PJ.BODY)],
                           source=f"testkit:{name}"))
    return objs


def one_plate(objs, name):
    """(bed, [Plate], [Placement]) with every object on one plate — a kit is
    printed in one go, not by role as a cascade is. `layout.plate` packs it
    and finds the tower's home exactly as it does for a cascade's plate."""
    bed = LY.choose_bed(objs)
    ps = LY.profile(bed)
    ex = [tuple(map(float, p.split("x"))) for p in ps.get("bed_exclude_area", [])]
    exclude = (LY.rect_obb(min(p[0] for p in ex), min(p[1] for p in ex),
                           max(p[0] for p in ex), max(p[1] for p in ex)) if ex else None)
    placed, at = LY.plate(objs, list(range(len(objs))), bed, ps, exclude, name)
    return bed, [PJ.Plate(name, at)], [PJ.Placement(i, 1, ob.cx, ob.cy, math.degrees(ob.theta))
                                        for i, ob in placed]


def make(key, out_dir=OUT, version=R.CURRENT):
    """Write kit `key`'s project. Returns (path, notes)."""
    from . import derive as D
    d = D.derive(primary(key, version))
    objs = objects(d)
    bed, plates, places = one_plate(objs, f"Test kit {key}")
    label, why, _p = KITS[key]
    # No model in the name: a one-slot box has no size letter.
    path = Path(out_dir) / f"Test kit {key} {label} v{d.Version}.3mf"
    path.parent.mkdir(parents=True, exist_ok=True)
    PJ.write(path, bed, objs, plates, places,
             title=f"Card Cascade test kit {key} ({label}) v{d.Version}",
             metadata={"cardcascade:model": d.calModelName,
                       "cardcascade:version": d.Version,
                       "cardcascade:testkit": f"{key}: {why}"})
    return path, [f"{bed} x{len(plates)}", f"{len(objs)} objects",
                  f"box {box_part.box_width(d):.1f} x {box_part.box_depth(d):.1f} x {d.BoxHeight - FLOOR_Z:g} (sliced from {FLOOR_Z:g})",
                  f"slope {holder_part.slant_slope(d, False):.3f}"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit", choices=sorted(KITS), action="append")
    ap.add_argument("--out", default=OUT, type=Path)
    ap.add_argument("--version", default=R.CURRENT, choices=R.RELEASES)
    args = ap.parse_args(argv)
    for key in args.kit or sorted(KITS):
        path, notes = make(key, args.out, args.version)
        print(f"{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {'; '.join(notes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
