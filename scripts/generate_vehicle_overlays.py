#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from typing import List
import requests
import cv2
import numpy as np

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.detection.yolo_vehicle_detector import YOLOVehicleDetector  # noqa: E402

OUT_DIR = ROOT / 'data' / 'test_results' / 'overlays_top30_vehicles'
OUT_DIR.mkdir(parents=True, exist_ok=True)

GEOJSON = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'


def build_mapbox_url(lon: float, lat: float) -> str:
    token = os.getenv('MAPBOX_TOKEN') or os.getenv('REACT_APP_MAPBOX_TOKEN')
    if not token:
        raise RuntimeError('MAPBOX_TOKEN not configured')
    zoom = 21  # Optimal zoom for Mapbox (clear, not upscaled)
    width, height = 1280, 1280  # Standard resolution
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lon},{lat},{zoom},0/{width}x{height}@2x?access_token={token}"
    )


def draw_overlays(image_bgr: np.ndarray, detections: List[dict]) -> np.ndarray:
    output = image_bgr.copy()
    for det in detections:
        x1, y1, x2, y2 = det.get('bbox', [0, 0, 0, 0])
        cls = det.get('class', 'vehicle')
        conf = float(det.get('confidence', 0.0) or 0.0)
        color = (0, 165, 255)  # orange default
        if cls in ('car', 'motorcycle', 'bicycle'):
            color = (0, 255, 0)  # green
        elif cls in ('truck', 'bus'):
            color = (255, 0, 0)  # blue-ish red
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        label = f"{cls} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        y0 = max(0, y1 - th - 6)
        cv2.rectangle(output, (x1, y0), (x1 + tw + 6, y0 + th + 6), color, -1)
        cv2.putText(output, label, (x1 + 3, y0 + th + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return output


def main() -> int:
    print("Starting vehicle overlay generation...")
    with open(GEOJSON, 'r') as f:
        data = json.load(f)
    features = data.get('features', [])

    def id_num(fid: str) -> int:
        try:
            return int(fid.split('_')[-1])
        except Exception:
            return 10**9

    top = [ft for ft in features if ft.get('properties', {}).get('id', '').startswith('finca_')]
    top.sort(key=lambda ft: id_num(ft['properties']['id']))
    top = [ft for ft in top if 1 <= id_num(ft['properties']['id']) <= 30]
    print(f"Processing {len(top)} fincas (top 30)")

    # Use same parameters as the detector for consistency
    detector = YOLOVehicleDetector()
    # Override with optimized settings for Mapbox zoom 21
    detector.conf_threshold = 0.12
    detector.iou_threshold = 0.35

    results = []
    for i, ft in enumerate(top):
        print(f"Processing finca {i+1}/30: {ft['properties']['id']}")
        props = ft['properties']
        fid = props['id']
        lat = props['lat']
        lon = props['lon']
        url = build_mapbox_url(lon, lat)
        # Download base image
        print(f"  Downloading image for {fid}...")
        r = requests.get(url, timeout=30)
        if not r.ok:
            print(f"  Error: mapbox {r.status_code}")
            results.append({"finca_id": fid, "error": f"mapbox {r.status_code}"})
            continue
        buf = np.frombuffer(r.content, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            print(f"  Error: decode failed")
            results.append({"finca_id": fid, "error": "decode failed"})
            continue

        det = detector.detect_vehicles_from_url(url, fid)
        vehicles = det.get('all_vehicles', [])
        overlay = draw_overlays(img, vehicles)

        out_path = OUT_DIR / f"{fid}.jpg"
        cv2.imwrite(str(out_path), overlay)
        results.append({
            "finca_id": fid,
            "vehicle_detected": det.get('vehicle_detected', False),
            "total_count": det.get('total_count', 0),
            "summary": det.get('summary'),
            "overlay": str(out_path)
        })
        print(f"{fid}: {det.get('summary')} -> {out_path}")

    out_json = OUT_DIR / 'summary.json'
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print('\nSaved summary to', out_json)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


