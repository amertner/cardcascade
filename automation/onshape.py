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
import os
import re
import subprocess
import sys
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

BASE = "https://cad.onshape.com"
OP_ITEM = "OnshapeCC"                 # 1Password item with access_key/secret_key
ANNUAL_LIMIT = 2500
LOG = Path(__file__).with_name("onshape_api_log.csv")
LOG_COLUMNS = ["date", "time", "run_id", "reason", "method", "status",
               "consumed", "run_calls", "cumulative_total", "endpoint"]

CALLS = 0          # billed calls this run
CUMULATIVE = 0     # all-time total (seeded from the ledger by begin())
RUN_ID = ""


def op_creds():
    try:
        out = subprocess.check_output(
            ["op", "item", "get", OP_ITEM, "--fields",
             "access_key,secret_key", "--reveal", "--format", "json"],
            text=True, stderr=subprocess.PIPE)
    except FileNotFoundError:
        sys.exit("op CLI not found; install the 1Password CLI, or set "
                 "ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY env vars.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"`op item get {OP_ITEM}` failed:\n{e.stderr.strip()}")
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
