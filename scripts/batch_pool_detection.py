#!/usr/bin/env python3
"""
Batch detect pools on high-res tiles using HSV + shape heuristics.

Inputs:
  - GeoJSON with fincas (id, lat, lon)
  - Tiles directory with {id}.jpg tiles (from fetch_pool_tiles.py)

Outputs:
  - JSON and CSV with detection results
  - Optional overlays directory with annotated images

Example:
  python scripts/batch_pool_detection.py \
    --input frontend/public/data/fincas_with_abandon_scores.geojson \
    --tiles data/pools/tiles --out data/pools --threads 8 --overlays
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import math
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class PoolDetection:
    finca_id: str
    pool_detected: bool
    state: str  # blue | green | empty | covered | unknown
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]]
    area_px: int


def load_image(path: Path) -> Optional[np.ndarray]:
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def classify_pool_state(bgr_roi: np.ndarray) -> Tuple[str, float]:
    if bgr_roi is None or bgr_roi.size == 0:
        return "unknown", 0.0

    hsv = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)

    blue_mask = cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255]))
    green_mask = cv2.inRange(hsv, np.array([40, 50, 50]), np.array([80, 255, 255]))
    empty_mask = cv2.inRange(hsv, np.array([0, 0, 30]), np.array([180, 50, 150]))

    total_px = bgr_roi.shape[0] * bgr_roi.shape[1]
    if total_px == 0:
        return "unknown", 0.0

    blue_pct = cv2.countNonZero(blue_mask) / total_px
    green_pct = cv2.countNonZero(green_mask) / total_px
    empty_pct = cv2.countNonZero(empty_mask) / total_px

    if blue_pct > 0.15:
        return "blue", min(1.0, blue_pct * 2)
    if green_pct > 0.10:
        return "green", min(1.0, green_pct * 2.5)
    if empty_pct > 0.20:
        return "empty", min(1.0, empty_pct * 1.5)

    gray = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2GRAY)
    if float(np.mean(gray)) < 80.0:
        return "covered", 0.6
    return "unknown", 0.3


def detect_pool_hsv_shape(img: np.ndarray) -> Tuple[bool, Optional[Tuple[int, int, int, int]], str, float, int]:
    h, w = img.shape[:2]

    # Exclude borders (reduce false detections outside parcel)
    pad = int(min(h, w) * 0.05)
    work = img[pad:h - pad, pad:w - pad].copy()

    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)

    blue = cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255]))
    green = cv2.inRange(hsv, np.array([40, 50, 50]), np.array([80, 255, 255]))
    water_mask = cv2.max(blue, green)

    water_mask = cv2.medianBlur(water_mask, 5)
    water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    water_mask = cv2.morphologyEx(water_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

    contours, _ = cv2.findContours(water_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_score = 0.0
    best_area = 0

    for cnt in contours:
        area = int(cv2.contourArea(cnt))
        if area < 2500:  # min area threshold
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        rect_area = bw * bh
        if rect_area == 0:
            continue
        fill_ratio = area / rect_area  # compactness
        ratio = bw / max(1, bh)
        if ratio < 0.25 or ratio > 4.0:
            continue
        if fill_ratio < 0.5:
            continue

        # score combines compactness and area
        score = fill_ratio * math.log1p(area)
        if score > best_score:
            best_score = score
            best_area = area
            best = (x + pad, y + pad, x + bw + pad, y + bh + pad)

    if best is None:
        return False, None, "unknown", 0.0, 0

    x1, y1, x2, y2 = best
    roi = img[y1:y2, x1:x2]
    state, color_conf = classify_pool_state(roi)
    # Normalize confidence ~0..1 using score
    conf = max(0.1, min(0.99, best_score / 3000.0)) * color_conf
    return True, best, state, float(conf), best_area


def annotate_overlay(img: np.ndarray, bbox: Tuple[int, int, int, int], state: str, path: Path) -> None:
    x1, y1, x2, y2 = bbox
    color = (34, 197, 94) if state == "blue" else (16, 185, 129) if state == "green" else (107, 114, 128)
    vis = img.copy()
    cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
    cv2.putText(vis, f"pool:{state}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)
    cv2.imwrite(str(path), vis)


def process_finca(feature: dict, tiles_dir: Path, overlays_dir: Optional[Path]) -> PoolDetection:
    props = feature.get("properties") or {}
    fid = str(props.get("id") or "").strip()
    safe_id = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in fid)
    tile_path = tiles_dir / f"{safe_id}.jpg"

    if not tile_path.exists():
        return PoolDetection(fid, False, "unknown", 0.0, None, 0)

    img = load_image(tile_path)
    if img is None:
        return PoolDetection(fid, False, "unknown", 0.0, None, 0)

    ok, bbox, state, conf, area = detect_pool_hsv_shape(img)
    if ok and overlays_dir is not None:
        overlays_dir.mkdir(parents=True, exist_ok=True)
        annotate_overlay(img, bbox, state, overlays_dir / f"{safe_id}.jpg")

    return PoolDetection(fid, ok, state, conf, bbox, area)


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch pool detection")
    ap.add_argument("--input", required=True, help="Path to fincas GeoJSON")
    ap.add_argument("--tiles", required=True, help="Directory with downloaded tiles")
    ap.add_argument("--out", required=True, help="Output directory for results")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--overlays", action="store_true", help="Save annotated overlays")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    input_path = Path(args.input)
    tiles_dir = Path(args.tiles)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    features = geojson.get("features") or []
    total = len(features)
    if args.limit and args.limit > 0:
        features = features[: args.limit]

    overlays_dir = out_dir / "overlays" if args.overlays else None

    print(f"Detecting pools on {len(features)}/{total} fincas…")
    start = time.time()

    results: List[PoolDetection] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as ex:
        for det in ex.map(lambda f: process_finca(f, tiles_dir, overlays_dir), features):
            results.append(det)

    dt = time.time() - start
    print(f"Done in {dt:.1f}s")

    # Export JSON
    ts = time.strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"fincas_pools_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"results": [asdict(r) for r in results]}, f, ensure_ascii=False, indent=2)

    # Export CSV
    csv_path = out_dir / f"fincas_pools_{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["finca_id", "pool_detected", "state", "confidence", "area_px", "bbox"])
        for r in results:
            writer.writerow([r.finca_id, int(r.pool_detected), r.state, f"{r.confidence:.3f}", r.area_px, r.bbox])

    # Summary
    total_detected = sum(1 for r in results if r.pool_detected)
    print(f"Pools detected: {total_detected}/{len(results)} ({(100.0*total_detected/ max(1,len(results))):.1f}%)")
    print(f"JSON: {json_path}")
    print(f"CSV:  {csv_path}")
    if overlays_dir:
        print(f"Overlays: {overlays_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


