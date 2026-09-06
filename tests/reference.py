"""What the references ARE, so a test says which release it is asserting.

Every hand-exported STEP in `spec/reference/` and every cached mesh in
`individual/` came out of Onshape at **7.0**. `cad/` can build any release in
`cad/revisions.RELEASES` and DEFAULTS to the current one, so a test that
compares against those references has to pin 7.0 — otherwise it re-baselines
itself silently the next time the default moves, which is the one failure a
regression corpus must not have.

That is the whole of this module: `primary(...)` and `from_row(...)` are
`cad.params`' own, with `Version` pinned to `VERSION`. A test that means a
different release says so at the call (`tests/test_holder_corpus.py` has priced
its engraving at an explicit `Version="6.6"` since long before the default
moved, and `tests/test_revisions.py` builds every release on purpose).

Import it as a sibling — `sys.path.insert(0, str(ROOT / "tests"))`, the way
`probe` is imported.
"""
import sys
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import params                                     # noqa: E402

# The generation every reference was exported at. NOT `revisions.CURRENT`, and
# deliberately a literal: when the current release moves, these files do not.
VERSION = "7.0"


# Where `Version` sits in the Primary, so a caller that passes it POSITIONALLY
# — `tests/test_pusher.py` names its release in the tuple — is left alone
# rather than handed two values for the same argument.
_VERSION_AT = [f.name for f in fields(params.Primary)].index("Version")


def primary(*args, **kw):
    """`params.Primary`, at the reference release unless the caller names one."""
    if len(args) > _VERSION_AT or "Version" in kw:
        return params.Primary(*args, **kw)
    return params.Primary(*args, **{**kw, "Version": VERSION})


def from_row(row, sleeved, version=VERSION):
    """`params.from_row`, at the reference release."""
    return params.from_row(row, sleeved, version)


def load_rows(path):
    return params.load_rows(path)
