#!/usr/bin/env python3
"""Shared Onshape REST core for the Card Cascade automation.

1Password credentials plus a single counted + logged HTTP layer that writes the
shared budget ledger (automation/onshape_api_log.csv). Every real call is billed
unless it is a 4xx client error. See the API budget: ~2500 calls/YEAR — be
frugal. Imported by set_variables.py (and, going forward, the exporter).
"""
import csv
import datetime
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

BASE = "https://cad.onshape.com"
OP_ITEM = "OnshapeCC"                 # 1Password item with access_key/secret_key
# ...and WHICH 1Password account holds it. `op` resolves a bare `item get`
# against its default account; this machine is signed in to three, and the
# default is not the one carrying OnshapeCC — the failure reads
# '"OnshapeCC" isn\'t an item', which looks like a missing secret rather than a
# lookup in the wrong place. Naming the account makes the command independent of
# whatever `op` last defaulted to. Override with OP_ACCOUNT for another sign-in.
OP_ACCOUNT = os.environ.get("OP_ACCOUNT", "mertner.1password.com")
ANNUAL_LIMIT = 2500
LOG = Path(__file__).with_name("onshape_api_log.csv")
LOG_COLUMNS = ["date", "time", "run_id", "reason", "method", "status",
               "consumed", "run_calls", "cumulative_total", "endpoint"]

# Adaptive polling. Each poll of a running translation is a BILLED call, so the
# aim is to wait long enough before the first poll that the export is already
# DONE — i.e. exactly one poll. We persist a learned delay per translation kind
# (part-studio exports are quick; assembly exports are bigger/slower); start at
# 10s and, whenever a call needed more than one poll, raise the learned delay to
# the observed completion time (+margin) so the NEXT call lands on one poll.
POLL_STATE = Path(__file__).with_name("state") / "poll_delay.json"
DEFAULT_POLL = 10          # first-poll wait before we've learned anything (s)
POLL_INTERVAL = 5          # wait between re-polls while still ACTIVE (s)
POLL_MARGIN = 3            # cushion added to a newly learned delay (s)

# Variable-change settle. POST /variables returns 204 as soon as the variable
# studio is written, but the change is NOT guaranteed to be visible to a
# translation requested immediately after: Onshape resolves the translation
# against the microversion it can see, and if that is still the pre-change one it
# serves a CACHED result computed for the PREVIOUS parameter set. That is a
# silently wrong export — right filename, previous cascade's geometry (this bit
# us on 2026-08-10; Compile 126 Un came back as Dominion 650 Sl, byte-identical).
# So wait after setting variables, before the batch's first translation. Sleeping
# costs 0 API calls, which is the whole point at ~2500/year; polling Onshape for
# readiness would not be free. The wait is learned/tunable in poll_delay.json.
#
# Do NOT try to detect staleness from how long the translate POST takes. Without
# a settle, a POST that returned fast meant "regenerated nothing, served a cached
# result" — which is how the original bug was spotted. With the settle in place
# the regeneration happens DURING the wait, so a healthy translate POST now
# returns in ~1.5s and a slow one is the anomaly. The signal inverted the moment
# this barrier existed. Staleness is caught by content instead (see verify.py).
SETTLE_KEY = "variable-settle"
DEFAULT_SETTLE = 20        # seconds to wait after setting variables
SETTLE_STEP = 10           # raise the learned wait by this after a stale export

CALLS = 0          # billed calls this run
CUMULATIVE = 0     # all-time total (seeded from the ledger by begin())
RUN_ID = ""


def op_creds():
    try:
        out = subprocess.check_output(
            ["op", "item", "get", OP_ITEM, "--account", OP_ACCOUNT, "--fields",
             "access_key,secret_key", "--reveal", "--format", "json"],
            text=True, stderr=subprocess.PIPE)
    except FileNotFoundError:
        sys.exit("op CLI not found; install the 1Password CLI, or set "
                 "ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY env vars.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"`op item get {OP_ITEM} --account {OP_ACCOUNT}` failed:\n"
                 f"{e.stderr.strip()}")
    data = json.loads(out)
    if isinstance(data, dict):
        data = [data]
    by = {(f.get("label") or f.get("id")): f.get("value") for f in data}
    a, s = by.get("access_key"), by.get("secret_key")
    if not (a and s):
        sys.exit(f"Could not read keys from op item {OP_ITEM!r}: {list(by)}")
    return a, s


def creds():
    a = os.environ.get("ONSHAPE_ACCESS_KEY")
    s = os.environ.get("ONSHAPE_SECRET_KEY")
    if not (a and s):
        a, s = op_creds()
    return HTTPBasicAuth(a, s)


class LazyAuth:
    """A requests auth object that resolves credentials on FIRST USE.

    A fully cached run (export.py --use-cache) makes zero API calls, so it must
    not demand a 1Password unlock — asking for keys it will never send is both a
    pointless prompt and a way to fail a run that needs no network at all.
    requests only ever calls auth(prepared_request), so proxying that is enough."""

    def __init__(self):
        self._auth = None

    def __call__(self, request):
        if self._auth is None:
            self._auth = creds()
        return self._auth(request)


def parse_url(url):
    """did/(w|v|m)id/eid from an Onshape URL."""
    m = re.search(
        r"/documents/([0-9a-f]+)/(w|v|m)/([0-9a-f]+)/e/([0-9a-f]+)", url)
    if not m:
        sys.exit(f"Could not find did/(w|v|m)id/eid in URL:\n  {url}")
    return m.groups()


def read_cumulative():
    if not LOG.exists():
        return 0
    try:
        with LOG.open(newline="") as f:
            rows = list(csv.DictReader(f))
        return int(rows[-1]["cumulative_total"]) if rows else 0
    except (ValueError, KeyError, IndexError):
        return 0


def begin():
    """Start a run: stamp RUN_ID and seed CUMULATIVE from the ledger."""
    global RUN_ID, CUMULATIVE
    RUN_ID = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    CUMULATIVE = read_cumulative()


def _log(reason, method, endpoint, status, consumed):
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(LOG_COLUMNS)
        now = datetime.datetime.now()
        w.writerow([now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                    RUN_ID, reason, method, status, int(consumed),
                    CALLS, CUMULATIVE, endpoint])


def http(auth, method, path, reason, **kw):
    """Single choke point: counts (4xx not billed), logs every attempt, and
    fails loudly with the server's message."""
    global CALLS, CUMULATIVE
    r = requests.request(method, BASE + path, auth=auth, **kw)
    consumed = not (400 <= r.status_code < 500)
    if consumed:
        CALLS += 1
        CUMULATIVE += 1
    _log(reason, method, path, r.status_code, consumed)
    if not r.ok:
        note = "" if consumed else "  (client 4xx — not billed)"
        sys.exit(f"{method} {path} -> HTTP {r.status_code}{note}\n"
                 f"{r.text[:1000]}")
    return r


def api(auth, method, path, reason, **kw):
    kw.setdefault("headers", {}).update(
        {"Accept": "application/json", "Content-Type": "application/json"})
    r = http(auth, method, path, reason, **kw)
    # Some endpoints (e.g. POST /variables) succeed with 204 No Content and an
    # empty body — return None rather than choking on json.loads("").
    if r.status_code == 204 or not r.content:
        return None
    return r.json()


def budget_line():
    return (f"API calls used this run: {CALLS}  "
            f"(year-to-date {CUMULATIVE}/{ANNUAL_LIMIT}, "
            f"{ANNUAL_LIMIT - CUMULATIVE} left)")


# ------------------------------------------------------------ adaptive polling
def _load_poll():
    try:
        return json.loads(POLL_STATE.read_text())
    except Exception:
        return {}


def poll_delay(kind, default=DEFAULT_POLL):
    return int(_load_poll().get(kind, default))


def _save_poll(kind, seconds):
    delays = _load_poll()
    delays[kind] = int(seconds)
    POLL_STATE.parent.mkdir(exist_ok=True)
    POLL_STATE.write_text(json.dumps(delays, indent=2))


def settle(label=""):
    """Wait for a just-POSTed variable change to become visible to translations.
    0 API calls — see the SETTLE_KEY note above for why this barrier exists."""
    s = poll_delay(SETTLE_KEY, DEFAULT_SETTLE)
    print(f"    … settling {s}s for the parameter change to propagate{label}")
    time.sleep(s)
    return s


def bump_settle():
    """An export came back stale despite the settle — wait longer next time."""
    new = poll_delay(SETTLE_KEY, DEFAULT_SETTLE) + SETTLE_STEP
    _save_poll(SETTLE_KEY, new)
    return new


def _learn_poll(kind, elapsed):
    """Raise the learned delay for `kind` toward the observed completion time so
    the next call needs a single poll. Increase-only: never risk an extra poll."""
    new = int(math.ceil(elapsed)) + POLL_MARGIN
    if new > _load_poll().get(kind, 0):
        _save_poll(kind, new)


def translate(auth, kind, did, path, body, reason=""):
    """Run one 3MF translation (part studio or assembly) and return
    (bytes, documentMicroversion). `kind` selects the learned poll delay; `path`
    is the .../translations endpoint; `did` is the document id for the download.

    Waits the learned delay before the first (billed) poll so one poll is the
    norm, and re-learns upward if it wasn't."""
    rp = f"{reason}-" if reason else ""
    tid = api(auth, "POST", path, f"{rp}translate", json=body)["id"]
    t0 = time.monotonic()
    time.sleep(poll_delay(kind))
    st, polls = {}, 0
    while polls < 12:
        st = api(auth, "GET", f"/api/translations/{tid}", f"{rp}poll")
        polls += 1
        if st.get("requestState") != "ACTIVE":
            break
        time.sleep(POLL_INTERVAL)
    if st.get("requestState") != "DONE":
        sys.exit(f"{kind} translation {st.get('requestState')}: "
                 f"{st.get('failureReason')}")
    if polls > 1:                       # took longer than we waited — wait more next time
        _learn_poll(kind, time.monotonic() - t0)
    fid = st["resultExternalDataIds"][0]
    data = http(auth, "GET", f"/api/documents/d/{did}/externaldata/{fid}",
                f"{rp}download").content
    return data, st.get("documentMicroversion", "")
