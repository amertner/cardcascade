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

**The line is monotonic.** A change introduced at 7.1 is in every release
after it; that is what a release line means. Undoing one is a NEW flag with
its own `since`, not a hole in this table.
"""
from dataclasses import dataclass, field, fields

from .refuse import refuse

# Every release `cad/` can build, oldest first. `CURRENT` is what a build
# defaults to; an older one is still buildable and is what every reference
# STEP and cached mesh in `individual/` is compared against.
RELEASES = ("7.0", "7.1")
CURRENT = "7.1"


@dataclass(frozen=True)
class Rev:
    """What is true of the release being built. One field per design change.

    `since` is the release the change SHIPS IN, and `spec` is where it is
    written down — both live here and nowhere else, so a field and its record
    cannot drift apart.
    """

    two_pushers: bool = field(metadata={
        "since": "7.1",
        "spec": "spec/BOX.md, 'Two pusher slots, at every size'",
        "what": "every cascade takes TWO pushers, whatever its size: "
                "`#calPusherSlots` is 2 rather than 2-for-Innovation-and-S-"
                "else-3, so 24 boxes lose a rear storage slot, its divider "
                "and its rim cutouts, their thumb cutout centres, and their "
                "projects ship one Pusher fewer. The Lid follows through "
                "`lid_socket_per_pusher`",
    })

    lid_socket_per_pusher: bool = field(metadata={
        "since": "7.1",
        "spec": "spec/LID.md, 'The middle socket is gone'",
        "what": "the Lid cuts one pusher socket per pusher the cascade ships "
                "instead of Onshape's plain size rule, so the four Innovation "
                "M lids lose their unused MIDDLE socket",
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
