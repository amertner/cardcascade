"""Where every part sits in a whole cascade.

`derive.py` is the only place a formula lives; this is the only place a
PLACEMENT lives, derived rather than measured into a constant
(`spec/ASSEMBLY.md`). The assembly frame is the BOX's part frame — X width, 0
at the centre; Y depth, +Y toward the back; Z 0 at the bed — so the Box is the
identity. Nothing here imports build123d (`cad/lazy.py` defers the parts).
"""
from . import derive as D
from . import lock as L
from .lazy import lazy

# Imported on first use: importing a part module loads build123d.
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
    """A rigid placement: part coordinates -> assembly coordinates. The images
    of the part's X and Z axes plus an origin, which is what build123d's
    `Plane` takes; Y follows as `z_dir x x_dir`, making a placement a ROTATION
    and not a mirror. Axis images are signed unit vectors, so the matrix is
    exact integers."""
    __slots__ = ("x_dir", "y_dir", "z_dir", "origin")

    def __init__(self, x_dir=(1, 0, 0), z_dir=(0, 0, 1), origin=(0.0, 0.0, 0.0)):
        self.x_dir, self.z_dir, self.origin = x_dir, z_dir, origin
        self.y_dir = _cross(z_dir, x_dir)

    def __call__(self, p):
        x, y, z = p
        return tuple(self.origin[i] + x * self.x_dir[i] + y * self.y_dir[i]
                     + z * self.z_dir[i] for i in range(3))

    def as_3mf(self):
        """3MF's twelve numbers; the translation is in METRES, the unit the
        file declares."""
        rows = (self.x_dir, self.y_dir, self.z_dir)
        return " ".join(
            [f"{n:g}" for r in rows for n in r]
            + [f"{n / 1000:.8f}" for n in self.origin])

    def location(self):
        from build123d import Location, Plane, Vector
        return Location(Plane(origin=Vector(*self.origin),
                              x_dir=Vector(*self.x_dir),
                              z_dir=Vector(*self.z_dir)))

    def __repr__(self):
        return (f"Place(x={self.x_dir}, z={self.z_dir}, "
                f"origin=({', '.join(f'{n:.3f}' for n in self.origin)}))")


IDENTITY = Place()


def box(d):
    return IDENTITY                     # the Box IS the frame


# On edge and upright, all three axis images forced: +X (rise) -> -Z, the tabs
# engaging the rim cutouts at the TOP; +Z (the tab face) -> -Y, those cutouts
# being cut through the inner back wall; +Y -> +X by right-handedness.

PLATE_SLOP = (L.BOX_SLOT_DEPTH - L.PLATE) / 2      # 0.100 a side, nominal


def pusher_stored(d, k):
    """The `k`th stored pusher, left to right. Z: the pusher HANGS by its
    tabs, top flush at the rim (`box.pusher_rest` is a CATCH below, not a
    shelf). X: part `y = -D/2` lands on the slot centre. Y: the plate centred
    in the slot band."""
    depth = d.calPusherTotalDepth
    centre = box_part.pusher_slots(d)[k]
    _y0, y1 = box_part.slot_band(d)
    return Place(x_dir=(0, 0, -1), z_dir=(0, -1, 0),
                 origin=(centre + depth / 2, y1 - PLATE_SLOP, d.BoxHeight))


# The holder's own axes already run the box's way: X across, Y with the REAR
# face at 0 and the body toward the front, Z up. So it is a translation.

def holder_rib(d, j):
    """(y, depth, first) for riser `j`, back to front. `box.slider_ribs` puts
    the odd `calFirstSliderDistance` rib LAST, the frontmost — the rib the
    deeper `FirstHolder` takes, and only when the row has an override."""
    ribs = box_part.slider_ribs(d)
    deep = 0 if d.isDeepSlotAtBack else len(ribs) - 1   # `Deep slot = back`
    first = bool(d.isFirstSlidingSlotOverride) and j == deep
    y0, y1 = ribs[j]
    return (y0 + y1) / 2, holder_part.holder_depth(d, first), first


def holder_x(d):
    """The X translation: the holder's origin is its FIRST compartment's
    centre, so centring it shifts half the compartment span."""
    return -(d.HorizontalSlots - 1) * d.calSlotwidth / 2


def holder_z_base(d):
    return holder_part.half_height(d)


def holder_closed(d, j):
    """Riser `j` on the floor, its side slots over rib `j`, resting on the two
    `side_floor` strips. The Z datum is the BOX's floor — `box.floor_top`,
    NOT `WallThickness`: they part company at 7.1, and a holder placed on the
    wall's thickness would sit inside the floor it rests on."""
    y, depth, _first = holder_rib(d, j)
    return Place(origin=(holder_x(d), y + depth / 2,
                         box_part.floor_top(d) + holder_z_base(d)))


def holders(d):
    """[(j, first)] — one per riser, back to front; `first` is the DEEP
    holder's flag and `rear_of` says which is the REAR one."""
    n = len(box_part.slider_ribs(d))
    return [(j, holder_rib(d, j)[2]) for j in range(n)]


def rear_of(d, j):
    """Is riser `j` the RearHolder — the rearmost, built without rear lips
    (`rev.rear_holder`)? Riser 0 is the back one."""
    return bool(d.rev.rear_holder) and j == 0


def holder_kinds(d):
    """The distinct holders a cascade is built from, each with the risers it
    stands on: `[((first, rear), [j, ...])]`, back to front."""
    out = {}
    for j, first in holders(d):
        out.setdefault((first, rear_of(d, j)), []).append(j)
    return sorted(out.items(), key=lambda kv: kv[1][0])


def pushers(d):
    """How many pushers a cascade STORES, and which slot each takes.
    `box.storage_slot_count`, NOT `pusher_slot_count`: the two differ on a
    variant back (7.2g), and this indexes `box.pusher_slots`."""
    return list(range(box_part.storage_slot_count(d)))


# Its own frame's origin is already the SLOT's corner, so this is just where
# that slot is in the box. Its Y runs the opposite way to the box's, so the
# placement is a 180 degree turn about Z; X alone flipped would be a MIRROR.

def token_slot_x(d):
    """The slot's +X end, which the turn makes its origin. Anchored on the
    last front DIVIDER (the sketch's own datum); the right inner wall less
    `FrontPocketSidePaddingWidth` agrees exactly."""
    return box_part.front_dividers(d)[-1] + d.calTokenHolderSlotWidth


def token_holder(d):
    """The FULL holder, dropped into the front pocket's last compartment. A
    merged cascade's HALF holder is an ALTERNATIVE at the same placement, so
    only the mesh changes. It stands on `box.floor_top`, not
    `WallThickness`."""
    front, _panel_front, _panel_back = box_part.pocket_span(d)
    return Place(x_dir=(-1, 0, 0), z_dir=(0, 0, 1),
                 origin=(token_slot_x(d), front, box_part.floor_top(d)))


def label_width(d):
    """The label the front holder takes: `labelmaker`'s wide front, or the
    62 where the box is too narrow for it (`box.front_label_len`)."""
    return box_part.front_label_len(d) - box_part.LABEL_HOLDER_EXTRA


def label_plate(d):
    """A slide-in label as it sits in the front holder, for a render.
    `labelmaker.make_label` builds it flat; a quarter turn about X stands it
    up — height to +Z, thickness to -Y — centred on the box's x, its bottom
    edge on the slot's floor and its back face at the bottom of the groove."""
    y_back = -box_part.box_depth(d) / 2 - box_part.LABEL_PROUD + box_part.LABEL_GROOVE
    return Place(x_dir=(1, 0, 0), z_dir=(0, -1, 0),
                 origin=(-label_width(d) / 2, y_back,
                         box_part.label_band(d)[0] + box_part.LABEL_GROOVE_IN))


LID_Y = 2.250              # the box sits this far back of the lid


def lid_closed(d):
    """The lid inverted over the box: a half turn about **Y**.

    A CHOICE, not a derivation — nothing geometric separates it from the half
    turn about Z, so the lid goes on either way round and only the logo can
    tell. Which way up a mark reads is settled by a PRINTED lid, never by a
    render (`spec/ASSEMBLY.md`). The `WallThickness` here is the LID's OWN
    floor, 1.600 at every release; the box's is `box.floor_top`.
    """
    return Place(x_dir=(-1, 0, 0), z_dir=(0, 0, -1),
                 origin=(0.0, LID_Y, D.WallThickness + d.BoxHeight))


def lid_under(d):
    """The lid the right way up with the box standing in it — the play state.
    No turn, and the box's floor rests on the lid's floor, so the LID drops by
    its own wall thickness in the box's frame."""
    return Place(origin=(0.0, LID_Y, -D.WallThickness))


def play_sockets(d):
    """Which of the lid's sockets the cascade's pushers stand in: all of them.
    From 7.1 `lid.socket_count` IS `box.pusher_slot_count`, so the mapping is
    the identity; at 7.0 some lids cut an extra middle socket and a 7.0 play
    assembly stands a pusher in it too."""
    from .parts import lid as lid_part
    return list(range(lid_part.socket_count(d)))


def pusher_socketed(d, socket):
    """A pusher standing in lid socket `socket`, the box's frame. Axes forced:
    the rise runs UP (+X -> +Z, leading edge into the socket) and the tabs
    point **-X**, the lid cutting its recesses into the channel's -X wall
    only. X: the plate centred in the channel. Y: centred on its socket. Z:
    the leading edge on the lid's floor, the box's own z = 0."""
    from .parts import lid as lid_part
    x = lid_part.socket_centres(d)[socket]
    y0, y1 = lid_part.socket_span(d)
    under = lid_under(d)
    cx, cy, _cz = under((x, (y0 + y1) / 2, 0.0))
    return Place(x_dir=(0, 0, 1), z_dir=(-1, 0, 0),
                 origin=(cx + L.PLATE / 2, cy + d.calPusherTotalDepth / 2, 0.0))


def tread_z(d, j):
    """The height of the tread riser `j` rests on, `j` counted from the BACK.
    The FRONTMOST holder takes the lowest, tread 1, because `slider_drops`
    puts the pusher's override on the leading edge."""
    return (d.RisingSliders - j) * d.calHeightIncrement


def holder_play(d, j):
    """Riser `j` on its tread, still riding rib `j`. X and Y are the closed
    state's exactly; only Z changes, from the floor to the tread."""
    closed = holder_closed(d, j)
    return Place(origin=(closed.origin[0], closed.origin[1],
                         tread_z(d, j) + holder_z_base(d)))


# From 7.2e (`rev.seated_lips`) every lip seats in the rest behind it when the
# cascade is open. The numbers that fixes come from the PLACEMENTS, so they
# are stated here and READ by the parts. `spec/HOLDER.md`, "Lips that seat".

def front_holder_gap(d):
    """From the divider panel's BACK face to the front holder's FRONT face, in
    Y — the gap the Box's lip crosses before entering that holder's rest."""
    j = len(box_part.slider_ribs(d)) - 1
    pl = holder_closed(d, j)
    depth = holder_part.holder_depth(d, holder_rib(d, j)[2])
    return (pl.origin[1] - depth) - box_part.pocket_span(d)[2]


def box_lip_diagonal(d):
    """Z where the front holder's slant crosses the divider panel's back
    face, in play. The band the box lip occupies ends here."""
    j = len(box_part.slider_ribs(d)) - 1
    first = holder_rib(d, j)[2]
    pl = holder_play(d, j)
    y = -(holder_part.holder_depth(d, first) + front_holder_gap(d))
    return pl.origin[2] + holder_part.slant_z(d, first, y)


def box_lip_top(d):
    """Z of the front holder's slant `box.LIP_BITE` inside its front face, in
    play — where the box lip's flat top sits from 7.2f (`box.lip_z`). At the
    BITE's depth and not the wall's face, because the rest floor follows the
    slant and is higher there."""
    j = len(box_part.slider_ribs(d)) - 1
    first = holder_rib(d, j)[2]
    pl = holder_play(d, j)
    y = -holder_part.holder_depth(d, first) + box_part.LIP_BITE
    return pl.origin[2] + holder_part.slant_z(d, first, y)


def box_lip_seat(d):
    """How far below the front holder's slant the Box lip's UNDERSIDE sits, in
    play, at the panel's back face: the depth a rest has to be for that lip to
    seat. Through 7.2e the lip is fixed and the rest is deepened per row; from
    7.2f (`rev.ribs_forward`) the lip is flat and this is `LIP_HEIGHT` on
    every row."""
    if d.rev.ribs_forward:
        return box_lip_top(d) - box_part.lip_z(d)
    return box_lip_diagonal(d) - box_part.lip_z(d)


# EXACT, not fitted: the topper's slant IS the holder's and `Room for Lips`
# notches its rear wall for the holder's rear lips with no clearance, which
# is a face-to-face mate. `spec/TOPPER.md`, "Assembly position".

def topper(d, j, first=False):
    """The topper on riser `j`, in the cascade frame: a half turn about **X**
    about the plane `z = topper.Z_BASE`, plus `-2 * depth` in Y. The modelled
    orientation is the PRINT one, slant face down; the assembly turns it back,
    which lands the slant at 0.000000 and the rear wall over the lips."""
    from .parts import topper as topper_part
    depth = holder_part.holder_depth(d, first)
    base = holder_closed(d, j).origin
    return Place(x_dir=(1, 0, 0), z_dir=(0, 0, -1),
                 origin=(base[0], base[1] - 2 * depth,
                         base[2] + 2 * topper_part.Z_BASE))


def topper_play(d, j, first=False):
    pl = topper(d, j, first)   # the same, one tread's height higher
    lift = holder_play(d, j).origin[2] - holder_closed(d, j).origin[2]
    return Place(x_dir=pl.x_dir, z_dir=pl.z_dir,
                 origin=(pl.origin[0], pl.origin[1], pl.origin[2] + lift))


# A card stack is a box the size of the cards a slot holds, placed where they
# stand, so a render can show a cascade IN USE; nothing here reaches a part.
# The fill has to be READABLE, so **an expansion owns a column**, the overflow
# running down the columns no expansion owns. Set 0 is the achievements and
# player aids, lettered `A` and in the deep BACK slot where a row has one.
# `spec/RENDER.md`, "Cards in the slots".
CARD_SETS = (16, 16) + (10,) * 10
CARD_SET_LABELS = {0: "A"}


def card_set_label(n):
    return CARD_SET_LABELS.get(n, str(n))
INNOVATION_SETS = ("Innovation", "Artifacts", "Cities", "Echoes",
                   "Figures", "Unseen")
# `CardHeight` is the studio's envelope and what a SLEEVED card measures.
# Other games' unsleeved cards are taken as the sleeve's worth shorter, which
# is a render-only guess.
UNSLEEVED_CARD_HEIGHT = {"Innovation": 89.0}
SLEEVE_HEIGHT = 3.0


def card_height(d):
    if d.isSleeved:
        return float(d.CardHeight)
    return UNSLEEVED_CARD_HEIGHT.get(d.GameName, d.CardHeight - SLEEVE_HEIGHT)


def card_column(d, k):
    """Column `k`'s slots FRONT to BACK: `[(riser or None, capacity)]`, None
    being the pocket. A merged row's mat slot has no pocket."""
    out = ([(None, d.FrontPocketCardCapacity)]
           if k < d.calFrontSlotsForCards else [])
    for j, first in reversed(holders(d)):
        out.append((j, d.FirstSlidingSlotCards if first else d.CardsPerSlidingSlot))
    return out


def card_slots(d):
    """`[(riser or None, column, capacity)]`, column by column, front first."""
    return [(j, k, cap) for k in range(d.HorizontalSlots)
            for j, cap in card_column(d, k)]


def card_fill(d, sets=None):
    """`[((riser, column), expansion, set number, cards)]` — which set stands
    in which slot, by the rule above. `sets` names the expansions; a second
    cascade of the same box passes the rest."""
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
    """`(x0, x1, y0, y1, z0, z1)` of a stack of `count` cards in `slot`, in the
    cascade frame: in a holder, on the pocket's floor against its BACK wall;
    in the front pocket, on the box floor against the front wall."""
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
    """Cap height of the set number on a stack's front face: sized to the
    rise, and never illegible."""
    return min(10.0, max(4.0, 0.6 * d.calHeightIncrement))
