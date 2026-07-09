#!/usr/bin/env python3
"""Export Card Cascade poster frames from Figma as correctly-named PNGs.

One-time Figma setup
--------------------
1. On the poster page, keep one frame per configuration (duplicate the
   Card component instance and pin each duplicate's variable modes:
   Box Size + Sleeves). All duplicates stay linked to the master
   component, so design edits propagate.
2. Name each frame exactly what its file should be called,
   e.g. "CC 202S" -> CC 202S.png
3. Create a personal access token: Figma > Settings > Security >
   Personal access tokens (scope: File content, read-only).

Usage
-----
    export FIGMA_TOKEN=figd_...
    python3 figma_export.py --file <FILE_KEY> [--page "Product Card"]
                            [--prefix "CC "] [--scale 1] [--out cascades]
                            [--list]

FILE_KEY is the id in the file's URL: figma.com/design/<FILE_KEY>/...

Frames are found on the given page, including inside sections. --prefix
limits export to frames whose name starts with the prefix (useful to
skip scratch frames). --list shows what would be exported and exits.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.figma.com/v1"


def api_get(path, token, tries=5):
    url = API + path
    delay = 2
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"X-Figma-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                wait = int(e.headers.get("Retry-After", delay))
                print(f"  rate limited, retrying in {wait}s...")
                time.sleep(wait)
                delay *= 2
                continue
            raise
    raise RuntimeError("unreachable")


def find_page(doc, page_name):
    pages = [c for c in doc["children"] if c["type"] == "CANVAS"]
    for p in pages:
        if p["name"].strip().lower() == page_name.strip().lower():
            return p
    names = ", ".join(repr(p["name"]) for p in pages)
    sys.exit(f"page {page_name!r} not found (pages: {names})")


def collect_frames(page):
    """Top-level frames on the page, descending into sections."""
    frames = []

    def walk(node, depth):
        for c in node.get("children", []):
            if c["type"] == "SECTION" and depth < 3:
                walk(c, depth + 1)
            elif c["type"] in ("FRAME", "COMPONENT", "INSTANCE"):
                frames.append((c["id"], c["name"]))

    walk(page, 0)
    return frames


def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", required=True, help="Figma file key")
    ap.add_argument("--page", default="Product Card")
    ap.add_argument("--prefix", default="", help="only frames starting with this")
    ap.add_argument("--scale", type=float, default=1.0, help="export scale (0.01-4)")
    ap.add_argument("--format", default="png", choices=["png", "jpg", "svg", "pdf"])
    ap.add_argument("--out", default=".", help="output directory")
    ap.add_argument("--list", action="store_true", help="list frames and exit")
    args = ap.parse_args()

    token = os.environ.get("FIGMA_TOKEN")
    if not token:
        sys.exit("set FIGMA_TOKEN (Figma > Settings > Security > tokens)")

    print(f"reading file {args.file} ...")
    doc = api_get(f"/files/{args.file}?depth=3", token)
    page = find_page(doc["document"], args.page)
    frames = [(fid, nm) for fid, nm in collect_frames(page)
              if nm.startswith(args.prefix)]
    if not frames:
        sys.exit(f"no frames on page {args.page!r} with prefix {args.prefix!r}")

    print(f"{len(frames)} frame(s) on {page['name']!r}:")
    for _, nm in frames:
        print(f"  {safe_filename(nm)}.{args.format}")
    if args.list:
        return

    os.makedirs(args.out, exist_ok=True)
    # request rendered urls in batches
    for i in range(0, len(frames), 20):
        batch = frames[i:i + 20]
        ids = ",".join(fid for fid, _ in batch)
        q = urllib.parse.urlencode(
            {"ids": ids, "format": args.format, "scale": args.scale})
        res = api_get(f"/images/{args.file}?{q}", token)
        if res.get("err"):
            sys.exit(f"render error: {res['err']}")
        for fid, nm in batch:
            url = res["images"].get(fid)
            if not url:
                print(f"  !! no render for {nm!r}, skipped")
                continue
            dest = os.path.join(args.out,
                                f"{safe_filename(nm)}.{args.format}")
            with urllib.request.urlopen(url, timeout=300) as r, \
                    open(dest, "wb") as f:
                f.write(r.read())
            print(f"  wrote {dest}")
    print("done")


if __name__ == "__main__":
    main()
