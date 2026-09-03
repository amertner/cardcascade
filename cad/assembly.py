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


# --- the TokenHolder -------------------------------------------------------
#
# Its own frame's origin is already the SLOT's corner, not the part's — the
# part is the slot inset CLEARANCE on all four sides — so this placement is
# just where that slot is in the box. Its Y runs the opposite way to the box's
# (0 at the slot's FRONT edge, negative going BACK), so the placement is a 180
# degree turn about Z: with X alone flipped it would be a MIRROR, which no
# physical part is. That also settles what its "left edge of the slot" means —
# left as seen from behind, which is the box's +X end.

def token_slot_x(p, d):
    """The slot's +X end, which the turn makes its origin.

    Two expressions land on it and they agree exactly, which is what says it is
    the right datum: the last front divider's right edge plus
    `calTokenHolderSlotWidth`, and the right inner wall less
    `FrontPocketSidePaddingWidth`. Both give 94.250 on Dominion `S4.16.10`.
    Anchored on the DIVIDER, because that is the sketch's own datum — the
    lesson `spec/LID.md` records twice about a rule that fits and is still hung
    off the wrong thing.
    """
    return box_part.front_dividers(p, d)[-1] + d.calTokenHolderSlotWidth


def token_holder(p, d):
    """The FULL holder, dropped into the front pocket's last compartment.

    A merged cascade also ships a HALF one, and the two are ALTERNATIVES rather
    than both fitting: `spec/TOKENHOLDER.md` says a half holder is not half of
    a full one and that they are not meant to stack in depth, and they are the
    same width, so the slot takes one or the other. The FULL is placed because
    every token-holder row gets one; `cad.assemble --half` swaps in the HALF on
    a merged row. The PLACEMENT is the same either way — the origin is the
    slot's corner, and both parts are inset `CLEARANCE` into it — so only the
    mesh changes.
    """
    front, _panel_front, _panel_back = box_part.pocket_span(p, d)
    return Place(x_dir=(-1, 0, 0), z_dir=(0, 0, 1),
                 origin=(token_slot_x(p, d), front, D.WallThickness))


# --- the Lid ---------------------------------------------------------------
#
# The lid's frame relates to the box's by a plain Y shift and, when it is on,
# a half turn. `parts/lid.py` states both halves already: `lid_y = box_y -
# 2.250` in its docstring, and "a box height h arrives at WALL + BoxHeight - h
# in the lid's frame" in `closing_grooves`.

LID_Y = 2.250              # the box sits this far back of the lid
LID_CLOSED_Z = D.WallThickness  # + BoxHeight; see lid_closed


def lid_closed(p, d):
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
    face — the face that points up once the lid is on — and **the four games'
    marks do not agree with each other**: Dominion's reads upright under a turn
    about X and Compile's, FCM's and Innovation's under a turn about Y, so one
    game is upside down whichever is chosen. Nothing in `cad/` rotates the
    artwork; the four `logos/<Game>/lid_logo.dxf` disagree, and the cached
    Onshape lids carry the same inlays to 0.001, so this is on the shipped
    product too. `spec/ASSEMBLY.md` records it; Allan decides which DXF turns.

    **Y is chosen because three of the four read correctly under it.** That is a
    majority, not a proof, and it is the honest description of the state of the
    evidence.

    Its cost is nil geometrically: the lid's sockets, placed `SOCKET_BACK` in
    from its back face, are empty when the cascade is closed — the pushers are
    in the rear storage — so nothing depends on where they land.
    """
    return Place(x_dir=(-1, 0, 0), z_dir=(0, 0, -1),
                 origin=(0.0, LID_Y, D.WallThickness + d.BoxHeight))


def lid_under(p, d):
    """The lid the right way up with the box standing in it — the play state.

    No turn at all, and the box's floor rests on the lid's floor, so the LID
    drops by its own wall thickness in the box's frame. It clears by
    `(lid inner - BoxWidth)/2 = 0.700` a side and `0.400` in depth over the
    box's whole footprint, rear storage included.
    """
    return Place(origin=(0.0, LID_Y, -D.WallThickness))


# --- the play state: pushers in the lid, holders on their treads ------------

def play_sockets(p, d):
    """Which of the lid's sockets the cascade's pushers stand in.

    A lid gets `lid.socket_count` sockets — the plain size rule — while the
    cascade ships `box.pusher_slot_count`. They agree everywhere except an
    Innovation M, whose lid has three and whose cascade has two, and there the
    unused one is the MIDDLE (Allan): `spec/LID.md` records that it is to be
    dropped from the Lid eventually. So the pushers take the OUTER pair.
    """
    from .parts import lid as lid_part
    n_sock = lid_part.socket_count(p)
    n_push = box_part.pusher_slot_count(p)
    if n_push >= n_sock:
        return list(range(n_sock))
    return [0, n_sock - 1] if n_push == 2 else list(range(n_push))


def pusher_socketed(p, d, socket):
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
    x = lid_part.socket_centres(p, d)[socket]
    y0, y1 = lid_part.socket_span(p, d)
    under = lid_under(p, d)
    cx, cy, _cz = under((x, (y0 + y1) / 2, 0.0))
    return Place(x_dir=(0, 0, 1), z_dir=(-1, 0, 0),
                 origin=(cx + L.PLATE / 2, cy + d.calPusherTotalDepth / 2, 0.0))


def tread_z(p, d, j):
    """The height of the tread riser `j` rests on, `j` counted from the BACK.

    A pusher's treads are its constant-X segments — part X is the rise, and it
    maps to the box's Z — so tread `k` is at `k * calHeightIncrement` and there
    are `RisingSliders` of them. The FRONTMOST holder takes the lowest, tread 1,
    because the pusher's first drop is `calFirstSliderDistance` and
    `slider_drops` puts the override on the leading edge, which is the front.
    """
    return (p.RisingSliders - j) * d.calHeightIncrement


def holder_play(p, d, j):
    """Riser `j` on its tread, still riding rib `j`.

    X and Y are the closed state's exactly — the holders ride the same slider
    ribs whether the cascade is open or shut, which is the whole idea — and
    only Z changes, from the floor to the tread.
    """
    closed = holder_closed(p, d, j)
    return Place(origin=(closed.origin[0], closed.origin[1],
                         tread_z(p, d, j) + holder_z_base(d)))


# --- the Topper ------------------------------------------------------------
#
# Allan: "The topper fits snugly on top of the card holder, with the
# protrusions on the side ensuring it doesn't slide down the diagonal. There is
# no mate per se." So the cached component's position is NOT an assembly
# position and nothing may be read off it directly — which is what an earlier
# draft of `spec/ASSEMBLY.md` did, and it was wrong twice over.
#
# What the part IS, from sectioning `Topper Blank S15-Un`: a long bar with two
# thin fins at its extreme ends, ~45 mm long, and a shorter protrusion at each
# compartment DIVIDER. The label is an inlay in the bar's `z_min` face, the same
# `-0.010 .. 0.800` signature the Lid's logo has. That face must be visible, so
# it is UP in use and the fins hang DOWN — which is what makes them protrusions
# that stop the bar sliding down the diagonal.
#
# X is not a choice: two independent features fix it, and both are exact.
# The bar's ends inset `holder.END_EXTRA` 4.900 from the holder's, so it spans
# exactly between the end blocks; and its protrusions sit at 33.500 and 100.500
# on an Innovation `S5.15.15`, which are `(k + 0.5) * calSlotwidth` — the
# holder's own dividers. So the Topper is drawn in the HOLDER's frame with no X
# offset at all.


def topper(p, d, j, drawn_face_z, first=False):
    """The topper on riser `j`, in the cascade frame.

    A half turn about **X** — label up, fins down — and then:

    * **X** unchanged, per above.
    * **Y** the topper's depth equals the holder's exactly (8.000 against
      8.000, and 6.000 against 6.000 on the 10-card pair), so laying it over
      the holder is the only alignment there is. The drawn part sits at
      `-2 * depth .. -depth`, so the turn about X and an origin of
      `-2 * depth` bring it onto the holder's own `-depth .. 0`.
    * **Z** the label face lands on `holder.card_top` — the topper caps the
      cards it names.

    `drawn_face_z` is the cached mesh's own minimum Z, the label face, and it is
    a PARAMETER rather than a constant because there is no `cad/` Topper to
    derive it from: the part is only available as the cached component, so its
    drawn frame is a fact about a file. `cad/assemble.py` reads it off the mesh
    it is about to place. It measures 48.450 against a `card_top` of 48.550.
    """
    depth = holder_part.holder_depth(p, d, first)
    base = holder_closed(p, d, j).origin
    return Place(x_dir=(1, 0, 0), z_dir=(0, 0, -1),
                 origin=(base[0], base[1] - 2 * depth,
                         base[2] + holder_part.card_top(d) + drawn_face_z))


def topper_play(p, d, j, drawn_face_z, first=False):
    """The same, on a cascaded holder — only the tread's height differs."""
    pl = topper(p, d, j, drawn_face_z, first)
    lift = holder_play(p, d, j).origin[2] - holder_closed(p, d, j).origin[2]
    return Place(x_dir=pl.x_dir, z_dir=pl.z_dir,
                 origin=(pl.origin[0], pl.origin[1], pl.origin[2] + lift))
