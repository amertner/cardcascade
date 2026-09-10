"""The release line, and what changed at each release.

`cad/` can build any release in `RELEASES`, and this module is the ONLY place
that says how one differs from another — as `derive.py` is the only place a
variable-studio formula lives and `assembly.py` the only place a placement
does. `spec/REVISIONS.md` is the record.

## A REVISION CHANGE is not a DIVERGENCE

Two things differ from Onshape and they are not the same kind of thing:

* a **DIVERGENCE** is `cad/` against Onshape at the SAME version, and it is
  permanent — the Box's hanging holes stopping at the slot band, its `CC`
  where the sketch says `Rev`, the XS box's one fastener, the Lid's fitted
  logo. It applies at every release and belongs in the part, recorded in
  `spec/` and asserted from both ends (`cad/README.md`, decision 6).
* a **REVISION CHANGE** is `cad/` 7.0 against `cad/` 7.1 — a design decision
  that ships in a release. It belongs HERE, and a build at the earlier release
  must keep reproducing what `individual/` holds, forever.

Mixing them is what this module exists to stop. A flag here means "the design
changed"; it never means "Onshape and we disagree".

## The two rules that keep it generalisable

**A part asks a NAMED question and never compares versions.** `d.rev.<flag>`,
not `d.Version >= "7.1"` — the flag name is what `spec/` records and what a
reader greps for, and adding the next change is one field here and one `if`
in the part.

**The line is monotonic.** A change introduced at 7.1a is in every release
after it; that is what a release line means. Undoing one is a NEW flag with
its own `since`, not a hole in this table.

## An unreleased release is iterated by LETTER

`7.1a`, `7.1b`, `7.1c`, ... and then plain `7.1` at the lock (Allan,
2026-09-08). The letter exists so that two parts printed from the SAME
unreleased release can be told apart on the shelf: while 7.1 is being worked
on, its geometry moves, and a shelf full of parts all stamped `CC 7.1` cannot
say which of them is which.

So **a letter is a release like any other** — a full member of `RELEASES`, with
its own position, its own `SAME_LOCK` entry and its own stamp signature — and
that is what makes the letter mean something: a change lands as a flag whose
`since` is the NEW letter, so `7.1a` keeps building what `7.1a` always built
and the part stamped with it stays reproducible. A letter that were only a
build marker, with the flags still keyed on `7.1`, would let two different
geometries wear the same stamp, which is the thing this is here to stop.

**Bumping.** A design change during 7.1 opens the next letter: add it to
`RELEASES` and `lock.SAME_LOCK`, move `CURRENT` on, give the new flag
`since: "<the new letter>"`, and leave the earlier letters' flags alone —
monotonicity carries them forward. Nothing is rebuilt in place; the earlier
letter is frozen, which is exactly what a version stamped on plastic has to be.

**At the lock**, plain `7.1` joins the END of the line and becomes `CURRENT`.
The letters STAY on it: parts printed at `7.1b` exist, and this repo's rule is
that a version you can hold must remain describable and buildable. `7.1` sits
after them all, so it carries every flag they introduced.

**7.1 was locked on 2026-09-10** and this is what it looks like: `RELEASES`
ends `..., "7.1d", "7.1"`, `CURRENT` is `7.1`, `lock.SAME_LOCK` admits it, and
not one flag's `since` moved — they still name the letter each change shipped
in, which is what keeps the letters meaning something and what
`tests/test_revisions.py` isolates them by. The next change opens `7.2a`, not
`7.1e`: `7.1` is on the line now, so a change after it is a change after the
release.
"""
from dataclasses import dataclass, field, fields

from .refuse import refuse

# Every release `cad/` can build, oldest first. `CURRENT` is what a build
# defaults to; an older one is still buildable and is what every reference
# STEP and cached mesh in `individual/` is compared against.
#
# `7.1a` .. `7.1d` were 7.1 being ITERATED, and the LETTER was the point (Allan,
# 2026-09-08): see "An unreleased release is iterated by LETTER" below.
#
# **7.1 is LOCKED** (Allan, 2026-09-10) and sits at the END of the line, which
# is what the lock means: the line is ordered, a flag is on from its `since`
# onward, so the last release carries every change the letters introduced and
# `7.1` is `7.1d`'s geometry under a `CC 7.1` stamp. The letters STAY, and are
# not renamed or removed: a version that has been built has to remain
# describable and buildable, and each of them is still only the flags at or
# before its own letter. The next design change opens `7.2a`.
RELEASES = ("7.0", "7.1a", "7.1b", "7.1c", "7.1d", "7.1")
CURRENT = "7.1"


@dataclass(frozen=True)
class Rev:
    """What is true of the release being built. One field per design change.

    `since` is the release the change SHIPS IN, and `spec` is where it is
    written down — both live here and nowhere else, so a field and its record
    cannot drift apart.
    """

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


# A version is a STRING and not a number (Allan, 2026-09-06). It is usually
# short and usually looks numeric — `7.0`, `7.1` — but it may be `7.1.1` or
# `7.1B` or anything else short enough to engrave, so NOTHING here parses it.
# The order of a release is its position in `RELEASES`, which is the only
# place the line's order is stated; a version that is not on the line has no
# position and no flags.
#
# One consequence, recorded because it is easy to trip over: the engraved
# stamp reader can only read a `digit . digit` word (`verify._dotted`), so a
# version of any other shape — `7.1.1`, `7.1B` — is checkable by its METADATA
# alone. That is a limit on the reader, not on the version.


def position(version):
    """Where `version` sits on the line, or None if it is not on it."""
    return RELEASES.index(version) if version in RELEASES else None


def at_least(version, since):
    """Is `version` at or after the release `since` shipped in?

    `since` is always a release on the line. `version` may be a historical one
    that predates it — `tests/test_holder_corpus.py` prices its engraving at
    `6.6` — and a version off the line is BEFORE it by construction: `of`
    admits nothing else.
    """
    here, there = position(version), position(since)
    if there is None:
        refuse(f"{since!r} is not a release; a flag's `since` must be one of "
               f"{', '.join(RELEASES)}")
    return here is not None and here >= there


def check(version):
    """The version, or a refusal naming the line.

    A typo has to fail here. Left to fall through it would build the CURRENT
    geometry under a `CC 7.15` stamp — the mixed-generation part that
    `parts.csv`'s Build column and `pusher.build`'s refusal both exist to
    prevent, and the stamp is the only thing a person holding the part can
    read.
    """
    if version not in RELEASES:
        refuse(f"unknown release {version!r}; cad/ builds one of "
               f"{', '.join(RELEASES)} (cad/revisions.py)")
    return version


# Versions that predate the line and are still asked about by name. A cached
# component or a reference STEP may carry one — `tests/test_holder_corpus.py`
# prices its engraving at `6.6` — and it correctly gets none of the line's
# flags. Naming them is what lets `of` refuse everything else: with versions
# as opaque strings there is no arithmetic that can tell a real old release
# from a typo, so the answer is a list, and a new one is admitted deliberately.
HISTORICAL = ("6.3", "6.4", "6.5", "6.6")


def of(version):
    """The `Rev` for a version: every change introduced at or before it.

    This is NOT `check`: it also takes a HISTORICAL version, which is a real
    thing to ask about — refusing `6.6` would leave the corpus unable to
    describe its own references — and gives it no flags, because every change
    here shipped after it.

    Anything else is refused. A version is an opaque string, so a typo cannot
    be told from a release by looking at it; the line and `HISTORICAL` are the
    whole of what is known, and building `7.15` as if it were current is how a
    part gets stamped with a release that does not exist. What a CLI may BUILD
    is narrower still — `check`.
    """
    if version not in RELEASES and version not in HISTORICAL:
        refuse(f"unknown version {version!r}; cad/ builds "
               f"{', '.join(RELEASES)} and knows the older "
               f"{', '.join(HISTORICAL)} by name — add it to "
               f"cad/revisions.RELEASES first")
    return Rev(**{f.name: at_least(version, f.metadata["since"])
                  for f in fields(Rev)})


def flags():
    """Every change field, with its `since` and `spec` metadata."""
    return fields(Rev)


def changes_at(version):
    """The flags this release INTRODUCES, for a report or a test."""
    return tuple(f.name for f in fields(Rev) if f.metadata["since"] == version)


def previous(version):
    """The release before this one, or None for the first."""
    i = RELEASES.index(check(version))
    return RELEASES[i - 1] if i else None
