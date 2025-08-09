import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import ee
import requests

# Safe GEE init: expects env GEE_SERVICE_ACCOUNT and GEE_PRIVATE_KEY (PEM string)

# Global progress tracking
_progress_lock = threading.Lock()
_progress_data = {}  # finca_id -> {stage: str, progress: int, timestamp: float}


def update_progress(finca_id: str, stage: str, progress: int):
    """Update progress for a finca NDVI computation"""
    with _progress_lock:
        _progress_data[finca_id] = {
            'stage': stage,
            'progress': progress,
            'timestamp': time.time()
        }


def get_progress(finca_id: str) -> Dict:
    """Get current progress for a finca"""
    with _progress_lock:
        return _progress_data.get(finca_id, {'stage': 'Unknown', 'progress': 0, 'timestamp': 0})


def clear_progress(finca_id: str):
    """Clear progress data for a finca"""
    with _progress_lock:
        _progress_data.pop(finca_id, None)


def _ensure_gee_initialized() -> bool:
    try:
        # If ee is already initialized, this will succeed
        _ = ee.Number(1).getInfo()
        return True
    except Exception as e:
        print(f"GEE test failed: {e}")
        pass
    try:
        # Try environment variables first
        service_account = os.getenv("GEE_SERVICE_ACCOUNT")
        private_key = os.getenv("GEE_PRIVATE_KEY")
        if service_account and private_key:
            credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
            ee.Initialize(credentials)
            return True
    except Exception:
        pass
    
    try:
        # Fallback to service account JSON file in project root
        project_root = Path(__file__).parent.parent.parent
        key_file = project_root / 'gee-service-account.json'
        if key_file.exists():
            credentials = ee.ServiceAccountCredentials(
                email=None,  # Will be read from the JSON file
                key_file=str(key_file)
            )
            ee.Initialize(credentials)
            return True
    except Exception:
        pass
        
    return False


def _date_windows(months: int = 6, window_days: int = 14) -> List[Tuple[str, str]]:
    end = datetime.utcnow().date()
    start = end - timedelta(days=int(months * 30))
    windows = []
    cur = start
    while cur < end:
        w_end = min(cur + timedelta(days=window_days), end)
        windows.append((cur.isoformat(), w_end.isoformat()))
        cur = w_end
    return windows


def _mask_s2_clouds(img: ee.Image) -> ee.Image:
    # Sentinel-2 SR cloud mask: use SCL classes (3=Cloud shadow, 8=Cloud medium prob, 9=Cloud high prob, 10=Thin cirrus)
    scl = img.select("SCL")
    mask = (
        scl.neq(3)
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(1))  # Saturated/defective
        .And(scl.neq(0))  # No data
    )
    return img.updateMask(mask)


def _compute_ndvi_series(lat: float, lon: float, buffer_m: float, months: int = 6, window_days: int = 14, out_dir: Path | None = None, thumb_size: Tuple[int, int] = (360, 240), finca_id: str = None) -> Dict:
    if not _ensure_gee_initialized():
        raise RuntimeError("GEE not configured")

    if finca_id:
        update_progress(finca_id, "Connecting to Google Earth Engine...", 10)

    pt = ee.Geometry.Point([lon, lat])
    roi = pt.buffer(buffer_m)

    if finca_id:
        update_progress(finca_id, "Querying satellite data...", 20)

    windows = _date_windows(months=months, window_days=window_days)
    entries: List[Dict] = []
    total_windows = len(windows)

    for idx, (start, end) in enumerate(windows):
        if finca_id:
            progress = 30 + int((idx / total_windows) * 55)  # 30% to 85%
            update_progress(finca_id, f"Processing image {idx+1}/{total_windows}...", progress)
        
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR")
            .filterBounds(roi)
            .filterDate(start, end)
        )
        count = col.size()
        if count.getInfo() == 0:
            entries.append({"start": start, "end": end, "ndvi": None, "cloud_pct": 100.0, "thumb": None})
            continue
        col = col.map(_mask_s2_clouds)
        # Compute NDVI on median composite
        median = col.median()
        ndvi = median.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndvi_mean = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=roi, scale=10, bestEffort=True
        ).get("NDVI")

        # Estimate cloud percentage using masked pixels
        total_px = ndvi.reduceRegion(
            reducer=ee.Reducer.count(), geometry=roi, scale=10, bestEffort=True
        ).get("NDVI")
        unmasked_px = median.select("B4").reduceRegion(
            reducer=ee.Reducer.count(), geometry=roi, scale=10, bestEffort=True
        ).get("B4")
        try:
            total_px = float(total_px.getInfo() or 0)
            unmasked_px = float(unmasked_px.getInfo() or 0)
            cloud_pct = max(0.0, min(100.0, 100.0 * (1.0 - (unmasked_px / total_px))) if total_px > 0 else 100.0)
        except Exception:
            cloud_pct = 100.0

        ndvi_val = ndvi_mean.getInfo() if ndvi_mean is not None else None
        if ndvi_val is not None:
            try:
                ndvi_val = float(ndvi_val)
            except Exception:
                ndvi_val = None
        # Optional thumbnail
        thumb_path = None
        if out_dir is not None and ndvi_val is not None and cloud_pct < 60.0:
            try:
                vis = median.visualize(bands=["B4", "B3", "B2"], min=0, max=3000, gamma=1.4)
                url = vis.getThumbURL({
                    "region": roi.coordinates().getInfo(),
                    "dimensions": f"{thumb_size[0]}x{thumb_size[1]}",
                    "format": "png",
                    "crs": "EPSG:3857"  # Web Mercator for better rendering
                })
                r = requests.get(url, timeout=30)
                if r.ok:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    name = f"w_{idx:02d}.png"
                    file_path = out_dir / name
                    with open(file_path, "wb") as f:
                        f.write(r.content)
                    thumb_path = name
            except Exception:
                thumb_path = None

        entries.append({"start": start, "end": end, "ndvi": ndvi_val, "cloud_pct": cloud_pct, "thumb": thumb_path})

    if finca_id:
        update_progress(finca_id, "Calculating NDVI values...", 90)

    # Aggregate stats
    ndvi_vals = [e["ndvi"] for e in entries if e["ndvi"] is not None and e["cloud_pct"] < 40.0]
    valid = len(ndvi_vals)
    if valid == 0:
        return {"series": entries, "summary": {"valid": 0, "status": "unknown"}}

    median6 = sorted(ndvi_vals)[valid // 2]
    mean = sum(ndvi_vals) / valid
    std = (sum((v - mean) ** 2 for v in ndvi_vals) / max(1, valid - 1)) ** 0.5
    dips = sum(1 for v in ndvi_vals if v <= (median6 - 0.15))
    green_persistence = sum(1 for v in ndvi_vals if v >= 0.55) / valid

    # Classification
    if dips >= 2 or std >= 0.08:
        status = "active"
    elif dips == 1 or (0.05 <= std < 0.08):
        status = "potential"
    elif green_persistence >= 0.70 and std <= 0.04 and dips == 0:
        status = "inactive"
    else:
        status = "potential"

    if finca_id:
        update_progress(finca_id, "Finalizing analysis...", 100)

    return {
        "series": entries,
        "summary": {
            "valid": valid,
            "median": median6,
            "std": std,
            "dips": dips,
            "green_persistence": green_persistence,
            "status": status,
            "window_days": window_days,
            "months": months,
        },
    }


def _create_fallback_ndvi_data(finca_id: str, lat: float, lon: float) -> Dict:
    """Create fallback NDVI data when GEE is not working"""
    import random
    from datetime import datetime, timedelta
    
    print(f"Creating fallback NDVI data for {finca_id}")
    
    # Generate 12 periods (6 months, bi-weekly)
    series = []
    end_date = datetime.now()
    
    for i in range(12):
        start = end_date - timedelta(days=(i+1)*14)
        end = end_date - timedelta(days=i*14)
        
        # Simulate realistic NDVI values (0.2-0.4 range)
        ndvi_val = 0.2 + random.random() * 0.2
        
        series.append({
            "start": start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "ndvi": ndvi_val,
            "cloud_pct": random.random() * 20,  # 0-20% cloud cover
            "thumb": None  # No thumbnails for fallback data
        })
    
    # Reverse to have chronological order
    series.reverse()
    
    return {
        "series": series,
        "summary": {
            "valid": len(series),
            "median": 0.3,
            "std": 0.05,
            "dips": 0,
            "green_persistence": 0.0,
            "status": "estimated",  # Mark as estimated data
            "window_days": 14,
            "months": 6
        }
    }


def compute_and_store(finca_id: str, lat: float, lon: float, out_dir: Path, buffer_m: float = 25.0) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "summary.json"
    
    # Fail fast if GEE is not available
    if not _ensure_gee_initialized():
        clear_progress(finca_id)
        raise RuntimeError(f"Google Earth Engine not available for {finca_id}")
    
    try:
        result = _compute_ndvi_series(lat, lon, buffer_m, out_dir=out_dir, finca_id=finca_id)
        out_file.write_text(json.dumps(result, indent=2))
        
        # Clear progress when done
        clear_progress(finca_id)
        
        return out_file
    except Exception as e:
        # Clear progress and fail
        clear_progress(finca_id)
        raise RuntimeError(f"NDVI computation failed for {finca_id}: {e}")


def load_summary(path: Path) -> Dict:
    if path.is_file():
        return json.loads(path.read_text())
    raise FileNotFoundError(str(path))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--lat", type=float, required=True)
    parser.add_argument("--lon", type=float, required=True)
    parser.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "data" / "ndvi"))
    args = parser.parse_args()
    out = Path(args.out) / args.id
    p = compute_and_store(args.id, args.lat, args.lon, out)
    print(f"Wrote {p}")


