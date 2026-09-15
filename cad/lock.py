"""The pusher lock standard, in code.

`automation/LOCK_STANDARD.md` is the document; this is it as constants.
`derive.calTabCentreDistance` transcribes the Onshape expression and `CLASSES`
here the standard; `tests/test_lock.py` holds them to each other. Every
dimension is constant across all 32 pushers: a design is ONE number, `s`,
from the centreline to each tab's centre.
"""

# The catalogue IS the 7.0 lock, and cad/ builds only that lock (cad/README.md,
# decision 4). A pre-7.0 pusher's tabs sat at a fixed inset from the depth
# edges and nothing here reproduces that; `pusher.build` REFUSES.
GENERATION = "7.0"
# Every RELEASE whose LOCK is GENERATION's — about the LOCK and nothing else.
# A new release must be admitted DELIBERATELY: leave it out and `pusher.build`
# refuses it rather than stamping the wrong version on 7.0 tabs
# (`tests/test_revisions.py` holds the two lists to each other). An ITERATION
# LETTER is a release like any other and is admitted too.
SAME_LOCK = ("7.0", "7.1a", "7.1b", "7.1c", "7.1d", "7.1", "7.2a", "7.2b", "7.2c",
             "7.2d", "7.2e", "7.2f", "7.2g", "8.0")


def lock_generation(version):
    return GENERATION if version in SAME_LOCK else version

# Sizes that do not move (LOCK_STANDARD.md).
PUSHER_TOTAL = 4.500      # plate + tab proudness
PLATE = 3.000             # PusherThickness
TAB_W = 3.800             # across the plate's depth
TAB_L = 5.000             # along the insertion direction
TAB_PROUD = 1.500         # one face only
NOTCH_W = 5.400
NOTCH_D = 5.200
BOX_SLOT_DEPTH = 3.200
LID_CHANNEL_W = PLATE + 0.300   # `#PusherThickness + 0.3mm` in the Lid's own
#                                 sketch; the tightest running clearance here
LID_SOCKET_CLEARANCE = 0.400   # socket span is D - this, 0.200 at each end
LID_RECESS_LEN = 4.000
LID_RECESS_STEP = 1.700   # set on a test print, NOT calculated — do not tune
BOX_CUTOUT_W = 4.500
BOX_CUTOUT_D = 5.250      # the standard's number; the box cuts 5.000 and
#                           records why (`parts/box.RIM_CUTOUT_Z`)

EDGE_MIN = 2.000
LAND_MIN = 1.200

# The catalogue: (name, s, minimum depth it may be used at).
CLASSES = (("C1", 3.10, 14.00),
           ("C2", 5.10, 18.00),
           ("C3", 8.50, 24.80),
           ("C4", 13.50, 34.80),
           ("C5", 24.00, 55.80))

# A class carries the notch only when the land between tab and notch holds up:
# s >= TAB_W/2 + NOTCH_W/2 + LAND_MIN. C1 and C2 lock by tabs alone.
NOTCH_MIN_S = TAB_W / 2 + NOTCH_W / 2 + LAND_MIN


def lock_class(depth):
    """The largest class that fits `depth`. A depth NEVER gets an `s` of its
    own: one exception and this stops being a catalogue."""
    for name, s, min_d in reversed(CLASSES):
        if depth >= min_d:
            return name, s
    raise ValueError(f"pusher depth {depth} is below C1's {CLASSES[0][2]}")


def has_notch(s):
    return s >= NOTCH_MIN_S


def check_edge(depth, s):
    return s <= depth / 2 - (TAB_W / 2 + EDGE_MIN)
