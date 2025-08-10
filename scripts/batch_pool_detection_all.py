#!/usr/bin/env python3
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any
import requests

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.detection.yolo_pool_detector import YOLOPoolDetector  # noqa: E402


def build_mapbox_url(lon: float, lat: float, zoom: int = 19, width: int = 1280, height: int = 960) -> str:
    token = os.getenv('MAPBOX_TOKEN') or os.getenv('REACT_APP_MAPBOX_TOKEN')
    if not token:
        raise RuntimeError('MAPBOX_TOKEN not configured')
    return (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lon},{lat},{zoom},0/{width}x{height}@2x?access_token={token}"
    )


def main() -> int:
    geojson_path = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    out_dir = ROOT / 'data' / 'test_results'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / 'pools_full_summary.json'

    with open(geojson_path, 'r') as f:
        data = json.load(f)

    features = data.get('features', [])
    print(f"Total features: {len(features)}")

    # Detector uses env vars for model and crop; ensure defaults
    os.environ.setdefault('POOL_CROP_RATIO', '0.7')

    detector = YOLOPoolDetector()
    results = []

    start = time.time()
    for idx, ft in enumerate(features, 1):
        props: Dict[str, Any] = ft.get('properties', {})
        fid = props.get('id')
        lat = props.get('lat')
        lon = props.get('lon')
        if not fid or lat is None or lon is None:
            continue

        url = build_mapbox_url(lon, lat)
        try:
            det = detector.detect_pools_from_url(url, fid)
            results.append({
                'finca_id': fid,
                'lat': lat,
                'lon': lon,
                'pool_detected': det.get('pool_detected', False),
                'pool_count': det.get('pool_count', 0),
                'best_pool': det.get('best_pool'),
                'summary': det.get('summary')
            })
        except Exception as e:
            results.append({'finca_id': fid, 'error': str(e)})

        if idx % 25 == 0:
            # checkpoint
            out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
            elapsed = time.time() - start
            print(f"Processed {idx}/{len(features)} in {elapsed:.1f}s")

    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    elapsed = time.time() - start
    print(f"Done. Saved {len(results)} results to {out_json} in {elapsed:.1f}s")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


