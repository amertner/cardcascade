"""Primary -> Derived. Every formula in the model, exactly once.

A faithful transcription of the Onshape variable studio, **in studio order**,
one statement per variable, keeping Onshape's names. Reviewing this against the
studio is meant to be mechanical: read down both, line by line.

Lengths are mm and angles degrees throughout, so Onshape's unit suffixes drop
out. Nothing here imports build123d — the derived layer is pure arithmetic and
is tested on its own (`tests/test_derive.py`).

No component module may recompute any of this. Read it from `Derived`.
"""
from . import tables as T

# --- constants (studio variables with literal values) ----------------------
PocketHeight = 75.0                 # default height of each card pocket
FrontPocketHeight = 75.0            # (back) height of the fixed front pocket
BoxRearPusherSupportDepth = 1.0     # slot in rear of box supporting the pusher
HolderSideSlotWidth = 5.0           # side slot on the card holder
LeanAngle = 0.0                     # pusher/card lean — NOT CURRENTLY USED
WallThickness = 1.6
Gripperwidth = 0.5                  # side closing grip holding box and lid
CardHolderGap = 0.4                 # gap between holders, for the slider lid
PusherFootDepth = 5.0
PusherThickness = 3.0
PusherFootThickness = 1.6
# How far the Lid's pusher socket sits in from its inner wall — and, less
# 1.000, where the logo's cap top goes. Allan's expression: the box's two walls
# and the plate between them, plus 1.2 of clearance.
FootDistanceFromWall = 2 * WallThickness + PusherThickness + 1.2      # 7.4
TabLeftMargin = 4.0                 # pre-7.0 tab placement (see lock.py)
TabWidth = 4.0
ClosingBumpDepth = 1.0
FrontPocketsSubdivided = 2
FrontPocketSidePaddingWidth = 5.8
NotchDepth = 2.5                    # topper notch grip
ThumbCutoutRadius = 12.0
LipDistanceFromFingerHole = 3.0
LipLength = 10.0
LipDepth = 2.1                      # "Tried 2.3 mm, it's a bit much"
LipChamfer = 1.2
LipHeight = 2.0                     # "Up from 1mm"


class Derived:
    """Immutable attribute view over the computed variable set.

    It carries EVERY variable the studio computes, not only the ones a part
    module reads: about two dozen are read by nothing in `cad/` (the label
    sizes, the Onshape-only helpers, the token holder's slot arithmetic). That
    is deliberate — `derive()` is a transcription of the studio and is tested
    as one (`tests/test_derive.py`), and a variable that is unread today is
    still the record of what Onshape computes, and the one a future part or a
    test will want. Do not prune them for tidiness.
    """
    __slots__ = ("_v",)

    def __init__(self, v):
        object.__setattr__(self, "_v", dict(v))

    def __getattr__(self, k):
        try:
            return self._v[k]
        except KeyError:
            raise AttributeError(f"no derived variable {k!r}") from None

    def __setattr__(self, k, v):
        raise AttributeError("Derived is immutable — formulas belong in derive()")

    def __repr__(self):
        return "Derived(" + ", ".join(f"{k}={v!r}" for k, v in self._v.items()) + ")"

    def items(self):
        return self._v.items()


def derive(p):
    """The studio, in order. `p` is a params.Primary."""
    v = {}
    g = p.GameName

    v["BoxHeight"] = 115.0 if g == "Colours" else 105.0
    v["LidHeight"] = 55.0 if g == "Colours" else 40.0
    # 92.0 for every game. The studio branches to 58.0 for CraftGutermann,
    # which is deprecated and removed here — see cad/tables.py.
    v["CardHeight"] = 92.0
    v["gameUnsleevedCardWidth"] = T.UNSLEEVED_CARD_WIDTH[g]
    v["game10UnsleevedCardThickness"] = T.TEN_UNSLEEVED_THICKNESS[g]
    v["game10SleevedCardThickness"] = T.TEN_SLEEVED_THICKNESS.get(g)

    v["calCardThickness"] = (v["game10UnsleevedCardThickness"] if p.isSleeved == 0
                             else v["game10SleevedCardThickness"]) / 10
    v["calCardwidth"] = v["gameUnsleevedCardWidth"] + {0: 0.0, 1: 2.0}[p.isSleeved]
    v["calSlotwidth"] = 3.0 + v["calCardwidth"]
    # `#BoxWidth` is a SKETCH variable, not a studio one, and it is the single
    # exception in this file. It is here because `calTokenHolderSlotWidth`
    # below is a studio variable written in terms of it, and the alternative —
    # a second copy of the expression — is the one thing this module exists to
    # prevent. `cad/parts/box.box_width` reads it back, so Box, Lid and
    # TokenHolder still share exactly one transcription. See spec/DERIVED.md.
    v["BoxWidth"] = 2 * WallThickness + 11.1 + v["calSlotwidth"] * p.HorizontalSlots
    # `#calPusherSlots` is the second sketch variable: how many pushers the
    # rear storage takes. 2 for every Innovation box (`isOnlyTwoPusherSlots`,
    # below, is the studio's own answer) and for an S box, else 3. Here for
    # the same reason `#BoxWidth` is — the Box, the Lid and the assembly all
    # read it, and it was being re-derived in `parts/box.py` with its own
    # `GameName == "Innovation"`, a second copy of the rule this file owns.
    v["calPusherSlots"] = 2 if (g == "Innovation" or p.HorizontalSlots <= 3) else 3
    v["calSlotDepth"] = v["calCardThickness"] * p.CardsPerSlidingSlot
    v["calFirstSlotDepth"] = (v["calSlotDepth"] if p.isFirstSlidingSlotOverride == 0
                              else v["calCardThickness"] * p.FirstSlidingSlotCards)

    v["calDesiredHeightIncrement"] = T.DESIRED_HEIGHT_INCREMENT[g]
    # The rise per riser. verify.audit_rises measures this off a printed pusher
    # and finds 10.875 at 8 risers; (105 - 18) / 8 is exactly that.
    v["calHeightIncrement"] = min(v["calDesiredHeightIncrement"],
                                  (v["BoxHeight"] - 18.0) / p.RisingSliders)

    v["calSliderDistance"] = v["calSlotDepth"] + 2.0 + CardHolderGap
    v["calFirstSliderDistance"] = v["calFirstSlotDepth"] + 2.0 + CardHolderGap
    v["calHolderDepth"] = v["calSliderDistance"] - 0.5
    v["calLogoSidelength"] = 3 * v["calHolderDepth"] / 4 - 0.2

    v["calFootTotalWidth"] = 2 * PusherThickness + 2 * PusherFootThickness
    v["calTabDepth"] = WallThickness - 0.1

    v["calSliderSpaceLeftRight"] = FrontPocketSidePaddingWidth + 0.1
    v["calLidTextOffset"] = v["calSliderSpaceLeftRight"]
    # NB the studio tests GameName == "None", which no game is, so this is
    # always calSliderSpaceLeftRight. Transcribed as written — see DERIVED.md.
    v["calFrontDividerLeftSpacing"] = 0.0 if g == "None" else v["calSliderSpaceLeftRight"]
    v["calFirstLeftFrontDividerDist"] = v["calSlotwidth"] + v["calFrontDividerLeftSpacing"]

    v["calPusherTotalDepth"] = ((p.RisingSliders - 1) * v["calSliderDistance"]
                                + v["calFirstSliderDistance"])
    # --- pre-7.0 tab placement; superseded by calTabCentreDistance ----------
    # Transcribed because the studio still has them; NOTHING reads them, as
    # cad/ builds 7.0 only. calTabDistance is the pre-7.0 tab-centre
    # separation and matches the 14 still-6.6 pushers on disk exactly.
    v["calNumTabs"] = 2 if v["calPusherTotalDepth"] > 18.0 else 1
    v["calTabDistance"] = (v["calPusherTotalDepth"]
                           - v["calNumTabs"] * (TabWidth + TabLeftMargin) + TabWidth)
    v["calTabToTapDistance"] = max(0.0, (v["calTabDistance"] - TabWidth) / 2)
    v["calPusherMarginToRight"] = (v["calPusherTotalDepth"] - TabLeftMargin
                                   - (v["calNumTabs"] - 1)
                                   * (v["calTabDistance"] + TabWidth))
    # -----------------------------------------------------------------------
    v["calPusherTotalHeight"] = v["calHeightIncrement"] * p.RisingSliders
    v["calFrontPocketDepth"] = v["calCardThickness"] * p.FrontPocketCardCapacity
    v["calAngleDelta"] = 0.0    # sin(LeanAngle) * BoxHeight; LeanAngle is 0

    v["calLidDepth"] = ((8.5 + (p.RisingSliders - 1) * v["calSliderDistance"]
                         + v["calFirstSliderDistance"])
                        + v["calFrontPocketDepth"] + WallThickness
                        + PusherThickness + 1.0)
    d = v["calLidDepth"]
    v["calSideLabelWidth"] = 62 if d > 77 else (45 if d > 59 else (32 if d > 44 else 20))

    v["calFirstSlotRisingCardCapacity"] = p.HorizontalSlots * (
        p.CardsPerSlidingSlot if p.isFirstSlidingSlotOverride == 0
        else p.FirstSlidingSlotCards)
    v["calRisingTypeCapacity"] = (p.RisingSliders - 1) * p.HorizontalSlots
    v["calFrontSlotsForCards"] = (p.HorizontalSlots if p.MatPocket == 0
                                  else p.HorizontalSlots - 2)
    v["calFrontSlotsExceptTokenHolderSlot"] = (p.HorizontalSlots - 1 if p.MatPocket == 0
                                               else v["calFrontSlotsForCards"])
    # What is left of the front pocket once the card compartments have taken
    # their slots: the width the token holder has to fit into. Transcribed as
    # Allan wrote it (see spec/TOKENHOLDER.md); it reduces to
    # `calSlotwidth - 0.600` on a plain box and `2 * calSlotwidth - 0.600` on a
    # Mat one, because `calFrontSlotsExceptTokenHolderSlot` drops by one more
    # when the mat merges two slots — which is the whole of what "merged" means
    # to this part. HorizontalSlots cancels out, so a token holder's size
    # depends on the card width and the Mat flag and on nothing else.
    v["calTokenHolderSlotWidth"] = (v["BoxWidth"]
                                    - v["calFrontSlotsExceptTokenHolderSlot"]
                                    * v["calSlotwidth"]
                                    - 2 * WallThickness
                                    - v["calFrontDividerLeftSpacing"]
                                    - FrontPocketSidePaddingWidth)
    v["calFrontTotalCapacity"] = v["calFrontSlotsForCards"] * p.FrontPocketCardCapacity
    v["calTotalCards"] = (v["calRisingTypeCapacity"] * p.CardsPerSlidingSlot
                          + v["calFirstSlotRisingCardCapacity"]
                          + v["calFrontTotalCapacity"])
    v["calAllTypeCapacity"] = v["calRisingTypeCapacity"] + p.HorizontalSlots

    # The studio's other branch was "Craft Cascade" for CraftGutermann; see
    # cad/tables.py for why that game is gone.
    v["ProductName"] = "Card Cascade"
    v["gameShortName"] = T.GAME_SHORT_NAME[g]
    v["isLabelHoldersOnBox"] = 0 if g == "Colours" else (1 if p.HorizontalSlots > 1 else 0)
    v["isOnlyTwoPusherSlots"] = 1 if g == "Innovation" else 0

    v["NotchLength"] = 3.5 if v["calSlotDepth"] > 5.5 else 2.5

    v["calMaxPocketHeight"] = min(v["CardHeight"] - 3.5,
                                  v["BoxHeight"] - WallThickness * 2
                                  - PusherFootThickness - 4.0 - 4.0)
    v["calPocketHeight"] = v["calMaxPocketHeight"]
    v["calPocketDrop"] = min(8.0, max(v["calSlotDepth"] + 2.0,
                                      v["calDesiredHeightIncrement"]
                                      - (v["CardHeight"] - v["calPocketHeight"])))

    v["calSizeLetter"] = T.SIZE_LETTER.get(p.HorizontalSlots, "?")
    slv = ".Un" if p.isSleeved == 0 else ".Sl"
    mat = "-M" if p.MatPocket == 1 else ""
    v["calHolderModel"] = (f"{v['calSizeLetter']}.{p.CardsPerSlidingSlot}{slv}{mat}")
    v["calTokenHolderModel"] = (f"{v['calSizeLetter']}{p.FrontPocketCardCapacity}"
                                f"{mat}{slv}")
    v["calModelName"] = (
        f"{v['calSizeLetter']}{p.RisingSliders}.{p.FrontPocketCardCapacity}"
        f".{p.CardsPerSlidingSlot}"
        f"{'' if p.isFirstSlidingSlotOverride == 0 else '-' + str(p.FirstSlidingSlotCards)}"
        f".{v['calSideLabelWidth']}{mat}{slv}")
    v["calCapacityLabel"] = f"{v['calTotalCards']} Cards/{'S' if p.isSleeved == 1 else 'U'}"
    v["calVersion"] = f"CC {p.Version}"

    # From v7: tabs sit this far from the pusher's centreline. This is the
    # C1..C5 lock catalogue of LOCK_STANDARD.md, expressed as a ladder on depth.
    ptd = v["calPusherTotalDepth"]
    v["calTabCentreDistance"] = (24.0 if ptd >= 55.8 else
                                 13.5 if ptd >= 34.8 else
                                 8.5 if ptd >= 24.8 else
                                 5.1 if ptd >= 18.0 else 3.1)
    return Derived(v)



# --- part-studio formulas that TWO parts share --------------------------------
#
# Not studio variables — each is a sketch's own expression — but written once
# here rather than once per part, which is the rule this module exists for.
# A part-studio formula ONE part uses stays in that part (the Lid's text
# offsets, the Topper's `#LogoEdgeDist`); these are the ones that were found
# transcribed twice, and in one case as reciprocals of each other.


def cascade_slope(d, slider_distance):
    """`dZ/dY` of the cascade diagonal — the Holder's `Top slant angle` and,
    inverted, the Box's lip angle (`Import Holder patterns` brings it across).

    The sketch's own expression (Allan's screenshot, 2026-09-04): a triangle
    whose vertical leg is

        max(#calSlotDepth + 2mm, #calHeightIncrement - 1mm)

    and whose top leg is `slider_distance - 1.2`. `#calSlotDepth` is the
    STANDARD slot depth even on the first-riser holder — the 246 first-riser
    reference reads 0.7812, which only the rise term gives there — while
    `slider_distance` is `calSliderDistance` for a standard holder and
    `calFirstSliderDistance` for the first-riser one and for the Box's lip,
    which meets the front holder. The rise term wins on every row in the
    catalogue, by 0.667 at the tightest (`S9.21.10.62-Sl`, 8.000 against
    8.667), and `tests/test_derive.py` says so; a row where the slot depth won
    would put a steeper diagonal on that holder, exactly as Onshape would.
    Measured off the slant faces' normals on three Holder references (1.7857 /
    0.7812 / 1.2037 predicted and read) and off the diagonal of all 50 cached
    holders for the Box.
    """
    rise = max(d.calSlotDepth + 2.0, d.calHeightIncrement - 1.0)
    return rise / (slider_distance - 1.2)


def back_slot_pitch(d):
    """`#dBackSlotWidth` — the rear pusher storage's pitch along X: the stored
    pusher's own depth plus 2.000 of clearance a side. Read off the rim
    cutouts of four Box STEPs; `assembly.py` places the pushers by it."""
    return d.calPusherTotalDepth + 4.0
