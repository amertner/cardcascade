"""Per-game provenance for exported components.

Records which component file was generated when, from which Onshape element, with
what configuration, and at what per-studio version — so the exporter can skip
components that already exist AT THE CURRENT VERSION rather than just "exist".
State lives in automation/state/<Game>.csv (committed, like the API ledger); it
makes no API calls.

A component is "current" when a row exists for its file whose `version` equals
the current per-studio version (onshape_config.VERSIONS[type]). Bumping a
studio's version makes its components stale; re-exporting refreshes the row.
"""
import csv
from pathlib import Path

STATE_DIR = Path(__file__).with_name("state")
COLUMNS = ["file", "type", "key", "element", "configuration",
           "version", "microversion", "sha", "exported_at"]


def _path(game):
    return STATE_DIR / f"{game}.csv"


def load(game):
    """{file: row-dict} from the game's provenance CSV (empty if none yet)."""
    p = _path(game)
    if not p.exists():
        return {}
    with p.open(newline="") as f:
        return {r["file"]: r for r in csv.DictReader(f)}


def save(game, rows):
    STATE_DIR.mkdir(exist_ok=True)
    with _path(game).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: (r["type"], r["file"])):
            w.writerow({c: r.get(c, "") for c in COLUMNS})


def all_rows():
    """(game, row) for every recorded component in every game. Used by the
    identity guard, which must see across games: a stale export hands you the
    PREVIOUS run's mesh, and the previous run is usually a different game."""
    for p in sorted(STATE_DIR.glob("*.csv")):
        with p.open(newline="") as f:
            for r in csv.DictReader(f):
                yield p.stem, r


def is_current(prov, file, version):
    """True iff `file` is recorded and its version matches `version`."""
    r = prov.get(file)
    return bool(r) and r.get("version") == str(version)


def make_row(file, type, key, element, configuration, version,
             microversion, when, sha=""):
    return {"file": file, "type": type,
            "key": "|".join(str(x) for x in key) if isinstance(key, tuple)
                   else str(key),
            "element": element or "", "configuration": configuration or "",
            "version": str(version), "microversion": microversion or "",
            "sha": sha or "", "exported_at": when}


def record(game, row):
    """Upsert one provenance row (keyed by file) and persist."""
    prov = load(game)
    prov[row["file"]] = row
    save(game, prov)
