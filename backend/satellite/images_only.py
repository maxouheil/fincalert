"""
Images Satellites SEULEMENT - Sans calcul NDVI
Strategy: Get thumbnails first, calculate NDVI later
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import ee
import requests

# Global progress tracking
_progress_lock = threading.Lock()
_progress_data = {}

def update_progress(finca_id: str, stage: str, progress: int):
    with _progress_lock:
        _progress_data[finca_id] = {
            'stage': stage,
            'progress': progress,
            'timestamp': time.time()
        }

def get_progress(finca_id: str) -> Dict:
    with _progress_lock:
        return _progress_data.get(finca_id, {'stage': 'Unknown', 'progress': 0, 'timestamp': 0})

def clear_progress(finca_id: str):
    with _progress_lock:
        _progress_data.pop(finca_id, None)

def _ensure_gee_initialized() -> bool:
    try:
        _ = ee.Number(1).getInfo()
        return True
    except Exception:
        pass
    try:
        project_root = Path(__file__).parent.parent.parent
        key_file = project_root / 'gee-service-account.json'
        if key_file.exists():
            credentials = ee.ServiceAccountCredentials(email=None, key_file=str(key_file))
            ee.Initialize(credentials)
            _ = ee.Number(1).getInfo()
            return True
    except Exception:
        pass
    return False

def _date_windows(months: int = 6, window_days: int = 14) -> List[Tuple[str, str]]:
    end = datetime.utcnow().date()
    start = end - timedelta(days=months * 30)
    windows = []
    current = start
    while current < end:
        next_date = current + timedelta(days=window_days)
        if next_date > end:
            next_date = end
        windows.append((current.isoformat(), next_date.isoformat()))
        current = next_date
    return windows

def _mask_s2_clouds(img):
    scl = img.select("SCL")
    mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(1)).And(scl.neq(0))
    return img.updateMask(mask)

def get_thumbnails_only(lat: float, lon: float, out_dir: Path, buffer_m: float = 25.0, finca_id: str = None) -> Dict:
    """
    ULTRA-FAST: Récupération des thumbnails seulement
    Pas de calcul NDVI = Pas de .getInfo() lents
    """
    if not _ensure_gee_initialized():
        raise RuntimeError("GEE not configured")

    if finca_id:
        update_progress(finca_id, "Preparing satellite image collection...", 10)

    pt = ee.Geometry.Point([lon, lat])
    roi = pt.buffer(buffer_m)
    roi_coords = roi.coordinates().getInfo()  # Une seule fois
    
    windows = _date_windows(months=6, window_days=14)
    entries = []
    total_windows = len(windows)

    if finca_id:
        update_progress(finca_id, "Downloading satellite images...", 20)

    for idx, (start, end) in enumerate(windows):
        if finca_id:
            progress = 20 + int((idx / total_windows) * 70)  # 20% to 90%
            update_progress(finca_id, f"Downloading image {idx+1}/{total_windows}...", progress)
        
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR")
            .filterBounds(roi)
            .filterDate(start, end)
        )
        
        # OPTIMIZATION: Skip count check - just try to get median
        try:
            col = col.map(_mask_s2_clouds)
            median = col.median()
            
            # FOCUS: Just get the thumbnail, no NDVI calculation
            vis = median.visualize(
                bands=["B4", "B3", "B2"], 
                min=0, 
                max=2000
            )
            
            url = vis.getThumbURL({
                "region": roi_coords,
                "dimensions": "200x150",  # Slightly bigger for quality
                "format": "png"
            })
            
            # Download thumbnail with short timeout
            r = requests.get(url, timeout=5)
            
            thumb_path = None
            if r.ok:
                out_dir.mkdir(parents=True, exist_ok=True)
                name = f"w_{idx:02d}.png"
                file_path = out_dir / name
                with open(file_path, "wb") as f:
                    f.write(r.content)
                thumb_path = name
                print(f"✅ Downloaded thumbnail {idx+1}: {name}")
            else:
                print(f"❌ Thumbnail download failed for {idx+1}: {r.status_code}")
            
            # Placeholder entry - NO NDVI calculation yet
            entries.append({
                "start": start,
                "end": end,
                "ndvi": None,  # Will be calculated later
                "cloud_pct": 50.0,  # Placeholder
                "thumb": thumb_path
            })
            
        except Exception as e:
            print(f"❌ Image processing failed for {idx}: {e}")
            entries.append({
                "start": start,
                "end": end,
                "ndvi": None,
                "cloud_pct": 100.0,
                "thumb": None
            })

    if finca_id:
        update_progress(finca_id, "Images downloaded successfully", 100)

    # Return minimal structure for now
    return {
        "series": entries,
        "summary": {
            "valid": len([e for e in entries if e["thumb"]]),
            "status": "images_only",  # Special status
            "window_days": 14,
            "months": 6,
            "note": "Images downloaded, NDVI calculation pending"
        },
    }

def compute_images_only(finca_id: str, lat: float, lon: float, out_dir: Path, buffer_m: float = 25.0) -> Path:
    """
    PUBLIC API: Get satellite images only, no NDVI
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "images.json"  # Different filename
    
    if not _ensure_gee_initialized():
        clear_progress(finca_id)
        raise RuntimeError(f"Google Earth Engine not available for {finca_id}")
    
    try:
        result = get_thumbnails_only(lat, lon, out_dir, buffer_m, finca_id=finca_id)
        out_file.write_text(json.dumps(result, indent=2))
        
        clear_progress(finca_id)
        print(f"🎯 Images saved to: {out_file}")
        return out_file
    except Exception as e:
        clear_progress(finca_id)
        raise RuntimeError(f"Image download failed for {finca_id}: {e}")

if __name__ == "__main__":
    # Test direct
    import tempfile
    test_dir = Path(tempfile.mkdtemp())
    print(f"Testing images-only download to: {test_dir}")
    
    try:
        result_file = compute_images_only("test", 38.92, 1.28, test_dir)
        with open(result_file) as f:
            data = json.load(f)
        
        images_count = len([s for s in data["series"] if s["thumb"]])
        print(f"✅ SUCCESS: Downloaded {images_count} thumbnail images")
        
        # List downloaded files
        for file in test_dir.glob("*.png"):
            print(f"  📸 {file.name}")
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
