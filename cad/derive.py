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
    """Immutable attribute view over the computed variable set."""
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
    v["CardHeight"] = 58.0 if g == "CraftGutermann" else 92.0
    v["gameUnsleevedCardWidth"] = T.UNSLEEVED_CARD_WIDTH[g]
    v["game10UnsleevedCardThickness"] = T.TEN_UNSLEEVED_THICKNESS[g]
    v["game10SleevedCardThickness"] = T.TEN_SLEEVED_THICKNESS.get(g)

    v["calCardThickness"] = (v["game10UnsleevedCardThickness"] if p.isSleeved == 0
                             else v["game10SleevedCardThickness"]) / 10
    v["calCardwidth"] = v["gameUnsleevedCardWidth"] + {0: 0.0, 1: 2.0}[p.isSleeved]
    v["calSlotwidth"] = 3.0 + v["calCardwidth"]
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
    # NB the studio tests GameName == "None", which no game is, so this is
    # always calSliderSpaceLeftRight. Transcribed as written — see DERIVED.md.
    v["calFrontDividerLeftSpacing"] = 0.0 if g == "None" else v["calSliderSpaceLeftRight"]
    v["calFirstLeftFrontDividerDist"] = v["calSlotwidth"] + v["calFrontDividerLeftSpacing"]

    v["calPusherTotalDepth"] = ((p.RisingSliders - 1) * v["calSliderDistance"]
                                + v["calFirstSliderDistance"])
    # --- pre-7.0 tab placement; superseded by calTabCentreDistance ----------
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
    v["calFrontTotalCapacity"] = v["calFrontSlotsForCards"] * p.FrontPocketCardCapacity
    v["calTotalCards"] = (v["calRisingTypeCapacity"] * p.CardsPerSlidingSlot
                          + v["calFirstSlotRisingCardCapacity"]
                          + v["calFrontTotalCapacity"])
    v["calAllTypeCapacity"] = v["calRisingTypeCapacity"] + p.HorizontalSlots

    v["ProductName"] = "Craft Cascade" if g == "CraftGutermann" else "Card Cascade"
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
