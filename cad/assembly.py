"""Where every part sits in a whole cascade.

`derive.py` is the only place a formula lives; this is the only place a
PLACEMENT lives. Component modules build a part in its own frame and know
nothing about any other part; everything that says how two parts meet is here,
and it is derived from `derive.py` and the part modules rather than measured
into a constant. `spec/ASSEMBLY.md` is the record, and says what settles each.

The assembly frame is the BOX's part frame — X width, 0 at the centre; Y depth,
+Y toward the back; Z, 0 at the bed — so the Box is placed by the identity,
which is what `cad/build.py` already assumes ("the part studio's origin is the
assembly's"). The corpus cannot supply a frame: `individual/*/_raw/Assembly
*.3mf` carries `<components>` transforms, but they are the print layout, and
`assembly_split.py` discards them.

Nothing here imports build123d, so the placements are pure arithmetic and are
tested on their own — the same split `derive.py` has. `Place.location()` builds
the build123d `Location` on demand for a caller that has one.
"""
from . import derive as D
from . import lock as L
from .parts import box as box_part
from .parts import holder as holder_part
from .parts import pusher as pusher_part

CLOSED = "closed"          # on the shelf, lid off
CLOSED_LID = "closed-lid"  # on the shelf, lid on
PLAY = "play"              # cascaded, lid underneath
STATES = (CLOSED, CLOSED_LID, PLAY)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


class Place:
    """A rigid placement: part coordinates -> assembly coordinates.

    Given as the images of the part's X and Z axes plus an origin, because that
    is how every mate in this file reads — "the rise runs up the box's Z, the
    tabs point forward" — and because it is exactly what build123d's `Plane`
    takes, so the B-rep and the mesh paths get their transform from one place.
    Y follows as `z_dir x x_dir`, which is what makes a placement a ROTATION and
    not a mirror; every mate here turns out to be one.

    Every axis image in this module is a signed unit vector, so the matrix is
    exact integers and a placement introduces no arithmetic error of its own.
    """
    __slots__ = ("x_dir", "y_dir", "z_dir", "origin")

    def __init__(self, x_dir=(1, 0, 0), z_dir=(0, 0, 1), origin=(0.0, 0.0, 0.0)):
        self.x_dir, self.z_dir, self.origin = x_dir, z_dir, origin
        self.y_dir = _cross(z_dir, x_dir)

    def __call__(self, p):
        """Place one point."""
        x, y, z = p
        return tuple(self.origin[i] + x * self.x_dir[i] + y * self.y_dir[i]
                     + z * self.z_dir[i] for i in range(3))

    def as_3mf(self):
        """3MF's twelve numbers. Rows are the axis images; the translation is
        in METRES, because that is the unit the file declares."""
        rows = (self.x_dir, self.y_dir, self.z_dir)
        return " ".join(
            [f"{n:g}" for r in rows for n in r]
            + [f"{n / 1000:.8f}" for n in self.origin])

    def location(self):
        """The same placement as a build123d `Location`, for the B-rep path."""
        from build123d import Location, Plane, Vector
        return Location(Plane(origin=Vector(*self.origin),
                              x_dir=Vector(*self.x_dir),
                              z_dir=Vector(*self.z_dir)))

    def __repr__(self):
        return (f"Place(x={self.x_dir}, z={self.z_dir}, "
                f"origin=({', '.join(f'{n:.3f}' for n in self.origin)}))")


IDENTITY = Place()


# --- the Box ---------------------------------------------------------------

def box(p, d):
    """The Box IS the frame."""
    return IDENTITY


# --- the Pusher, stored in the rear ----------------------------------------
#
# On edge and upright: the rise runs up the box's Z, the depth across its
# WIDTH — `#dBackSlotWidth` is `calPusherTotalDepth + 4.000` measured along X —
# and the plate's thickness into the 3.200 slot band. All three axis images are
# FORCED, which is why this reads as one placement and not a family:
#
#   +X (rise, 0 at the leading edge where the tabs are) -> -Z, because the tabs
#      engage the rim cutouts at the TOP of the box;
#   +Z (the face the tabs stand proud of)               -> -Y, because those
#      cutouts are cut through the 1.300 INNER back wall, which is forward of
#      the slot band;
#   +Y                                                  -> +X by right-handedness.
#
# The origin then follows from three fits, and each lands on a number the
# standard already states.

PLATE_SLOP = (L.BOX_SLOT_DEPTH - L.PLATE) / 2      # 0.100 a side, nominal


def pusher_stored(p, d, k):
    """The `k`th stored pusher, left to right.

    * **Z** — `origin_z = BoxHeight`, so the pusher HANGS by its tabs with its
      top flush at the rim and the tab's 5.000 fills the cutout's
      `100.000..105.000` exactly. `box.pusher_rest` is then a CATCH 0.500 below
      it, not a shelf: `min(25.000, BoxHeight - H - 0.500)`. Innovation's
      87.000 pusher is where the `min` bites, and only the flush reading closes
      the arithmetic.
    * **X** — the tabs sit at part `y = -D/2 +- s` and the box's rim cutouts at
      `slot_centre +- s`, so part `y = -D/2` lands on the slot centre.
    * **Y** — the plate centred in the slot band, which is `PLATE_SLOP` a side.
    """
    depth = d.calPusherTotalDepth
    centre = box_part.pusher_slots(p, d)[k]
    y0, y1 = box_part.slot_band(p, d)
    return Place(x_dir=(0, 0, -1), z_dir=(0, -1, 0),
                 origin=(centre + depth / 2, y1 - PLATE_SLOP, d.BoxHeight))


# --- the Holder ------------------------------------------------------------
#
# The holder's own axes already run the box's way: X across, Y with the REAR
# face at 0 and the body toward the front, Z up. So it is a translation.

def holder_rib(p, d, j):
    """(y, depth, first) for riser `j`, back to front.

    `box.slider_ribs` is back to front and puts the odd one — the
    `calFirstSliderDistance` rib — LAST, which is the frontmost. That is the
    rib the deeper `FirstHolder` takes, and only when the row has an override.
    """
    ribs = box_part.slider_ribs(p, d)
    first = bool(p.isFirstSlidingSlotOverride) and j == len(ribs) - 1
    y0, y1 = ribs[j]
    return (y0 + y1) / 2, holder_part.holder_depth(p, d, first), first


def holder_x(p, d):
    """The X translation. The holder's origin is its FIRST compartment's centre,
    so centring it in the box is a shift of half the compartment span — and it
    then clears by `(11.100 - 9.800)/2 = 0.650` a side, the holder being
    `calSlotwidth * H + 9.800` wide in an inner box of `calSlotwidth * H
    + 11.100`."""
    return -(p.HorizontalSlots - 1) * d.calSlotwidth / 2


def holder_z_base(d):
    """Where the holder's own Z 0 goes if its base is to sit at Z 0 here. Its
    base is at `-(CardHeight - 1.500)/2` in its own frame."""
    return holder_part.half_height(d)


def holder_closed(p, d, j):
    """Riser `j` on the floor, its side slots over rib `j`.

    Resting on the two `side_floor` strips, which `box.side_floor` says is what
    they are left standing for. The side slot is centred on the holder's own
    depth, so a holder centred on its rib is centred on its card slot too, and
    consecutive holders clear by `calSliderDistance - depth = CardHolderGap`.
    """
    y, depth, _first = holder_rib(p, d, j)
    return Place(origin=(holder_x(p, d), y + depth / 2,
                         D.WallThickness + holder_z_base(d)))


def holders(p, d):
    """[(j, first)] — one per riser, back to front."""
    n = len(box_part.slider_ribs(p, d))
    return [(j, holder_rib(p, d, j)[2]) for j in range(n)]


def pushers(p, d):
    """How many pushers a cascade stores, and which slot each takes."""
    return list(range(box_part.pusher_slot_count(p)))
