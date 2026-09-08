# Revisions — the release line, and what changed at each one

`cad/revisions.py` is the code; this is the record. It answers one question:
**what does a cascade built at 7.0 have that one built at 7.1 does not, and
why?**

## A REVISION CHANGE is not a DIVERGENCE

The distinction is the whole point of the mechanism, and getting it wrong is
what the mechanism prevents.

| | DIVERGENCE | REVISION CHANGE |
|---|---|---|
| what it is | `cad/` against **Onshape**, at the same version | `cad/` 7.0 against `cad/` 7.1 |
| how long | permanent | from its release on |
| lives in | the part, recorded in `spec/` | `cad/revisions.py`, recorded here |
| asserted by | the part's own test, both ends (`cad/README.md`, decision 6) | `tests/test_revisions.py`, both releases |

The four standing DIVERGENCES are the Box's hanging holes stopping at the slot
band, its `CC` where the sketch says `Rev`, the XS box's single fastener, and
the Lid's fitted logo. They apply at 7.0 and 7.1 alike and they are NOT in the
revisions table — putting them there would make the table read as a mixed bag
of switches instead of a release history. That was asked and settled (Allan,
2026-09-06).

## A version is a STRING

Short, usually numeric-looking — `7.0`, `7.1` — but it may be `7.1a`, `7.1.1`
or anything else that fits on a part, so nothing parses it (Allan,
2026-09-06). The iteration letter below is the first version on the line that
is not a number at all, and nothing had to change to admit it: it is a member
of `RELEASES` like any other string. A release's ORDER is its position in `RELEASES`, which is the only
place the line's order is stated, and `HISTORICAL` names the older versions
still asked about by name (`6.6`, which `tests/test_holder_corpus.py` prices
its engraving at). Anything else is refused: with opaque strings there is no
arithmetic that tells a real old release from a typo, so the answer is a list.

One consequence to know before choosing a version: the engraved-stamp reader
can only read a `digit . digit` word (`verify._dotted`), so a version of any
other shape — `7.1.1`, `7.1B` — is checkable by its METADATA alone. That is a
limit on the reader, not on the version, and it is why the metadata witness
exists at all.

## The two rules that keep it generalisable

**A part asks a NAMED question and never compares versions.** `d.rev.<flag>`,
never `d.Version >= "7.1"`. The flag name is what this file records and what a
reader greps for; a version comparison is invisible to both. Adding the next
change is one field in `revisions.Rev`, one `if` in the part, and one case in
`tests/test_revisions.py`.

**The line is monotonic.** A change introduced at 7.1 is in every release after
it — that is what a release line means. Undoing one later is a NEW flag with
its own `since`, not a hole in the table.

## How a release reaches a part

`Primary.Version` -> `derive` -> `d.rev`, a frozen record of one boolean per
change, riding on the `Derived`. That keeps the rule the rebuild already has:
every feature below `derive` takes the `Derived` alone. `rev` is deliberately
NOT one of the studio's variables — Onshape has no counterpart for it — so it
is a slot on `Derived` beside `_v` rather than a key inside it.

## The releases

### 7.0 — the Onshape generation

What every reference STEP in `spec/reference/` and every cached mesh in
`individual/` was exported at, and what every shipped cascade under
`cascades/` is. A 7.0 build must reproduce them exactly, forever; that is what
the corpus tests assert, and `tests/reference.py` is why they keep asserting it
when the default moves.

### 7.1 — the cad-built release, being iterated as `7.1a`

Currently on the line as **`7.1a`** and not as `7.1`: the release is unfinished,
and the letter is what a part built today is stamped and titled with (see "An
unreleased release is iterated by LETTER"). Everything below is what `7.1a`
is; the next change opens `7.1b`.

The same 7.0 **lock** (`lock.SAME_LOCK`, and `pusher.build` refuses a release
that has not declared one) under a `CC 7.1` stamp, so a cad-built cascade can
be told from an Onshape-exported one on the shelf — and, since the version goes
into the project name and title, in the file too.

Its geometry changes, in the order they were made:

* **`lid_socket_per_pusher`** — the Lid cuts one pusher socket per pusher the
  cascade ships (`box.pusher_slot_count`) instead of Onshape's plain size rule,
  so the four Innovation M lids lose their unused MIDDLE socket. Four lids and
  no others; the outer pair does not move, so no pusher and no margin changes.
  `spec/LID.md`, "The middle socket is gone".
* **`two_pushers`** — every cascade takes TWO pushers, whatever its size, where
  Onshape gave 3 to every M and L box that is not Innovation. It restates 24 of
  the 50 boxes — one fewer rear storage slot, divider and pair of rim cutouts —
  moves their thumb cutout, and ships one Pusher fewer in each of their
  projects. The Lid follows through the flag above, so nothing has three
  sockets at 7.1. `spec/BOX.md`, "Two pusher slots, at every size".
* **`thick_floor`** — the Box's floor is `2.000` where every wall stays
  `WallThickness`'s `1.600` (Allan). It is the two SIDE FLOORS that matter: the
  card area is cut clean through (`bottom_slot`), so what the floor actually is
  is the pair of strips the holders rest on, plus the front pocket's and the
  rear storage's. It grows **upward**, into the cavity, so nothing about the
  box's outside changes — same bounding box, same rim, same rim cutouts, same
  `Top of back`, same hanging holes, all of them measured from the bed — and
  the `0.400` comes out of the interior, which has `12.900` of headroom over
  the tallest holder on all 50 rows. Everything standing on the floor rises
  with it by exactly `0.400`: every holder and the token holder. The Lid keeps
  its `1.600` floor. `spec/BOX.md`, "The floor is 2.000, and it grows UPWARD".

**The flags are separable and the tests keep them so.** Two of the three reach
the Lid, so comparing 7.0 with 7.1 shows 28 lids changing and says nothing about
which flag did what; `tests/test_revisions.py` turns one flag on at a time
against a 7.0 Derived to isolate them. `thick_floor` needs the same treatment
for a different reason: `two_pushers` restates 24 boxes wholesale, so only a
7.0 Derived carrying the floor flag ALONE — same three slots, same `CC 7.0` ink
— can show that the floor moved and nothing else did. That technique is the
reason a `Rev` is a record of independent booleans rather than a version number
to compare against.

## What a release moves besides its flags

**The stamp.** Every part engraves `CC <version>`, so a 7.1 part differs from
a 7.0 one in ink even where no flag touched it — `1.44 mm3` on the Innovation M
lid, which is the `0` against the `1`. `tests/test_revisions.py` separates the
two deliberately: it prices the FLAG by building a 7.0 `Derived` carrying 7.1's
`Rev` (same ink, one socket fewer) and the STAMP as what is left. A tolerance
wide enough to swallow both would hide a second change.

**Two witnesses to the release, because one is not enough.** Reading the
engraved version back is not OCR: it is a signature over the COUNTERS of the
two digits either side of the period (`verify.STAMP_SIGNATURES`), and at 7.1
that stops being sufficient. `7` has no counter and neither has `1`, so 7.1
reads `("none", "none")` — and so would 7.2, 7.3, 7.5 and 7.7. The counters
cannot separate them and no better reader will: those glyphs differ in their
strokes, not in their holes.

So every component `cad.build` writes now STATES its release in the file as
well, as `CardCascade:Version` metadata under a declared namespace, beside a
human `Title` and `Description` Studio will show. The two witnesses answer
different questions and neither replaces the other:

| | the ENGRAVING | the METADATA |
|---|---|---|
| who can read it | anyone holding the printed part | anything reading the file |
| how exact | ambiguous from 7.1 on | exact |
| what it guards | a 7.x pusher going into a 6.6 lid | which release wrote this file |

`verify.check_stamp` holds both to the release AND to each other: a positive
mismatch from either is fatal, and so is the two disagreeing, which means the
file is not self-consistent whatever the cascade wanted. Only when NEITHER can
be read is it a warning. An Onshape export carries no metadata and is checked
by its glyph exactly as before.

`verify.py --stamps --tree build` is the release-time check: every component in
a cad tree must state one release, and the Box, Lid and Pusher must be engraved
with it too.

**The tree.** Filenames carry no version — a NAME is an identity
(`components.tracked_name`) — so two releases written to one tree overwrite
each other part for part. `cad.build --out` therefore follows `--version` by
default: `build/` for the current release, `build/v<version>/` for any other.
`cad.cascade --components` follows the same rule, and `cad.promote` reads the
LOCK GENERATION's tree, because what it stages goes into a shipped cascade
whose other parts are Onshape 7.0 exports.

## Defaults, and why the tests pin

`revisions.CURRENT` is **7.1**: a plain `cad.build` or `cad.cascade` builds the
current release (Allan, 2026-09-06). `cad.compare` and `tests/test_parallel.py`
are the exception that proves the rule: they pin **7.0**, because what they
regress against is the shipped tree, which the Onshape pipeline built at 7.0 —
and from 7.1 a twin is MEANT to print differently, two pushers against three. That makes the default a moving target by
design, so **every test that compares against a reference pins the release it
means** — `tests/reference.py`, `VERSION = "7.0"`, a literal and not
`revisions.CURRENT`. `tests/test_holder_corpus.py` had already been pricing its
engraving at an explicit `Version="6.6"` long before the default moved, which
is the same idea; this generalises it.

A test that does not pin is a test that re-baselines itself the next time the
default moves — the one failure a regression corpus must not have.

## An unreleased release is iterated by LETTER

`CURRENT` is not a finished thing. The way this repo is worked (Allan,
2026-09-06) is: **sit at a version for a while, accumulate changes in it, then
lock it and release it.** The letter is how those accumulating states are told
apart (Allan, 2026-09-08): **`7.1a`, `7.1b`, `7.1c`, ... and then plain `7.1`
at the lock.**

**The problem it solves is physical.** While 7.1 is being worked on its
geometry moves — three times already — and every part printed along the way
says `CC 7.1`. A shelf of them cannot say which is which, and the stamp is the
only thing a person holding the plastic can read. A letter makes each state
nameable on the part itself.

**A letter is a release like any other**, and that is the whole design: a full
member of `RELEASES`, with its own position on the line, its own
`lock.SAME_LOCK` entry and its own row in `verify.STAMP_SIGNATURES`. It is what
makes the letter MEAN something — a change lands as a flag whose `since` is the
NEW letter, so a build at `7.1a` keeps producing what `7.1a` always produced,
and the part stamped with it stays reproducible.

The alternative was considered and rejected: a letter as a mere build marker,
with the flags still keyed on `7.1`. It reads simpler and it is wrong — a
change would move the geometry under every earlier letter, so two different
shapes would wear the same stamp, which is the one thing the stamp exists to
prevent.

### Bumping, and locking

To bump: add the letter to `RELEASES` and to `lock.SAME_LOCK`, move `CURRENT`
onto it, give the new change's flag `since: "<the new letter>"`, and leave
every earlier flag alone — the line is monotonic, so they carry forward.
Nothing is rebuilt in place any more; the earlier letter is FROZEN, which is
what a version stamped on plastic has to be.

At the lock, plain `7.1` joins the END of the line and becomes `CURRENT`. The
letters STAY on it. Parts printed at `7.1b` exist, and the rule this repo
keeps everywhere is that a version you can hold must remain describable and
buildable; `7.1` sitting after them all carries every flag they introduced.

**`7.1` itself is not on the line until then**, deliberately: while the release
is unfinished, nothing can build it, stamp it or title a project with it, so
there is no way to put an unfinished `CC 7.1` on a part by accident.

**Prose in `spec/` says "from 7.1" and means the release**, not the letter —
the geometry sections were written about the release and stay true of every
letter in it. The flags' `since` is the exact answer and `cad/revisions.py` is
where to read it.

The reference corpus is the model for what a locked release looks like: 7.0 is
locked, `tests/reference.py` pins it, and a 7.0 build must reproduce
`individual/` forever.

## Adding the next release — or the next LETTER

The steps are the same for both, because a letter IS a release.

1. Add it to `RELEASES`, set `CURRENT` if it is the new default, and add it to
   `lock.SAME_LOCK` if it keeps the 7.0 lock. Leaving it out of `SAME_LOCK` is
   a loud failure (`pusher.build` refuses it) rather than a quiet wrong stamp.
2. For each change: a field in `revisions.Rev` with its `since` and `spec`, and
   an `if d.rev.<flag>` in the part.
3. A case in `tests/test_revisions.py`, asserting the old release still has the
   old behaviour. Its coverage check names any flag with no case.
4. A section here.
5. A stamp signature in `verify.STAMP_SIGNATURES`, and then
   `verify.py --stamps --tree build` before publishing. Adding the signature
   may not be enough on its own: see below.
