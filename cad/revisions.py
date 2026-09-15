"""The release line, and what changed at each release.

`cad/` can build any release in `RELEASES`, and this module is the ONLY place
that says how one differs from another — as `derive.py` is the only place a
variable-studio formula lives and `assembly.py` the only place a placement
does. `spec/REVISIONS.md` holds the whole of the procedure below.

A **REVISION CHANGE** is `cad/` 7.0 against `cad/` 7.1, a design decision that
ships in a release, and it belongs HERE. A **DIVERGENCE** is `cad/` against
Onshape at the SAME version, permanent, and belongs in the part. Not mixing
them is what this module exists for: a flag here means "the design changed",
never "Onshape and we disagree".

Two rules keep it generalisable. **A part asks a NAMED question and never
compares versions** — `d.rev.<flag>`, not `d.Version >= "7.1"`. **The line is
monotonic**: a change introduced at 7.1a is in every release after it, and
undoing one is a NEW flag with its own `since`, not a hole in this table.

An unreleased release is iterated by LETTER — `7.1a`, `7.1b`, ... and then
plain `7.1` at the lock — so two parts printed from the same unreleased
release can be told apart on the shelf. A letter is a release like any other,
frozen once it is passed; at the lock the plain release joins the END of the
line, keeping the letters and every flag they introduced, and no flag's
`since` ever moves.
"""
from dataclasses import dataclass, field, fields

from .refuse import refuse

# Every release `cad/` can build, oldest first; `CURRENT` is the build
# default. A LETTER is a release being iterated and the plain release sits at
# the END of its letters. Letters are NEVER renamed or removed — a version
# that has been printed has to remain describable and buildable.
# `spec/REVISIONS.md` says what each one changed.
RELEASES = ("7.0", "7.1a", "7.1b", "7.1c", "7.1d", "7.1", "7.2a", "7.2b", "7.2c",
            "7.2d", "7.2e", "7.2f", "7.2g", "8.0")
CURRENT = "8.0"


@dataclass(frozen=True)
class Rev:
    """What is true of the release being built. One field per design change.
    `since` is the release the change SHIPS IN and `spec` is where it is
    written down; both live here, so a field and its record cannot drift."""

    two_pushers: bool = field(metadata={
        "since": "7.1a",
        "spec": "spec/BOX.md, 'Two pusher slots, at every size'",
        "what": "every cascade takes TWO pushers, whatever its size: "
                "`#calPusherSlots` is 2 rather than 2-for-Innovation-and-S-"
                "else-3, so 24 boxes lose a rear storage slot, its divider "
                "and its rim cutouts, their thumb cutout centres, and their "
                "projects ship one Pusher fewer. The Lid follows through "
                "`lid_socket_per_pusher`",
    })

    lid_socket_per_pusher: bool = field(metadata={
        "since": "7.1a",
        "spec": "spec/LID.md, 'The middle socket is gone'",
        "what": "the Lid cuts one pusher socket per pusher the cascade ships "
                "instead of Onshape's plain size rule, so the four Innovation "
                "M lids lose their unused MIDDLE socket",
    })

    rear_thumbs_spread: bool = field(metadata={
        "since": "7.1b",
        "spec": "spec/BOX.md, 'A thumb cutout every 70 mm of back pocket'",
        "what": "the back pocket gets as many `Thumb Cutout in back`s as it "
                "takes to put one every REAR_THUMB_PITCH (70.000) along it, "
                "spread evenly and centred on the pocket (Allan). One cutout "
                "served every pocket at 7.1a, and 45 of the 50 are over "
                "100 mm wide, four of them over 280. "
                "`#calFingerHoleOffset` stops placing it: the pocket does",
    })

    stout_lattice: bool = field(metadata={
        "since": "7.1c",
        "spec": "spec/BOX.md and spec/HOLDER.md, 'A stouter lattice'",
        "what": "the lattice window is 9.000 wide rather than 10.000 and "
                "there are FOUR rows of them where there were three — the "
                "Box's `Hanging holes` and the Holder's `Vertical slits in "
                "holder` alike, and the front pocket's slits with them, "
                "being the same openings (Allan, 2026-09-09). The pillar "
                "between two windows takes the whole 1.000 the window gives "
                "up, because the mullion is what absorbs the pitch; and it "
                "is tied back to a bridge after 13.125 rather than 18.167. "
                "Both halves are for the PILLARS, which break: the Holder's "
                "are 1.800 x 0.800 at the narrowest slot width and print as "
                "isolated islands standing free the whole window height, so "
                "they snap at the base mid-print and end up hanging from the "
                "bridge that closed over them. Filleting the window corners "
                "was tried first and is NOT this: it prints worse, because a "
                "fillet at a window's top corner turns a clean short bridge "
                "into an overhang. Sides vertical, top horizontal",
    })

    both_lid_editions: bool = field(metadata={
        "since": "7.1d",
        "spec": "spec/LID.md, 'Both editions ship, on a plate each'",
        "what": "a cascade that carries a NON-DEFAULT edition of its game's "
                "mark ships the default one as well, as a second Lid on a "
                "plate of its own (Allan, 2026-09-10). That is Innovation's "
                "two single-set cascades and so four projects: each gets the "
                "plain `Innovation` lid it already carried and an `Innovation "
                "Ultimate` lid beside it, and its owner prints whichever the "
                "shelf should read. No lid's GEOMETRY moves — the alternate "
                "is the same lid with the other mark in its underside, fitted "
                "by the same rule — so this is a change to what a project "
                "CONTAINS, as `two_pushers` was",
    })

    thick_floor: bool = field(metadata={
        "since": "7.1a",
        "spec": "spec/BOX.md, 'The floor is 2.000, and it grows UPWARD'",
        "what": "the Box's floor is 2.000 where every wall stays "
                "WallThickness's 1.600 (Allan). It grows UPWARD into the "
                "cavity, so BoxHeight, the rim and every bed-referenced "
                "feature of the lock are exactly where they were and the "
                "0.400 comes out of the interior, which has 12.900 of "
                "headroom on all 50 rows. The Lid keeps its 1.600 floor",
    })

    rear_holder: bool = field(metadata={
        "since": "7.2a",
        "spec": "spec/HOLDER.md, 'The RearHolder'",
        "what": "every cascade's REARMOST holder is a `RearHolder`: the same "
                "holder without its rear lips, which hook the holder behind "
                "and behind the rearmost there is only the box's back wall, "
                "0.950 away, which a shallow slant's lips reach past (0.3-0.4 "
                "of interference on Dominion's 8- and 9-riser cascades, 0.65 "
                "on a deep holder at the back; Allan, 2026-09-13). It replaces "
                "one plain Holder in every project, and where the rearmost "
                "slot is the deep one (`Deep slot` = back) it replaces the "
                "FirstHolder, taking that holder's depth and slant under the "
                "RearHolder name. Before the flag every holder has lips",
    })

    unmarked_lid: bool = field(metadata={
        "since": "7.2b",
        "spec": "spec/LID.md, 'An unmarked lid, on a plate of its own'",
        "what": "every cascade ships a SECOND lid on a plate of its own, "
                "with no mark in its underside and `(C) Mertner` embossed "
                "where the game's name is on the lid the cascade carries "
                "(Allan, 2026-09-13). Everything else on it — the capacity "
                "and model lines, the Card Cascade block, the sockets, the "
                "grooves — is the cascade's own lid's. A change to what a "
                "project CONTAINS, as `both_lid_editions` was: no existing "
                "lid moves, and Innovation's single-set cascades ship three",
    })

    larger_lid_text: bool = field(metadata={
        "since": "7.2c",
        "spec": "spec/LID.md, 'The text block grows with the lid'",
        "what": "the Lid's three-line text block (capacity, game name or "
                "credit, model) is scaled up where the lid has room — every "
                "cap and gap by one factor per cascade, anchored at its cap "
                "top and right edge, growing left and down until it is a "
                "line gap from the Card Cascade block (the left socket on an "
                "XS lid) or keeps at the front wall what it keeps at the "
                "back, and never past 1.5 (Allan, 2026-09-13: larger where "
                "space permits, not filling the space). M and L lids reach "
                "1.5 but the four shallowest, S lids 1.0-1.37, XS 1.07-1.18; "
                "the Card Cascade block is untouched. Before the flag every lid's block is 3.5/3.5/"
                "3.0 cap",
    })

    plain_box_plate: bool = field(metadata={
        "since": "7.2d",
        "spec": "spec/BOX.md, 'A plain box on a plate of its own'",
        "what": "a cascade whose parts.csv row sets `Plain box` ships a "
                "SECOND box on a plate of its own, at the END of the project: "
                "the same box built without its front and side label holders "
                "(`isLabelHoldersOnBox = 0`, the option the `Label holders` "
                "column has turned off since 2026-09-05), for an owner who "
                "wants no label on the shelf (Allan, 2026-09-13: Compile's "
                "three rows). A change to what a project CONTAINS, as "
                "`unmarked_lid` was: no box moves, the ordinary one stays on "
                "plate 1 with its pushers, and the plain one is an "
                "alternative to it, printed instead of it. Which rows: the "
                "column, asked only through `build.ships_plain_box`",
    })

    seated_lips: bool = field(metadata={
        "since": "7.2e",
        "spec": "spec/HOLDER.md, 'Lips that seat'",
        "what": "every lip seats in the rest of the part behind it when the "
                "cascade is open, and reaches no further (Allan, 2026-09-13, "
                "off flat cascades whose lips were too long). Three formulas "
                "become one rule: the slant is the cascade's own diagonal, "
                "`calHeightIncrement / sliderDistance` (`derive.cascade_"
                "slope`), so a holder's lip band lands exactly on the notch "
                "band of the holder behind; a lip reaches the gap plus one "
                "wall in Y — 1.200 for a holder's rear lips, 2.050 for the "
                "box's — instead of 2.100 along the slant, which was 0.38 to "
                "1.81 in Y; and the rest is notched through the whole front "
                "wall, the lip's base plus REST_CLEARANCE wide and deep "
                "enough for the box lip too, instead of starting "
                "2*calSlotDepth along the slant, which left 333-Sl a 0.33 "
                "notch and 246-Sl none. Before the flag the lips of 246 Sl, "
                "333 Sl and M8.16 Sl land on the wall behind (134 / 46 / 35 "
                "mm3 in play) and the box lip touches only six front holders, "
                "all under their notch",
    })

    ribs_forward: bool = field(metadata={
        "since": "7.2f",
        "spec": "spec/BOX.md, 'The ribs move forward'",
        "what": "the slider ribs — and so every holder — move forward by "
                "`box.rib_shift` (0.850) so the front holder is CardHolderGap "
                "0.400 from the divider panel, as every holder is from the "
                "one behind it, instead of 1.250 (Allan, 2026-09-14: the box "
                "lip should not have further to go than a holder's). The box "
                "lip becomes a wedge — underside on the slant, front face "
                "slanting back up to a flat top LIP_SINK under the holder's "
                "slant — that BITES that wall by LIP_BITE "
                "0.150 — inside the holder's 0.200 rib slack, so the holder "
                "still slides straight down its ribs past it (a lip that "
                "fills the wall, 7.2e's, stops it dead: a holder cannot pass "
                "a fixed lip on the way in) — with its top on the holder's "
                "slant at the wall's face in play (`box.lip_z`, on a 0.800 "
                "post above the panel's bevel) so every rest is the plain "
                "2.200 and every lip floats 0.200. The lid and pusher do not "
                "move, so a holder now hangs 0.500 past the front edge of "
                "its tread instead of sitting 0.350 inside it; the rearmost "
                "holder is 1.800 from the back wall instead of 0.950. A "
                "prototype: `cad.testkit` builds one-slot cascades to print "
                "it before the catalogue moves",
    })

    shorter_box: bool = field(metadata={
        "since": "7.2f",
        "spec": "spec/BOX.md, 'The box loses the room behind the last holder'",
        "what": "with the ribs forward (`ribs_forward`) the rearmost holder "
                "sat 1.800 from the inner back wall; the box and the lid lose "
                "`calRearTrim` (1.400) of depth so it sits CardHolderGap "
                "0.400 there, like every holder from the next (Allan, "
                "2026-09-14, off the kit A print). The ribs keep their place "
                "against the front pocket (`box.rib_shift` is derived from "
                "the depth and comes out 0.550 BACK of the studio's rule), "
                "and the lid's pusher sockets move with them "
                "(`lid.socket_back`) so every holder sits CENTRED on its "
                "tread, 0.200 each way, where 7.0 had it 0.150 off and the "
                "rib shift alone 0.500 over the front edge. Every box and lid "
                "in the catalogue is 1.400 shallower; a 7.2f lid does not fit "
                "an earlier box",
    })

    unsleeved_card_width: bool = field(metadata={
        "since": "7.2g",
        "spec": "spec/BOX.md, 'The unsleeved XS box is as wide as its twin'",
        "what": "a row may state its UNSLEEVED cards' width outright "
                "(`Primary.UnsleevedCardWidth`, parts.csv's `Unsleeved card "
                "width`), as it has been able to state its sleeved ones since "
                "7.2a. One row takes it: `Single Mini` at 66, the sleeved "
                "width, so the unsleeved twin's box grows 148.300 -> 152.300 "
                "and its lid 152.900 -> 156.900, the same as the sleeved "
                "cascade's (Allan, 2026-09-14). It reaches everything the card "
                "width does — slot, box, lid, holders, toppers — and nothing "
                "else: `calCardThickness` stays unsleeved, so the capacity, "
                "the depth and the rise do not move and the model code stays "
                "`XS5.15.10.32-Un`. It is what makes four unsleeved pushers "
                "fit the back (145.600 of 149.100 inner, against 145.100 "
                "before), and it makes the pair's two lids interchangeable. "
                "GATED because `Single Mini` has a 7.0 corpus behind it — "
                "`individual/` and `spec/reference/Box Innovation 130U.step` — "
                "which an ungated column would restate",
    })

    back_pocket_variants: bool = field(metadata={
        "since": "7.2g",
        "spec": "spec/BOX.md, 'Two back pockets, and no ordinary box'",
        "what": "a row may ship back-pocket VARIANT boxes IN PLACE OF the "
                "ordinary one (parts.csv's `Back pocket`, asked only through "
                "`build.back_pocket_variants_built`). `Single Mini` ships two "
                "(Allan, 2026-09-14), because it is used in PAIRS and the two "
                "halves want different backs: `open` has no dividers, no "
                "cavities and no rim cutouts, so the whole slot band is empty "
                "from the floor up and the pocket is the full inner width — "
                "149.100, which takes the 128 mm player aids where the "
                "ordinary box's 71.500 / 50.500 does not; `notches` hangs as "
                "many pushers as the width takes — 4 unsleeved, 3 sleeved, "
                "since their pushers are 32.000 and 44.500 deep — and has no "
                "thumb cutout, there being no pocket left to reach into. The "
                "count is DERIVED (`box.storage_slot_count`), never stated. "
                "The Lid does not follow: `calPusherSlots` is how many pushers "
                "the CASCADE ships and stays 2, so both boxes take the same "
                "lid. A change to what a project CONTAINS, as "
                "`plain_box_plate` was — except that here the ordinary box is "
                "REPLACED rather than joined",
    })


# A version is a STRING and not a number: it may be anything short enough to
# engrave, so NOTHING here parses one. A release's order is its POSITION in
# `RELEASES`, and a version not on the line has no position and no flags.
#
# Easy to trip over: the engraved stamp reader reads `digit . digit` plus an
# unidentifiable trailing mark (`verify._dotted`), so a version of any other
# shape is checkable by its METADATA alone.


def position(version):
    return RELEASES.index(version) if version in RELEASES else None


def at_least(version, since):
    """Is `version` at or after the release `since` shipped in? `since` is
    always a release on the line; `version` may be a HISTORICAL one, and a
    version off the line is BEFORE it by construction."""
    here, there = position(version), position(since)
    if there is None:
        refuse(f"{since!r} is not a release; a flag's `since` must be one of "
               f"{', '.join(RELEASES)}")
    return here is not None and here >= there


def check(version):
    """The version, or a refusal naming the line. A typo has to fail HERE:
    left to fall through it would build the current geometry under a stamp
    naming a release that does not exist."""
    if version not in RELEASES:
        refuse(f"unknown release {version!r}; cad/ builds one of "
               f"{', '.join(RELEASES)} (cad/revisions.py)")
    return version


# Versions that predate the line and are still asked about by name: a cached
# component or a reference STEP may carry one, and it correctly gets none of
# the line's flags. Naming them is what lets `of` refuse everything else —
# with versions as opaque strings no arithmetic can tell an old release from a
# typo, so the answer is a LIST.
HISTORICAL = ("6.3", "6.4", "6.5", "6.6")


def of(version):
    """The `Rev` for a version: every change introduced at or before it.

    NOT `check`: it also takes a HISTORICAL version, which the corpus needs to
    describe its own references, and gives it no flags. Anything else is
    refused. What a CLI may BUILD is narrower still (`check`).
    """
    if version not in RELEASES and version not in HISTORICAL:
        refuse(f"unknown version {version!r}; cad/ builds "
               f"{', '.join(RELEASES)} and knows the older "
               f"{', '.join(HISTORICAL)} by name — add it to "
               f"cad/revisions.RELEASES first")
    return Rev(**{f.name: at_least(version, f.metadata["since"])
                  for f in fields(Rev)})


def flags():
    return fields(Rev)


def previous(version):
    i = RELEASES.index(check(version))
    return RELEASES[i - 1] if i else None
