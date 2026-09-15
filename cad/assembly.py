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

Nothing here imports build123d — the part modules it takes its arithmetic
from are loaded on first use (`cad/lazy.py`) — so the placements are pure
arithmetic and are tested on their own, the same split `derive.py` has. `Place.location()` builds
the build123d `Location` on demand for a caller that has one.
"""
from . import derive as D
from . import lock as L
from .lazy import lazy

# The part modules, for their arithmetic — imported on first use, because
# importing one loads build123d (`cad/lazy.py`).
box_part = lazy(".parts.box", __package__)
holder_part = lazy(".parts.holder", __package__)

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

def box(d):
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


def pusher_stored(d, k):
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
    centre = box_part.pusher_slots(d)[k]
    _y0, y1 = box_part.slot_band(d)
    return Place(x_dir=(0, 0, -1), z_dir=(0, -1, 0),
                 origin=(centre + depth / 2, y1 - PLATE_SLOP, d.BoxHeight))


# --- the Holder ------------------------------------------------------------
#
# The holder's own axes already run the box's way: X across, Y with the REAR
# face at 0 and the body toward the front, Z up. So it is a translation.

def holder_rib(d, j):
    """(y, depth, first) for riser `j`, back to front.

    `box.slider_ribs` is back to front and puts the odd one — the
    `calFirstSliderDistance` rib — LAST, which is the frontmost. That is the
    rib the deeper `FirstHolder` takes, and only when the row has an override.
    """
    ribs = box_part.slider_ribs(d)
    deep = 0 if d.isDeepSlotAtBack else len(ribs) - 1   # `Deep slot = back`
    first = bool(d.isFirstSlidingSlotOverride) and j == deep
    y0, y1 = ribs[j]
    return (y0 + y1) / 2, holder_part.holder_depth(d, first), first


def holder_x(d):
    """The X translation. The holder's origin is its FIRST compartment's centre,
    so centring it in the box is a shift of half the compartment span — and it
    then clears by `(11.100 - 9.800)/2 = 0.650` a side, the holder being
    `calSlotwidth * H + 9.800` wide in an inner box of `calSlotwidth * H
    + 11.100`."""
    return -(d.HorizontalSlots - 1) * d.calSlotwidth / 2


def holder_z_base(d):
    """Where the holder's own Z 0 goes if its base is to sit at Z 0 here. Its
    base is at `-(CardHeight - 1.500)/2` in its own frame."""
    return holder_part.half_height(d)


def holder_closed(d, j):
    """Riser `j` on the floor, its side slots over rib `j`.

    Resting on the two `side_floor` strips, which `box.side_floor` says is what
    they are left standing for. The side slot is centred on the holder's own
    depth, so a holder centred on its rib is centred on its card slot too, and
    consecutive holders clear by `calSliderDistance - depth = CardHolderGap`.

    The Z datum is the BOX's floor — `box.floor_top`, not `WallThickness`.
    The two agree before 7.1 and part company at it, where the floor is 2.000
    and the wall stays 1.600, and a holder placed on the wall's thickness would
    then sit 0.400 inside the floor it rests on.
    """
    y, depth, _first = holder_rib(d, j)
    return Place(origin=(holder_x(d), y + depth / 2,
                         box_part.floor_top(d) + holder_z_base(d)))


def holders(d):
    """[(j, first)] — one per riser, back to front. `first` is the DEEP
    holder's flag (its depth and slant); which riser is the REAR holder, the
    one built without lips, is `rear_of`."""
    n = len(box_part.slider_ribs(d))
    return [(j, holder_rib(d, j)[2]) for j in range(n)]


def rear_of(d, j):
    """Is riser `j` the RearHolder — the rearmost, built without rear lips
    (`rev.rear_holder`)? Riser 0 is the back one."""
    return bool(d.rev.rear_holder) and j == 0


def holder_kinds(d):
    """The distinct holders a cascade is built from, each with the risers it
    stands on: `[((first, rear), [j, ...])]`, back to front. Up to three —
    the RearHolder, the plain Holder, and the FirstHolder where the row
    overrides the first slot and the deep one is at the front."""
    out = {}
    for j, first in holders(d):
        out.setdefault((first, rear_of(d, j)), []).append(j)
    return sorted(out.items(), key=lambda kv: kv[1][0])


def pushers(d):
    """How many pushers a cascade stores, and which slot each takes.

    STORES, so it is `box.storage_slot_count` and not `pusher_slot_count`:
    the two are the same number on every catalogue box, and differ on a
    variant back (7.2g) — an `open` one stores none and a `notched` one more
    than the cascade ships. `pusher_stored` indexes `box.pusher_slots` by
    what this returns, so reading the cascade's count here would place a
    pusher in a slot that is not there.
    """
    return list(range(box_part.storage_slot_count(d)))


# --- the TokenHolder -------------------------------------------------------
#
# Its own frame's origin is already the SLOT's corner, not the part's — the
# part is the slot inset CLEARANCE on all four sides — so this placement is
# just where that slot is in the box. Its Y runs the opposite way to the box's
# (0 at the slot's FRONT edge, negative going BACK), so the placement is a 180
# degree turn about Z: with X alone flipped it would be a MIRROR, which no
# physical part is. That also settles what its "left edge of the slot" means —
# left as seen from behind, which is the box's +X end.

def token_slot_x(d):
    """The slot's +X end, which the turn makes its origin.

    Two expressions land on it and they agree exactly, which is what says it is
    the right datum: the last front divider's right edge plus
    `calTokenHolderSlotWidth`, and the right inner wall less
    `FrontPocketSidePaddingWidth`. Both give 94.250 on Dominion `S4.16.10`.
    Anchored on the DIVIDER, because that is the sketch's own datum — the
    lesson `spec/LID.md` records twice about a rule that fits and is still hung
    off the wrong thing.
    """
    return box_part.front_dividers(d)[-1] + d.calTokenHolderSlotWidth


def token_holder(d):
    """The FULL holder, dropped into the front pocket's last compartment.

    A merged cascade also ships a HALF one, and the two are ALTERNATIVES rather
    than both fitting: `spec/TOKENHOLDER.md` says a half holder is not half of
    a full one and that they are not meant to stack in depth, and they are the
    same width, so the slot takes one or the other. The FULL is placed because
    every token-holder row gets one; `cad.assemble --half` swaps in the HALF on
    a merged row. The PLACEMENT is the same either way — the origin is the
    slot's corner, and both parts are inset `CLEARANCE` into it — so only the
    mesh changes.

    It stands on the box's FLOOR, so its Z is `box.floor_top` — 2.000 from
    7.1, where `WallThickness` stays 1.600 (`holder_closed` says why).
    """
    front, _panel_front, _panel_back = box_part.pocket_span(d)
    return Place(x_dir=(-1, 0, 0), z_dir=(0, 0, 1),
                 origin=(token_slot_x(d), front, box_part.floor_top(d)))


# --- the front label -------------------------------------------------------

def label_width(d):
    """The label the front holder takes: `labelmaker`'s wide front, or the
    62 where the box is too narrow for it (`box.front_label_len`)."""
    return box_part.front_label_len(d) - box_part.LABEL_HOLDER_EXTRA


def label_plate(d):
    """A slide-in label as it sits in the front holder, for a render.

    `labelmaker.make_label` builds a label flat: x 0..width, y 0..22.2 (its
    height), z 0..1.2 (the white base, then the raised detail). Stood up with
    a quarter turn about X (height to +Z, thickness to -Y, the detail toward
    the viewer) it goes centred on the box's x, its bottom edge on the slot's
    floor (`LABEL_Z0 + LABEL_GROOVE_IN`), and its back face at the bottom of
    the groove — the pad stands LABEL_PROUD off the wall at `y = -BoxDepth/2`
    and the groove runs LABEL_GROOVE back into it."""
    y_back = -box_part.box_depth(d) / 2 - box_part.LABEL_PROUD + box_part.LABEL_GROOVE
    return Place(x_dir=(1, 0, 0), z_dir=(0, -1, 0),
                 origin=(-label_width(d) / 2, y_back,
                         box_part.LABEL_Z0 + box_part.LABEL_GROOVE_IN))


# --- the Lid ---------------------------------------------------------------
#
# The lid's frame relates to the box's by a plain Y shift and, when it is on,
# a half turn. `parts/lid.py` states both halves already: `lid_y = box_y -
# 2.250` in its docstring, and "a box height h arrives at WALL + BoxHeight - h
# in the lid's frame" in `closing_grooves`.

LID_Y = 2.250              # the box sits this far back of the lid


def lid_closed(d):
    """The lid inverted over the box.

        box = (lid_x, 2.250 - lid_y, (WallThickness + BoxHeight) - lid_z)

    A half turn about **Y**, and it is a choice rather than a derivation.

    The closing mechanism cannot say: the box's bump sits at box `y
    -1.750..6.250`, symmetric about the `2.250` both candidates turn around, so
    it arrives at lid `y -4.000..4.000` under either and the groove fits either
    way. Neither can interference — the sockets hang from box `z 105.000` down
    to `100.000`, and nothing of the box reaches that height at the front or at
    the back, so both placements measure `0.0000 mm3`. The two differ by a half
    turn about Z, which is a proper rotation, so nothing about the FIT can
    separate them at all.

    Nothing geometric separates them, so the LID GOES ON EITHER WAY ROUND. The
    only thing that can tell is the logo pattern, which is in the floor's outer
    face — the face that points up once the lid is on.

    **Y is used**, and which way up each game's mark then reads is settled by
    a PRINTED lid, not by this placement or a render of it: renders argued
    Dominion's drawing turned and a printed Dominion lid turned it back. A
    printed Innovation lid put that game's mark in turned
    (`tables.LID_LOGO_TURNED`); Compile and FCM are open until a lid of each
    is printed. `spec/ASSEMBLY.md` records it.

    The `WallThickness` in the placement is the LID's OWN floor, which stays
    1.600 at every release — the box's is `box.floor_top` and from 7.1 they are
    different numbers. Same for `lid_under`.

    Its cost is nil geometrically: the lid's sockets, placed `SOCKET_BACK` in
    from its back face, are empty when the cascade is closed — the pushers are
    in the rear storage — so nothing depends on where they land.
    """
    return Place(x_dir=(-1, 0, 0), z_dir=(0, 0, -1),
                 origin=(0.0, LID_Y, D.WallThickness + d.BoxHeight))


def lid_under(d):
    """The lid the right way up with the box standing in it — the play state.

    No turn at all, and the box's floor rests on the lid's floor, so the LID
    drops by its own wall thickness in the box's frame. It clears by
    `(lid inner - BoxWidth)/2 = 0.700` a side and `0.400` in depth over the
    box's whole footprint, rear storage included.
    """
    return Place(origin=(0.0, LID_Y, -D.WallThickness))


# --- the play state: pushers in the lid, holders on their treads ------------

def play_sockets(d):
    """Which of the lid's sockets the cascade's pushers stand in: all of them.

    From 7.1 `lid.socket_count` IS `box.pusher_slot_count`
    (`rev.lid_socket_per_pusher`), so the two parts agree and the mapping is
    the identity. At 7.0 the four Innovation M lids still cut a third, middle
    socket for a cascade that ships two pushers, and a 7.0 play assembly
    stands a pusher in that one too.

    The pushers land in the same places either way: the socket span does not
    depend on the count (`lid.socket_centres`).
    """
    from .parts import lid as lid_part
    return list(range(lid_part.socket_count(d)))


def pusher_socketed(d, socket):
    """A pusher standing in lid socket `socket`, the box's frame.

    The axes are forced the same way the stored pusher's are, off a different
    feature: the rise runs UP (+X -> +Z, leading edge down into the socket) and
    the tabs must point **-X**, because the lid cuts its two recesses into the
    channel's -X wall only. Right-handedness gives +Y -> +Y.

    * **X** — the `3.000` plate centred in the `3.300` channel, `0.150` a side.
      The standard's `0.200` of play on the recess step is the other extreme of
      the same fit, with the plate hard against the recess wall.
    * **Y** — the pusher centred on its socket, which is `LID_SOCKET_CLEARANCE`
      shorter than the pusher is deep, so `0.200` overhangs at each end.
    * **Z** — the leading edge on the lid's floor, which `lid_under` puts at
      the box's own `z = 0`: box and pushers stand on the same surface.
    """
    from .parts import lid as lid_part
    x = lid_part.socket_centres(d)[socket]
    y0, y1 = lid_part.socket_span(d)
    under = lid_under(d)
    cx, cy, _cz = under((x, (y0 + y1) / 2, 0.0))
    return Place(x_dir=(0, 0, 1), z_dir=(-1, 0, 0),
                 origin=(cx + L.PLATE / 2, cy + d.calPusherTotalDepth / 2, 0.0))


def tread_z(d, j):
    """The height of the tread riser `j` rests on, `j` counted from the BACK.

    A pusher's treads are its constant-X segments — part X is the rise, and it
    maps to the box's Z — so tread `k` is at `k * calHeightIncrement` and there
    are `RisingSliders` of them. The FRONTMOST holder takes the lowest, tread 1,
    because the pusher's first drop is `calFirstSliderDistance` and
    `slider_drops` puts the override on the leading edge, which is the front.
    """
    return (d.RisingSliders - j) * d.calHeightIncrement


def holder_play(d, j):
    """Riser `j` on its tread, still riding rib `j`.

    X and Y are the closed state's exactly — the holders ride the same slider
    ribs whether the cascade is open or shut, which is the whole idea — and
    only Z changes, from the floor to the tread.
    """
    closed = holder_closed(d, j)
    return Place(origin=(closed.origin[0], closed.origin[1],
                         tread_z(d, j) + holder_z_base(d)))


# --- the lips, in play -------------------------------------------------------
#
# From 7.2e (`rev.seated_lips`) every lip seats in the rest of the part behind
# it when the cascade is open, and the two numbers that fixes come from the
# PLACEMENTS, so they are stated here and read by the parts (`box.lip_tool`,
# `holder.rest_depth`) rather than transcribed into either. `spec/HOLDER.md`,
# "Lips that seat".

def front_holder_gap(d):
    """From the divider panel's BACK face to the front holder's FRONT face, in
    Y — the gap the Box's lip has to cross before it enters that holder's
    rest, as `CardHolderGap` (0.400) is the gap between two holders. 1.250 on
    every row: the frontmost rib is centred on its card slot, the holder on
    its rib, and the panel sits `calFrontPocketDepth + FRONT_DIVIDER` behind
    the front wall."""
    j = len(box_part.slider_ribs(d)) - 1
    pl = holder_closed(d, j)
    depth = holder_part.holder_depth(d, holder_rib(d, j)[2])
    return (pl.origin[1] - depth) - box_part.pocket_span(d)[2]


def box_lip_diagonal(d):
    """Z where the front holder's slant surface crosses the divider panel's
    back face, in play: the holder rides its tread, so `tread + half_height
    + slant_z(-(depth + gap))`. The band the box lip should occupy ends here
    — and from 7.2f it does (`box.lip_z`)."""
    j = len(box_part.slider_ribs(d)) - 1
    first = holder_rib(d, j)[2]
    pl = holder_play(d, j)
    y = -(holder_part.holder_depth(d, first) + front_holder_gap(d))
    return pl.origin[2] + holder_part.slant_z(d, first, y)


def box_lip_top(d):
    """Z of the front holder's slant surface `box.LIP_BITE` inside its front
    face, in play — where the box lip's flat top sits from 7.2f
    (`box.lip_z`). At the bite's depth and not the wall's face because the
    rest floor follows the slant and is `LIP_BITE * slope` higher there
    (0.52 on Compile): measured at the face, a flat lip's tip met the floor
    by 1.0 mm3. Here the tip clears it by `REST_CLEARANCE` exactly and the
    face by more."""
    j = len(box_part.slider_ribs(d)) - 1
    first = holder_rib(d, j)[2]
    pl = holder_play(d, j)
    y = -holder_part.holder_depth(d, first) + box_part.LIP_BITE
    return pl.origin[2] + holder_part.slant_z(d, first, y)


def box_lip_seat(d):
    """How far below the front holder's slant surface the Box lip's UNDERSIDE
    sits, in play, at the panel's back face where the lip leaves it: the
    depth a rest has to be for that lip to seat.

    Through 7.2e the lip is fixed at `box.LIP_Z` 85.500 while the diagonal
    crosses the panel `4 - 0.85 * slope` above its top — 2.000 at a slope of
    2.35, more on a flatter cascade — so the rest is deepened per row rather
    than the lip moved, whose root would otherwise stand above the panel's
    87.500 top. From 7.2f (`rev.ribs_forward`) the lip is flat and its top
    is the surface at the WALL's face (`box_lip_top`), so it is measured
    there and is the plain `LIP_HEIGHT`, 2.000, on every row.
    """
    if d.rev.ribs_forward:
        return box_lip_top(d) - box_part.lip_z(d)
    return box_lip_diagonal(d) - box_part.lip_z(d)


# --- the Topper ------------------------------------------------------------
#
# `spec/TOPPER.md` and `cad/parts/topper.py` are the authority here, and they
# make the placement EXACT rather than fitted. Two features of the part say
# what it mates to:
#
#   `TriangleMatch` extrudes the HOLDER's own `Top slant angle` face, so the
#   topper's slant IS the holder's — `topper.slant_slope` is
#   `holder.slant_slope`, to six decimals on every parameter set.
#
#   `Room for Lips` notches the topper's REAR wall for the holder's rear lips,
#   binding to `holder.lip_plan` with no clearance at all.
#
# So the topper sits with its slant flush on the holder's slant and its rear
# over the holder's lips. That is a face-to-face mate and it fixes the
# placement completely — no fitting, no measurement, no parameter.
#
# Allan's description of it: "The topper fits snugly on top of the card holder,
# with the protrusions on the side ensuring it doesn't slide down the
# diagonal." The diagonal is that slant, and the protrusions are the two tabs.


def topper(d, j, first=False):
    """The topper on riser `j`, in the cascade frame.

    A half turn about **X**, about the plane `z = topper.Z_BASE`, and one of
    `-2 * depth` in Y.

    The turn is not this module's invention. Allan: "Upside down is necessary
    for it to print properly, so the flat side with the names is face-down. It
    is used face-up when in use. This is a common pattern." The modelled
    orientation is the PRINT one — `Upside Down` in the feature tree is what
    puts it there — and the assembly turns it back.

    * **X** is not a choice. `topper.width` is `calSlotwidth * HorizontalSlots`
      — the holder less its two end blocks — and the part's X origin is the
      first slot's centre, "exactly as the Holder's is".
    * **Y**: the drawn part runs `-2*depth .. -depth` and the turn maps that
      onto the holder's own `-depth .. 0`, putting the topper's rear wall over
      the holder's rear lips, which is what `Room for Lips` is cut for.
    * **Z**: `2 * topper.Z_BASE`, i.e. the turn is about the base plane itself.
      That is what lands the slant: the topper's slant meets the holder's at
      **0.000000** on all four Innovation parameter sets, at BOTH ends of it.

    The part does not rest on the cards at all; it rests on the slant.
    Fitting a placement that a construction already determines is the mistake
    `spec/LID.md` records twice.
    """
    from .parts import topper as topper_part
    depth = holder_part.holder_depth(d, first)
    base = holder_closed(d, j).origin
    return Place(x_dir=(1, 0, 0), z_dir=(0, 0, -1),
                 origin=(base[0], base[1] - 2 * depth,
                         base[2] + 2 * topper_part.Z_BASE))


def topper_play(d, j, first=False):
    """The same, on a cascaded holder — only the tread's height differs."""
    pl = topper(d, j, first)
    lift = holder_play(d, j).origin[2] - holder_closed(d, j).origin[2]
    return Place(x_dir=pl.x_dir, z_dir=pl.z_dir,
                 origin=(pl.origin[0], pl.origin[1], pl.origin[2] + lift))


# --- the CARDS: for looking at, not for printing ----------------------------
#
# A card stack is a box the size of the cards a slot holds, placed where they
# stand, so a render can show a cascade IN USE: which slot holds which set of
# which expansion, and how much of each card shows in play. `cad.assemble
# --cards` places them and numbers them; `cad.gltf` colours a stack by its
# expansion. Nothing here reaches a part.
#
# An Innovation expansion is twelve sets of cards, numbered 0 to 11: sets 0
# and 1 of 16 cards, the rest of 10. A cascade holds as many expansions as it
# has slots for, twelve a set, counting the front pockets and every riser slot.
#
# The fill has to be READABLE, because a slot that has run out of cards has
# to say what it held: **an expansion owns a column.** Its sets run
# down that column front to back — 0 in the front pocket, 1 in the first
# riser, which are the two deep slots a column has, then 2, 3, ... to the
# back — and whatever does not fit continues down the columns no expansion
# owns, column by column, the expansions in order. So on the four-column,
# nine-row `M8.16.10-16` each expansion's 0..8 is its own column and the
# fourth column reads 9, 10, 11 of each in turn; on a single-set cascade it
# is plain column-major. An empty slot is "this column, this row". A set
# larger than its slot is cut to the slot: a 16 in a 15-card pocket shows 15.
#
# Set 0 is not an age: it is the expansion's achievements and player aids,
# wanted once at setup, so it is lettered `A` rather than numbered, and on a
# row whose deep slot is at the BACK (`isDeepSlotAtBack`) it goes there — the
# least stable riser, used least — with 1 to 8 then running from the front
# pocket back.
CARD_SETS = (16, 16) + (10,) * 10
CARD_SET_LABELS = {0: "A"}


def card_set_label(n):
    """What a stack's numeral says: the set number, or `A` for set 0."""
    return CARD_SET_LABELS.get(n, str(n))
INNOVATION_SETS = ("Innovation", "Artifacts", "Cities", "Echoes",
                   "Figures", "Unseen")
# `CardHeight` (92) is the studio's envelope and what a SLEEVED card measures;
# an unsleeved Innovation card is 89. Other games' unsleeved cards are
# taken as the sleeve's worth shorter, which is a render-only guess.
UNSLEEVED_CARD_HEIGHT = {"Innovation": 89.0}
SLEEVE_HEIGHT = 3.0


def card_height(d):
    """How tall a card is, as it stands in a slot."""
    if d.isSleeved:
        return float(d.CardHeight)
    return UNSLEEVED_CARD_HEIGHT.get(d.GameName, d.CardHeight - SLEEVE_HEIGHT)


def card_column(d, k):
    """Column `k`'s slots FRONT to BACK: `[(riser or None, capacity)]` — the
    front pocket, then the first (frontmost) riser, then back to riser 0.
    `riser` is `holders`' index (0 is the back one); None is the pocket. A
    merged row's mat slot has no pocket, so its column starts at the riser."""
    out = ([(None, d.FrontPocketCardCapacity)]
           if k < d.calFrontSlotsForCards else [])
    for j, first in reversed(holders(d)):
        out.append((j, d.FirstSlidingSlotCards if first else d.CardsPerSlidingSlot))
    return out


def card_slots(d):
    """Every slot, column by column and front to back within a column:
    `[(riser or None, column, capacity)]`."""
    return [(j, k, cap) for k in range(d.HorizontalSlots)
            for j, cap in card_column(d, k)]


def card_fill(d, sets=None):
    """`[((riser, column), expansion, set number, cards)]` — which set stands
    in which slot, by the rule above: an expansion owns a column, and the
    overflow runs down the unowned columns in order. `sets` names the
    expansions; the default is `INNOVATION_SETS` from the first, and a second
    cascade of the same box passes the rest (`cad.assemble --sets
    Echoes,Figures,Unseen`)."""
    n_exp = len(card_slots(d)) // len(CARD_SETS)
    names = list(sets or INNOVATION_SETS)
    if len(names) < n_exp:
        raise ValueError(f"{d.calModelName} holds {n_exp} expansions and only "
                         f"{len(names)} are named: {', '.join(names)}")
    if n_exp > d.HorizontalSlots:
        raise ValueError(f"{d.calModelName} has {d.HorizontalSlots} columns "
                         f"for {n_exp} expansions; the rule needs one each")
    names = names[:n_exp]
    out, spare = [], []
    for e, name in enumerate(names):
        column = card_column(d, e)
        if d.isDeepSlotAtBack:
            # Set 0 to the deep BACK slot; the rest fill from the front.
            column = column[-1:] + column[:-1]
        for n, size in enumerate(CARD_SETS):
            if n < len(column):
                j, cap = column[n]
                out.append(((j, e), name, n, min(size, cap)))
            else:
                spare.append((name, n, size))
    free = [(j, k, cap) for k in range(n_exp, d.HorizontalSlots)
            for j, cap in card_column(d, k)]
    for (j, k, cap), (name, n, size) in zip(free, spare):
        out.append(((j, k), name, n, min(size, cap)))
    return out


def card_stack(d, slot, count, state):
    """`(x0, x1, y0, y1, z0, z1)` of a stack of `count` cards in `slot`, in
    the cascade frame. In a holder the stack stands on the pocket's floor
    against its BACK wall, where a raised holder leaves it; in the front
    pocket it stands on the box floor against the front wall."""
    j, k = slot
    t = d.calCardThickness * count
    w, h = d.calCardwidth, card_height(d)
    if j is None:
        x = box_part.thumb_centres(d)[k]
        y0 = box_part.pocket_span(d)[0]
        z0 = box_part.floor_top(d)
        return (x - w / 2, x + w / 2, y0, y0 + t, z0, z0 + h)
    place = holder_closed if state in (CLOSED, CLOSED_LID) else holder_play
    ox, oy, oz = place(d, j).origin
    x = ox + k * d.calSlotwidth
    y1 = oy - holder_part.WALL
    z0 = oz + holder_part.pocket_z(d)[0] - holder_part.FLOOR_DROP
    return (x - w / 2, x + w / 2, y1 - t, y1, z0, z0 + h)


def card_label_cap(d):
    """Cap height of the set number on a stack's front face: sized to what a
    riser shows of the card behind it — the rise — and never illegible."""
    return min(10.0, max(4.0, 0.6 * d.calHeightIncrement))
