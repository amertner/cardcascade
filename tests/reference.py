"""What the references ARE, so a test says which release it is asserting.

Every STEP in `spec/reference/` and cached mesh in `individual/` came out
of Onshape at **7.0**, while `cad/` defaults to the current release, so a test
comparing against them must PIN 7.0 or it re-baselines itself when the
default moves. `primary(...)` and `from_row(...)` are `cad.params`' own with
`Version` pinned; a test meaning another release says so at the call. Import
as a sibling — `sys.path.insert(0, str(ROOT / "tests"))`.
"""
import sys
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cad import params                                     # noqa: E402

# The generation every reference was exported at — NOT `revisions.CURRENT`.
VERSION = "7.0"


# Where `Version` sits, so a caller passing it POSITIONALLY is left alone.
_VERSION_AT = [f.name for f in fields(params.Primary)].index("Version")


def tree():
    """Where a build AT the reference release lives — `build/v7.0`, written
    by `cad.build --part all --version 7.0`. Pinning the Primary is only half
    of it: a 7.0 expectation read against a 3MF out of `build/` compares
    against the CURRENT release, a real difference from 7.1 on."""
    from cad import build as B
    return B.out_for(VERSION)


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
