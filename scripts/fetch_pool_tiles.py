#!/usr/bin/env python3
"""
Fetch high-resolution Mapbox Static tiles for each finca.

Inputs:
  - GeoJSON with features containing properties: id, lat, lon
Outputs:
  - JPEG tiles saved to the output directory (one per finca)

Env:
  - MAPBOX_TOKEN or REACT_APP_MAPBOX_TOKEN must be set

Example:
  python scripts/fetch_pool_tiles.py \
    --input frontend/public/data/fincas_with_abandon_scores.geojson \
    --out data/pools/tiles --zoom 19.5 --size 640 --threads 8
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import requests


def sanitize_id(fid: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in fid)


def build_mapbox_url(lon: float, lat: float, zoom: float, size: int, token: str) -> str:
    # Use @2x for better quality
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lon},{lat},{zoom},0/{size}x{size}@2x?access_token={token}"
    )


def download(url: str, out_path: Path, timeout: int = 20) -> Tuple[bool, Optional[str]]:
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, timeout=timeout, stream=True) as r:
            if r.status_code == 429:
                return False, "rate_limited"
            if not r.ok:
                return False, f"http_{r.status_code}"
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True, None
    except Exception as e:
        return False, str(e)


def process_feature(feature: dict, *, zoom: float, size: int, token: str, out_dir: Path) -> Tuple[str, bool, Optional[str]]:
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    fid = str(props.get("id") or "").strip()
    if not fid:
        return ("", False, "missing_id")

    if geom.get("type") == "Point" and isinstance(geom.get("coordinates"), list):
        lon, lat = geom["coordinates"][0], geom["coordinates"][1]
    else:
        lon = float(props.get("lon")) if props.get("lon") is not None else None
        lat = float(props.get("lat")) if props.get("lat") is not None else None
    if lat is None or lon is None:
        return (fid, False, "missing_coords")

    url = build_mapbox_url(lon, lat, zoom, size, token)
    safe_id = sanitize_id(fid)
    out_file = out_dir / f"{safe_id}.jpg"

    if out_file.exists() and out_file.stat().st_size > 0:
        return (fid, True, "cached")

    ok, err = download(url, out_file)
    return (fid, ok, err)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Mapbox tiles for fincas")
    parser.add_argument("--input", required=True, help="Path to GeoJSON with fincas")
    parser.add_argument("--out", required=True, help="Output directory for tiles")
    parser.add_argument("--zoom", type=float, default=19.5, help="Mapbox zoom level (default: 19.5)")
    parser.add_argument("--size", type=int, default=640, help="Tile size in px (default: 640)")
    parser.add_argument("--threads", type=int, default=8, help="Concurrent downloads")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of fincas (0 = all)")
    args = parser.parse_args()

    token = os.getenv("MAPBOX_TOKEN") or os.getenv("REACT_APP_MAPBOX_TOKEN")
    if not token:
        print("ERROR: MAPBOX_TOKEN (or REACT_APP_MAPBOX_TOKEN) is required.", file=sys.stderr)
        return 1

    input_path = Path(args.input)
    out_dir = Path(args.out)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 1

    with open(input_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    features = geojson.get("features") or []
    total = len(features)
    if args.limit and args.limit > 0:
        features = features[: args.limit]

    print(f"Found {total} features. Downloading {len(features)} tiles to {out_dir}…")

    start = time.time()
    completed = 0
    rate_limited = 0
    failed = 0

    def worker(feat: dict) -> Tuple[str, bool, Optional[str]]:
        return process_feature(feat, zoom=args.zoom, size=args.size, token=token, out_dir=out_dir)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as ex:
        for fid, ok, err in ex.map(worker, features):
            completed += 1
            if ok:
                if err == "cached":
                    print(f"[CACHE] {fid}")
                else:
                    print(f"[OK] {fid}")
            else:
                if err == "rate_limited":
                    rate_limited += 1
                else:
                    failed += 1
                print(f"[ERR] {fid}: {err}")

    dt = time.time() - start
    print(f"Done in {dt:.1f}s. ok={completed - failed - rate_limited}, rate_limited={rate_limited}, failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


