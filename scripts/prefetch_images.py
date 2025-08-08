#!/usr/bin/env python3
"""
Prefetch static satellite thumbnails for each finca into frontend/public/cache/

Reads fincas from frontend/public/data/fincas_extreme_west.geojson
Downloads Mapbox Static Images for 1x and 2x DPR.

Env:
  - MAPBOX_TOKEN or REACT_APP_MAPBOX_TOKEN

Usage:
  python scripts/prefetch_images.py
"""

import json
import os
import re
import sys
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


def sanitize_id(value: str) -> str:
    """Make a safe filename from an id (keep alnum, dot, dash, underscore)."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", value.strip())


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def download(url: str, out_path: Path, timeout: int = 30) -> None:
    if out_path.exists() and out_path.stat().st_size > 0:
        return
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def main() -> int:
    token = os.getenv("MAPBOX_TOKEN") or os.getenv("REACT_APP_MAPBOX_TOKEN")
    if not token:
        print("ERROR: MAPBOX_TOKEN (or REACT_APP_MAPBOX_TOKEN) is required.", file=sys.stderr)
        return 1

    root = Path(__file__).resolve().parents[1]
    data_path = root / "frontend" / "public" / "data" / "fincas_extreme_west.geojson"
    out_dir = root / "frontend" / "public" / "cache"
    ensure_dir(out_dir)

    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}", file=sys.stderr)
        return 1

    with open(data_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    features = geojson.get("features") or []
    print(f"Found {len(features)} features. Downloading thumbnails...")

    count = 0
    for feature in features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        fid = str(props.get("id") or "").strip() or None
        coords = None
        if (geom.get("type") == "Point") and isinstance(geom.get("coordinates"), list):
            coords = geom["coordinates"]
        lon = float(props.get("lon") or (coords[0] if coords else 0))
        lat = float(props.get("lat") or (coords[1] if coords else 0))
        if not fid:
            # Skip if no identifier
            continue

        safe_id = sanitize_id(fid)
        # Mapbox static image base (keep consistent with frontend sizes)
        base = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},18.5,0/280x200"
        url_1x = f"{base}?access_token={token}"
        url_2x = f"{base}@2x?access_token={token}"

        out1 = out_dir / f"{safe_id}.jpg"
        out2 = out_dir / f"{safe_id}@2x.jpg"

        try:
            download(url_1x, out1)
            download(url_2x, out2)
            count += 1
        except Exception as e:
            print(f"WARN: failed {fid}: {e}")

    print(f"Done. Cached {count} thumbnails in {out_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


