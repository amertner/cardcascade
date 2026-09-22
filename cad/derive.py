"""Primary -> Derived. Every formula in the model, exactly once.

A faithful transcription of the Onshape variable studio, **in studio order**,
one statement per variable, keeping Onshape's names, so that reviewing it
against the studio is mechanical (`spec/DERIVED.md`). Lengths are mm and
angles degrees throughout; nothing here imports build123d. No component module
may recompute any of this: read it from `Derived`.
"""
import dataclasses

from . import revisions as REV
from . import tables as T

STUDIO_BOX_HEIGHT = 105.0          # every studio game but Colours
STUDIO_LID_HEIGHT = 40.0
STUDIO_CARD_HEIGHT = 92.0
STUDIO_LABEL_HEIGHT = 22.2         # `labelmaker.LABEL_HEIGHT`
PocketHeight = 75.0
FrontPocketHeight = 75.0
BoxRearPusherSupportDepth = 1.0     # slot in rear of box supporting the pusher
HolderSideSlotWidth = 5.0
LeanAngle = 0.0                     # pusher/card lean — NOT CURRENTLY USED
WallThickness = 1.6
Gripperwidth = 0.5                  # side closing grip holding box and lid
CardHolderGap = 0.4                 # gap between holders
PusherFootDepth = 5.0
PusherThickness = 3.0
# Mirrors of part constants `calRearTrim` needs; tests/test_box.py holds them
# equal.
BOX_FRONT_DIVIDER = 1.0
BOX_SLIDER_W = 1.5
HOLDER_DEPTH_GAP = 0.4
PusherFootThickness = 1.6
# How far the Lid's pusher socket sits in from its inner wall — and, less
# 1.000, where the logo's cap top goes: the box's two walls and the plate
# between them, plus 1.2 of clearance.
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
LipHeight = 2.0


class Derived:
    """Immutable attribute view over the computed variable set.

    It carries EVERY variable the studio computes, not only the ones a part
    reads: `derive()` is a transcription. Do NOT prune the unread ones.
    """
    __slots__ = ("_v", "rev")

    def __init__(self, v, rev):
        object.__setattr__(self, "_v", dict(v))
        # `rev` is NOT a studio variable and so is not in `_v`: it is what the
        # RELEASE says about the design. It rides on the Derived so that every
        # feature still takes `d` alone.
        object.__setattr__(self, "rev", rev)

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
    """The studio, in order. `p` is a params.Primary and its inputs come onto
    the Derived BY NAME, so nothing below `derive` handles a Primary."""
    v = dataclasses.asdict(p)
    g = p.GameName
    # The RELEASE, resolved once because `calPusherSlots` below depends on it.
    rev = REV.of(p.Version)

    # cad/ adds a HEIGHT CLASS (`tables.HEIGHT_CLASS`): its box and label.
    cls = T.HEIGHT_CLASS.get(g)
    # cad/ only: the class a part asks about, "" for a studio game.
    v["HeightClass"] = cls or ""
    v["BoxHeight"] = T.BOX_HEIGHT.get(
        g, T.CLASS_BOX_HEIGHT.get(cls, STUDIO_BOX_HEIGHT))
    v["LabelHeight"] = T.CLASS_LABEL_HEIGHT.get(cls, STUDIO_LABEL_HEIGHT)
    # The label holder sits between two lid rims (`lid_drop`), so the lid
    # takes half of what the box loses and half of what the label gives back.
    # Written as differences, exactly 40.0 for every studio game.
    v["LidHeight"] = T.LID_HEIGHT.get(
        g, STUDIO_LID_HEIGHT + ((v["BoxHeight"] - STUDIO_BOX_HEIGHT)
                                - (v["LabelHeight"] - STUDIO_LABEL_HEIGHT)) / 2)
    # 92.0 for every studio game; the studio's CraftGutermann branch is
    # deprecated and removed here (cad/tables.py). cad/ adds a game of
    # shorter cards (`tables.CARD_HEIGHT`).
    v["CardHeight"] = T.CARD_HEIGHT.get(g, STUDIO_CARD_HEIGHT)
    v["gameUnsleevedCardWidth"] = T.UNSLEEVED_CARD_WIDTH[g]
    v["game10UnsleevedCardThickness"] = T.TEN_UNSLEEVED_THICKNESS[g]
    v["game10SleevedCardThickness"] = T.TEN_SLEEVED_THICKNESS.get(g)

    v["calCardThickness"] = (v["game10UnsleevedCardThickness"] if p.isSleeved == 0
                             else v["game10SleevedCardThickness"]) / 10
    v["calCardwidth"] = v["gameUnsleevedCardWidth"] + {0: 0.0, 1: 2.0}[p.isSleeved]
    # A row may state its sleeved cards' width outright (cad/ only,
    # `Primary.SleevedCardWidth`), the studio's +2.000 being a game-wide guess.
    if p.isSleeved and p.SleevedCardWidth:
        v["calCardwidth"] = p.SleevedCardWidth
    # And from 7.2g the mirror of it (`rev.unsleeved_card_width`), which makes
    # a twin pair one width and their lids interchangeable. GATED, the rows
    # that take it having a 7.0 corpus behind them. WIDTH only:
    # `calCardThickness` is untouched, so capacity, depth and rise stay put.
    if not p.isSleeved and p.UnsleevedCardWidth and rev.unsleeved_card_width:
        v["calCardwidth"] = p.UnsleevedCardWidth
    v["calSlotwidth"] = 3.0 + v["calCardwidth"]
    # `#BoxWidth` is a SKETCH variable, not a studio one — here because
    # `calTokenHolderSlotWidth` below is written in terms of it and a second
    # copy of the expression is what this module exists to prevent.
    v["BoxWidth"] = 2 * WallThickness + 11.1 + v["calSlotwidth"] * p.HorizontalSlots
    # `#calPusherSlots` is the second sketch variable: how many pushers the
    # rear storage takes, and the one variable here that depends on the
    # RELEASE. `isOnlyTwoPusherSlots` below is the studio's own answer.
    v["calPusherSlots"] = 2 if rev.two_pushers else (
        2 if (g == "Innovation" or p.HorizontalSlots <= 3) else 3)
    v["calSlotDepth"] = v["calCardThickness"] * p.CardsPerSlidingSlot
    v["calFirstSlotDepth"] = (v["calSlotDepth"] if p.isFirstSlidingSlotOverride == 0
                              else v["calCardThickness"] * p.FirstSlidingSlotCards)

    v["calDesiredHeightIncrement"] = T.DESIRED_HEIGHT_INCREMENT[g]
    # The rise per riser, confirmed by `verify.audit_rises` off a printed
    # pusher.
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
    # Transcribed because the studio still has them; NOTHING reads them, cad/
    # building only the 7.0 lock (`lock.SAME_LOCK`).
    v["calNumTabs"] = 2 if v["calPusherTotalDepth"] > 18.0 else 1
    v["calTabDistance"] = (v["calPusherTotalDepth"]
                           - v["calNumTabs"] * (TabWidth + TabLeftMargin) + TabWidth)
    v["calTabToTapDistance"] = max(0.0, (v["calTabDistance"] - TabWidth) / 2)
    v["calPusherMarginToRight"] = (v["calPusherTotalDepth"] - TabLeftMargin
                                   - (v["calNumTabs"] - 1)
                                   * (v["calTabDistance"] + TabWidth))
    # -----------------------------------------------------------------------
    v["calPusherTotalHeight"] = v["calHeightIncrement"] * p.RisingSliders
    # cad/ only: where the deeper first-riser slot sits. The studio puts it at
    # the FRONT; `Deep slot = back` moves it to the back rib and the pusher's
    # last drop (`assembly.holder_rib`).
    v["isDeepSlotAtBack"] = 1 if (p.DeepSlotAtBack and p.isFirstSlidingSlotOverride) else 0
    v["calFrontPocketDepth"] = v["calCardThickness"] * p.FrontPocketCardCapacity
    v["calAngleDelta"] = 0.0    # sin(LeanAngle) * BoxHeight; LeanAngle is 0

    # cad/ only, from 7.2f (`rev.shorter_box`): how much shallower the box and
    # the lid are than the studio's rule. With the ribs forward the rearmost
    # holder stands 1.800 from the back wall; this takes that to CardHolderGap
    # (`spec/BOX.md`, "The box loses the room behind the last holder").
    front_space = 6.0 - 2 * WallThickness - BOX_FRONT_DIVIDER          # 1.800
    overhang = BOX_SLIDER_W / 2 - HOLDER_DEPTH_GAP / 2                 # 0.550
    rear_gap = BOX_SLIDER_W / 2 + HOLDER_DEPTH_GAP / 2                 # 0.950
    rib_shift = front_space - overhang - CardHolderGap                 # 0.850
    v["calRearTrim"] = (rear_gap + rib_shift - CardHolderGap) if rev.shorter_box else 0.0
    v["calLidDepth"] = ((8.5 + (p.RisingSliders - 1) * v["calSliderDistance"]
                         + v["calFirstSliderDistance"])
                        + v["calFrontPocketDepth"] + WallThickness
                        + PusherThickness + 1.0 - v["calRearTrim"])
    # The side label's width is read off the STUDIO's lid depth, BEFORE
    # `calRearTrim`: it is a digit of the model code, which is an identity,
    # and 7.2f's trim would otherwise rename two rows' boxes.
    d = v["calLidDepth"] + v["calRearTrim"]
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
    # their slots. Transcribed as Allan wrote it (spec/TOKENHOLDER.md);
    # HorizontalSlots cancels out, so a token holder's size depends on the
    # card width and the Mat flag alone.
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

    # The studio's other branch was "Craft Cascade" for the deprecated
    # CraftGutermann (cad/tables.py).
    v["ProductName"] = "Card Cascade"
    v["gameShortName"] = T.GAME_SHORT_NAME[g]
    # cad/ only: what a part engraves where the game's name goes — CREDIT for
    # a GENERIC game (`tables.GENERIC_GAMES`), else the name itself.
    v["GameText"] = T.CREDIT if g in T.GENERIC_GAMES else g
    # The studio's rule, AND the one input Onshape does not have: parts.csv's
    # `Label holders` column can turn them OFF on a box the rule would give
    # them to. It cannot turn them ON where the rule says no.
    v["isLabelHoldersOnBox"] = (0 if g == "Colours" or p.HorizontalSlots <= 1
                                else p.LabelHolders)
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
    # cad/ only: a HEIGHT CLASS's box leads its codes with its height,
    # `86-L6.10.10.32.Un`; a studio box's codes are the studio's.
    pre = f"{v['BoxHeight']:g}-" if cls else ""
    v["calHolderModel"] = (f"{pre}{v['calSizeLetter']}.{p.CardsPerSlidingSlot}{slv}{mat}")
    v["calTokenHolderModel"] = (f"{pre}{v['calSizeLetter']}{p.FrontPocketCardCapacity}"
                                f"{mat}{slv}")
    v["calModelName"] = (
        f"{pre}{v['calSizeLetter']}{p.RisingSliders}.{p.FrontPocketCardCapacity}"
        f".{p.CardsPerSlidingSlot}"
        f"{'' if p.isFirstSlidingSlotOverride == 0 else '-' + str(p.FirstSlidingSlotCards)}"
        f".{v['calSideLabelWidth']}{mat}{slv}")
    v["calCapacityLabel"] = f"{v['calTotalCards']} Cards/{'S' if p.isSleeved == 1 else 'U'}"
    v["calVersion"] = f"CC {p.Version}"

    # From v7: tabs sit this far from the pusher's centreline — the C1..C5
    # lock catalogue of LOCK_STANDARD.md, as a ladder on depth.
    ptd = v["calPusherTotalDepth"]
    v["calTabCentreDistance"] = (24.0 if ptd >= 55.8 else
                                 13.5 if ptd >= 34.8 else
                                 8.5 if ptd >= 24.8 else
                                 5.1 if ptd >= 18.0 else 3.1)
    return Derived(v, rev)


# Not studio variables — each is a sketch's own expression — but written once
# here rather than once per part. A part-studio formula ONE part uses stays in
# that part; these were found transcribed twice.


def cascade_slope(d, slider_distance):
    """`dZ/dY` of the cascade diagonal — the Holder's `Top slant angle` and,
    inverted, the Box's lip angle.

    The studio's own expression is a triangle whose vertical leg is
    `max(#calSlotDepth + 2mm, #calHeightIncrement - 1mm)` and whose top leg is
    `slider_distance - 1.2`; `#calSlotDepth` is the STANDARD slot depth even
    on the first-riser holder. **From 7.2e (`rev.seated_lips`) the slant IS
    the diagonal**, `calHeightIncrement / slider_distance`, so one holder's
    slant plane continues the next one's and its rear lips land exactly on the
    notch band of the holder behind (`spec/HOLDER.md`, "Lips that seat").
    """
    if d.rev.seated_lips:
        return d.calHeightIncrement / slider_distance
    rise = max(d.calSlotDepth + 2.0, d.calHeightIncrement - 1.0)
    return rise / (slider_distance - 1.2)


# The Box's MEASURED Z datums are the studio's 105 box's. Each follows ONE
# of three things, and these say how far that thing has moved from the
# studio's: 0.000 for every studio game (`spec/BOX.md`, "Shorter cards").

def rim_drop(d):
    """The box's RIM: the bump, the rim cutouts, `REAR_TOP` and the lattice
    under it."""
    return d.BoxHeight - STUDIO_BOX_HEIGHT


def card_drop(d):
    """The CARDS: the pocket cut and front thumb (`POCKET_CUT_TOP`), the
    pre-7.2f box lip. A class box taller than its cards need moves these
    with the cards, not with the rim."""
    return d.CardHeight - STUDIO_CARD_HEIGHT


def lid_drop(d):
    """The rim of the lid the box STANDS IN, in play: the label holder's
    bottom stays 2.100 above it."""
    return d.LidHeight - STUDIO_LID_HEIGHT


def closed_rim_drop(d):
    """The CLOSED lid's rim: the lowered front stays 2.000 above it, and the
    label holder's fasteners 1.100 below. With `LidHeight` from `derive`,
    the label fits between the two rims exactly as on the 105 box."""
    return (d.BoxHeight - d.LidHeight) - (STUDIO_BOX_HEIGHT - STUDIO_LID_HEIGHT)


def back_slot_pitch(d):
    """`#dBackSlotWidth` — the rear pusher storage's pitch along X: the stored
    pusher's own depth plus 2.000 of clearance a side."""
    return d.calPusherTotalDepth + 4.0
