#!/usr/bin/env python3
"""Smallest end-to-end test of the Onshape REST API for Card Cascade:
discover a Part Studio's parts (and any configuration inputs), optionally
set one, and export to OBJ. Proves the export pipeline before we build the
real sweep.

!!! HARD BUDGET: the Onshape Free plan allows only ~2500 API calls PER YEAR.
    That is ~12 full cascade exports for the WHOLE year. This script is built
    to be frugal: it caches discovery, counts every call, logs each one to
    onshape_api_log.csv, and prints the running yearly total. ALWAYS --dry-run
    first, read the estimated call count, then run for real.

Credentials: read from 1Password by default via
    op item get OnshapeCC --fields access_key,secret_key --reveal
Override for offline/other use with ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY.

Usage:
    # 1. Discover parts + config inputs ONCE (2 calls). Cached thereafter.
    python3 onshape_test.py "<url>" --list

    # 2. Cost a command without spending anything (0 API calls):
    python3 onshape_test.py "<url>" --dry-run

    # 3. Export the WHOLE studio in one call (e.g. the toppers studio):
    python3 onshape_test.py "<url>" -o toppers.zip

    # 4. Export one part with a configuration value set:
    python3 onshape_test.py "<url>" --set size=40mm --part "Box" -o box40.zip

Frugality notes:
  * Discovery (GET /parts, /configuration) is cached to .onshape_cache.json;
    export mode never re-fetches it. --refresh forces a re-fetch (2 calls).
  * Encoded configuration strings are cached per --set combination.
  * Omit --part to export the whole studio in ONE call (parts become named
    OBJ groups) instead of one call per part.
  * Polling is bounded: one wait, then capped polls. Each poll is a call.
  * Default format is 3MF: it keeps parts as SEPARATE objects (OBJ paints
    colour on as face materials and collapses parts into one mesh), and it
    is exactly what make_cascade.py's load_export() already parses.
"""
import argparse
import csv
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

BASE = "https://cad.onshape.com"
OP_ITEM = "OnshapeCC"          # 1Password item holding access_key / secret_key
ANNUAL_LIMIT = 2500            # Onshape Free hard cap, calls per year
CACHE = Path(__file__).with_name(".onshape_cache.json")
LOG = Path(__file__).with_name("onshape_api_log.csv")
# endpoint last: it is the long field, so keep it out of the way when browsing.
# consumed=0 for 4xx client errors — Onshape does not bill those.
LOG_COLUMNS = ["date", "time", "run_id", "reason", "method", "status",
               "consumed", "run_calls", "cumulative_total", "endpoint"]

CALLS = 0          # real Onshape HTTP calls this run
CUMULATIVE = 0     # all-time total (seeded from the log at startup)
RUN_ID = ""


# ---------------------------------------------------------------- credentials
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
        sys.exit(f"Could not read access_key/secret_key from op item "
                 f"{OP_ITEM!r}; fields seen: {list(by)}")
    return a, s


def creds():
    a = os.environ.get("ONSHAPE_ACCESS_KEY")
    s = os.environ.get("ONSHAPE_SECRET_KEY")
    if not (a and s):
        a, s = op_creds()
    return HTTPBasicAuth(a, s)


# ------------------------------------------------------------------- API log
def read_cumulative():
    if not LOG.exists():
        return 0
    try:
        with LOG.open(newline="") as f:
            rows = list(csv.DictReader(f))
        return int(rows[-1]["cumulative_total"]) if rows else 0
    except (ValueError, KeyError, IndexError):
        return 0


def log_call(reason, method, endpoint, status, consumed):
    """Append one row. CALLS/CUMULATIVE are already updated by http()."""
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(LOG_COLUMNS)
        now = datetime.datetime.now()
        w.writerow([now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                    RUN_ID, reason, method, status, int(consumed),
                    CALLS, CUMULATIVE, endpoint])


# ----------------------------------------------------------------- HTTP layer
def http(auth, method, path, reason, **kw):
    """Single choke point: counts (4xx client errors are NOT billed, so they
    don't count), logs every attempt, and fails loudly with the server's
    own message."""
    global CALLS, CUMULATIVE
    r = requests.request(method, BASE + path, auth=auth, **kw)
    consumed = not (400 <= r.status_code < 500)
    if consumed:
        CALLS += 1
        CUMULATIVE += 1
    log_call(reason, method, path, r.status_code, consumed)
    if not r.ok:
        note = "" if consumed else "  (client 4xx — not billed)"
        sys.exit(f"{method} {path} -> HTTP {r.status_code}{note}\n"
                 f"{r.text[:1000]}")
    return r


def api(auth, method, path, reason, **kw):
    kw.setdefault("headers", {}).update(
        {"Accept": "application/json", "Content-Type": "application/json"})
    return http(auth, method, path, reason, **kw).json()


# -------------------------------------------------------------------- helpers
def parse_url(url):
    """did/(w|v|m)id/eid from an Onshape URL."""
    m = re.search(
        r"/documents/([0-9a-f]+)/(w|v|m)/([0-9a-f]+)/e/([0-9a-f]+)", url)
    if not m:
        sys.exit(f"Could not find did/(w|v|m)id/eid in URL:\n  {url}")
    return m.groups()


def field(obj, *names):
    """Read a field the API may or may not wrap in {'message': ...}."""
    src = obj.get("message", obj)
    for n in names:
        if n in src:
            return src[n]
    return None


def load_cache():
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def save_cache(c):
    CACHE.write_text(json.dumps(c, indent=2))


def fetch_parts(auth, stem, cache):
    """GET /parts (1 call), cache it. Only needed to map a --part NAME->id."""
    parts = api(auth, "GET", f"/api/parts{stem}", "discovery:parts")
    cache.setdefault(stem, {})["parts"] = parts
    save_cache(cache)
    return parts


def fetch_config(auth, stem, cache):
    """GET /configuration (1 call), cache it. Only needed for --list."""
    cfg = api(auth, "GET", f"/api/elements{stem}/configuration",
              "discovery:configuration")
    cache.setdefault(stem, {})["configuration"] = cfg
    save_cache(cache)
    return cfg


def resolve_part(name, parts):
    if not parts:
        return None
    m = [p for p in parts if name in (p.get("partId"), p.get("name"))]
    return m or None


def budget_line():
    return (f"API calls used this run: {CALLS}  "
            f"(year-to-date {CUMULATIVE}/{ANNUAL_LIMIT}, "
            f"{ANNUAL_LIMIT - CUMULATIVE} left)")


# ----------------------------------------------------------------------- main
def main():
    global RUN_ID, CUMULATIVE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("--list", action="store_true",
                    help="fetch + cache config inputs and parts, then exit")
    ap.add_argument("--refresh", action="store_true",
                    help="force re-fetch of discovery even if cached (2 calls)")
    ap.add_argument("--set", action="append", default=[], metavar="PARAM=VALUE",
                    help="configuration input to set (repeatable)")
    ap.add_argument("--part",
                    help="part id or exact name; omit to export whole studio")
    ap.add_argument("--format", default="3MF",
                    help="formatName (default 3MF — keeps parts as separate "
                         "objects; feeds make_cascade.py directly)")
    ap.add_argument("--resolution", default="medium",
                    choices=["coarse", "medium", "fine"],
                    help="mesh tessellation for 3MF/OBJ/STL (default medium)")
    ap.add_argument("--units", default="millimeter",
                    help="mesh export units (default millimeter)")
    ap.add_argument("--opt", action="append", default=[], metavar="KEY=VALUE",
                    help="extra translation-body field, repeatable "
                         "(e.g. the 'export unique parts as individual files' "
                         "flag once you know its name; true/false/int coerced)")
    ap.add_argument("-o", "--out", default="export.3mf")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and estimated call count; 0 API calls")
    ap.add_argument("--poll-wait", type=float, default=8.0,
                    help="seconds to wait before first poll (default 8)")
    ap.add_argument("--poll-interval", type=float, default=5.0)
    ap.add_argument("--poll-max", type=int, default=6,
                    help="max poll calls before giving up (default 6)")
    args = ap.parse_args()

    did, wtype, wid, eid = parse_url(args.url)
    stem = f"/d/{did}/{wtype}/{wid}/e/{eid}"
    cache = load_cache()
    set_key = ";".join(sorted(args.set))
    encoded_cached = cache.get(stem, {}).get("encodings", {}).get(set_key)

    # ---------- dry run: no credentials, no calls, no logging ----------
    if args.dry_run:
        st = cache.get(stem, {})
        expected = worst = 0
        print("DRY RUN — planned Onshape API calls:")
        if args.set and encoded_cached is None:
            print("  + 1  POST configurationencodings")
            expected += 1
            worst += 1
        elif args.set:
            print("  · 0  configuration encoding (cached)")
        need_parts = (args.refresh if args.part else False) or (
            bool(args.part) and resolve_part(args.part, st.get("parts")) is None)
        if need_parts:
            print("  + 1  discovery (GET /parts, to resolve --part name)")
            expected += 1
            worst += 1
        elif args.part:
            print("  · 0  --part resolved from cache")
        print("  + 1  POST translations")
        print(f"  + 1  GET translation status (expected; up to {args.poll_max} "
              "if the server is slow)")
        print("  + 1  GET externaldata (download)")
        expected += 3
        worst += 2 + args.poll_max
        ytd = read_cumulative()
        print(f"\nExpected: {expected} calls   (worst case {worst}). "
              f"Year-to-date {ytd}/{ANNUAL_LIMIT} ({ANNUAL_LIMIT - ytd} left).")
        print("Run the same command without --dry-run to execute.")
        return

    RUN_ID = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    CUMULATIVE = read_cumulative()
    auth = creds()

    if args.list:
        st = cache.get(stem, {})
        parts = None if args.refresh else st.get("parts")
        cfg = None if args.refresh else st.get("configuration")
        if parts is None:
            parts = fetch_parts(auth, stem, cache)
        if cfg is None:
            cfg = fetch_config(auth, stem, cache)
        print("Configuration inputs:")
        cparams = field(cfg, "configurationParameters") or []
        if not cparams:
            print("  (none — this studio needs no --set; export it whole)")
        for p in cparams:
            opts = field(p, "options") or []
            names = [field(o, "option") for o in opts]
            detail = f"  options={names}" if names else "  (value input)"
            print(f"  {field(p, 'parameterId')}{detail}")
        print("\nParts:")
        for p in parts:
            print(f"  {p.get('name')!r}  partId={p.get('partId')}")
        print("\n" + budget_line())
        return

    # ---------- encode configuration (cached per --set combo) ----------
    configuration = ""
    if args.set:
        if encoded_cached is not None:
            configuration = encoded_cached
            print(f"encoded configuration (cached): {configuration!r}")
        else:
            params = []
            for spec in args.set:
                k, _, v = spec.partition("=")
                if not _:
                    sys.exit(f"--set needs PARAM=VALUE, got {spec!r}")
                params.append({"parameterId": k, "parameterValue": v})
            enc = api(auth, "POST",
                      f"/api/elements{stem}/configurationencodings", "encode",
                      json={"parameters": params})
            configuration = enc.get("encodedId") or enc.get("queryParam", "")
            cache.setdefault(stem, {}).setdefault(
                "encodings", {})[set_key] = configuration
            save_cache(cache)
            print(f"encoded configuration: {configuration!r}")

    # ---------- resolve --part name -> partId (cache first, fetch on miss) ----
    part_ids = ""
    if args.part:
        parts = cache.get(stem, {}).get("parts")
        match = None if args.refresh else resolve_part(args.part, parts)
        if match is None:                       # cache miss -> 1 discovery call
            parts = fetch_parts(auth, stem, cache)
            match = resolve_part(args.part, parts)
        if match is None:
            sys.exit(f"no part matching {args.part!r}; parts are "
                     f"{[p.get('name') for p in parts]}")
        part_ids = ",".join(p["partId"] for p in match)
        print(f"exporting part(s): {part_ids}")

    # ---------- translate ----------
    body = {"formatName": args.format, "storeInDocument": False,
            "notifyUser": False}
    if args.format.upper() in ("3MF", "OBJ", "STL"):
        # Mesh formats must say how finely to tessellate, else Onshape
        # returns "Invalid resolution parameters were specified." The rest
        # mirrors the working UI 3MF export request (minus session cruft):
        # grouping keeps parts as separate objects, yAxisIsUp=false keeps
        # Onshape's Z-up frame (make_cascade lays out in Z-up mm), and
        # excludeHiddenEntities skips suppressed/hidden parts.
        body["resolution"] = args.resolution
        body["units"] = args.units
        body["grouping"] = False
        body["yAxisIsUp"] = False
        body["flattenAssemblies"] = False
        body["excludeHiddenEntities"] = True
        body["includeExportIds"] = False
    if configuration:
        body["configuration"] = configuration
    if part_ids:
        body["partIds"] = part_ids
    for spec in args.opt:                 # arbitrary extra body fields
        k, _, v = spec.partition("=")
        if not _:
            sys.exit(f"--opt needs KEY=VALUE, got {spec!r}")
        if v.lower() in ("true", "false"):
            v = v.lower() == "true"
        elif re.fullmatch(r"-?\d+", v):
            v = int(v)
        body[k] = v

    job = api(auth, "POST", f"/api/partstudios{stem}/translations",
              "translate", json=body)
    tid = job["id"]
    print(f"translation {tid} started; waiting {args.poll_wait:g}s before poll")
    time.sleep(args.poll_wait)
    state, st, i = None, {}, 0
    for i in range(args.poll_max):
        st = api(auth, "GET", f"/api/translations/{tid}", "poll")
        state = st["requestState"]
        if state != "ACTIVE":
            break
        time.sleep(args.poll_interval)
    if state != "DONE":
        sys.exit(f"translation {state}: {st.get('failureReason')} "
                 f"(polled {i + 1}x)\n{budget_line()}")

    # ---------- download ----------
    fid = st["resultExternalDataIds"][0]
    r = http(auth, "GET", f"/api/documents/d/{did}/externaldata/{fid}",
             "download")
    Path(args.out).write_bytes(r.content)
    print(f"wrote {args.out} ({len(r.content)} bytes)")
    print(budget_line())


if __name__ == "__main__":
    main()
