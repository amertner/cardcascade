"""The pusher lock standard, in code.

`automation/LOCK_STANDARD.md` is the document; this is it as constants. The
catalogue is also `verify.LOCK_CLASSES` and, in the CAD, `calTabCentreDistance`
— three copies of one table, which is two too many. `derive.calTabCentreDistance`
is the transcription of the Onshape expression and `CLASSES` here is the
transcription of the standard; `tests/test_lock.py` holds them to each other.

Every dimension is a constant across all 32 pushers. A design is one number:
`s`, the distance from the pusher's centreline to each tab's centre.
"""

# The catalogue IS the 7.0 lock, and cad/ builds only 7.0 — see cad/README.md,
# "One generation". A pre-7.0 pusher put its tabs at a fixed inset from the two
# depth edges (4.20 front, 4.00 back, notch always) and nothing here reproduces
# that; `pusher.build` refuses rather than stamp the wrong version on it.
GENERATION = "7.0"

# Sizes that do not move (LOCK_STANDARD.md).
PUSHER_TOTAL = 4.500      # plate + tab proudness
PLATE = 3.000             # PusherThickness
TAB_W = 3.800             # across the plate's depth
TAB_L = 5.000             # along the insertion direction
TAB_PROUD = 1.500         # one face only
NOTCH_W = 5.400
NOTCH_D = 5.200
BOX_SLOT_DEPTH = 3.200
LID_RECESS_LEN = 4.000
LID_RECESS_STEP = 1.700   # set on a test print, NOT calculated — do not tune
BOX_CUTOUT_W = 4.500
BOX_CUTOUT_D = 5.250

# Placement rule.
EDGE_MIN = 2.000
LAND_MIN = 1.200

# The catalogue: (name, s, minimum depth it may be used at).
CLASSES = (("C1", 3.10, 14.00),
           ("C2", 5.10, 18.00),
           ("C3", 8.50, 24.80),
           ("C4", 13.50, 34.80),
           ("C5", 24.00, 55.80))

# A class carries the notch only when the land between tab and notch holds up:
# s >= TAB_W/2 + NOTCH_W/2 + LAND_MIN, i.e. s >= 5.80. C1 and C2 lock by tabs
# alone and their lids lose the key rib.
NOTCH_MIN_S = TAB_W / 2 + NOTCH_W / 2 + LAND_MIN


def lock_class(depth):
    """The largest class that fits `depth`. A depth never gets an `s` of its
    own — one exception and this stops being a catalogue."""
    for name, s, min_d in reversed(CLASSES):
        if depth >= min_d:
            return name, s
    raise ValueError(f"pusher depth {depth} is below C1's {CLASSES[0][2]}")


def has_notch(s):
    return s >= NOTCH_MIN_S


def check_edge(depth, s):
    """Guard for a new box size: a tab must keep EDGE_MIN of plate outboard."""
    return s <= depth / 2 - (TAB_W / 2 + EDGE_MIN)
