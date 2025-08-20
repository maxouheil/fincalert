#!/usr/bin/env python3
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.detection.yolo_vehicle_detector import YOLOVehicleDetector  # noqa: E402


def build_mapbox_url(lon: float, lat: float, zoom: int = 19, width: int = 1280, height: int = 960) -> str:
    token = os.getenv('MAPBOX_TOKEN') or os.getenv('REACT_APP_MAPBOX_TOKEN')
    if not token:
        raise RuntimeError('MAPBOX_TOKEN not configured')
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lon},{lat},{zoom},0/{width}x{height}@2x?access_token={token}"
    )


def main(limit: int = 30) -> int:
    geojson_path = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    out_dir = ROOT / 'data' / 'test_results'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / 'vehicles_full_summary.json'
    out_log = out_dir / 'vehicles_full_summary.log'

    with open(geojson_path, 'r') as f:
        data = json.load(f)

    features = data.get('features', [])
    print(f"Total features: {len(features)}")

    # Detector config via env vars has sensible defaults
    os.environ.setdefault('VEHICLE_CROP_RATIO', '0.7')
    os.environ.setdefault('VEHICLE_ALLOWED_CLASSES', 'car,truck,bus,motorcycle,bicycle')

    detector = YOLOVehicleDetector()
    results = []

    start = time.time()
    processed = 0
    for idx, ft in enumerate(features, 1):
        if processed >= limit:
            break
        props: Dict[str, Any] = ft.get('properties', {})
        fid = props.get('id')
        lat = props.get('lat')
        lon = props.get('lon')
        if not fid or lat is None or lon is None:
            continue

        url = build_mapbox_url(lon, lat)
        try:
            det = detector.detect_vehicles_from_url(url, fid)
            results.append({
                'finca_id': fid,
                'lat': lat,
                'lon': lon,
                'vehicle_detected': det.get('vehicle_detected', False),
                'total_count': det.get('total_count', 0),
                'counts_by_class': det.get('counts_by_class', {}),
                'best_vehicle': det.get('best_vehicle'),
                'summary': det.get('summary')
            })
        except Exception as e:
            results.append({'finca_id': fid, 'error': str(e)})

        processed += 1

        if processed % 10 == 0:
            out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
            with open(out_log, 'a') as lf:
                lf.write(f"Processed {processed}/{limit}\n")
            elapsed = time.time() - start
            print(f"Processed {processed}/{limit} in {elapsed:.1f}s")

    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    elapsed = time.time() - start
    print(f"Done. Saved {len(results)} results to {out_json} in {elapsed:.1f}s")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


