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

    lid_socket_per_pusher: bool = field(metadata={
        "since": "7.1",
        "spec": "spec/LID.md, 'The middle socket is gone'",
        "what": "the Lid cuts one pusher socket per pusher the cascade ships "
                "instead of Onshape's plain size rule, so the four Innovation "
                "M lids lose their unused MIDDLE socket",
    })


def key(version):
    """`\"7.10\"` sorts after `\"7.9\"`: compare numbers, not strings."""
    try:
        return tuple(int(x) for x in str(version).split("."))
    except ValueError:
        refuse(f"malformed version {version!r}; expected digits and dots")


def at_least(version, since):
    return key(version) >= key(since)


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


def of(version):
    """The `Rev` for a version: every change introduced at or before it.

    This is NOT `check` — it takes any version on the line's own scale, because
    a HISTORICAL one is a real thing to ask about. `tests/test_holder_corpus.py`
    prices the cached engraving at `Version="6.6"`, which predates every change
    here and correctly gets none of them; refusing it would make the corpus
    unable to describe its own references.

    A version NEWER than the newest release is refused, though, and the
    asymmetry is deliberate: history is a fact, but the future is a typo, and
    silently handing `7.15` every flag is how a part gets built to a release
    that does not exist. What a CLI may BUILD is narrower still — `check`.
    """
    if key(version) > key(RELEASES[-1]):
        refuse(f"version {version!r} is after the newest release "
               f"{RELEASES[-1]!r}; add it to cad/revisions.RELEASES first")
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
