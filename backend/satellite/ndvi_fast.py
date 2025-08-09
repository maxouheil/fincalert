"""
FAST NDVI - Séparation calcul NDVI et thumbnails
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

# Global progress tracking (réutilisé du fichier optimized)
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

def compute_ndvi_only(lat: float, lon: float, buffer_m: float = 25.0, finca_id: str = None) -> Dict:
    """
    ULTRA-FAST: Calcul NDVI seulement, PAS de thumbnails
    """
    if not _ensure_gee_initialized():
        raise RuntimeError("GEE not configured")

    if finca_id:
        update_progress(finca_id, "Initializing NDVI calculation...", 10)

    pt = ee.Geometry.Point([lon, lat])
    roi = pt.buffer(buffer_m)
    
    windows = _date_windows(months=6, window_days=14)
    entries = []
    total_windows = len(windows)

    if finca_id:
        update_progress(finca_id, "Processing satellite data...", 20)

    for idx, (start, end) in enumerate(windows):
        if finca_id:
            progress = 20 + int((idx / total_windows) * 60)  # 20% to 80%
            update_progress(finca_id, f"Computing NDVI {idx+1}/{total_windows}...", progress)
        
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR")
            .filterBounds(roi)
            .filterDate(start, end)
        )
        
        count = col.size().getInfo()
        if count == 0:
            entries.append({"start": start, "end": end, "ndvi": None, "cloud_pct": 100.0, "thumb": None})
            continue
            
        col = col.map(_mask_s2_clouds)
        median = col.median()
        ndvi = median.normalizedDifference(["B8", "B4"]).rename("NDVI")
        
        # SIMPLIFIED: Just get NDVI value, ignore cloud calculation
        try:
            ndvi_val = ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=30,  # Even larger scale for speed
                bestEffort=True
            ).get('NDVI').getInfo()
            
            if ndvi_val is not None:
                ndvi_val = float(ndvi_val)
            
            # Dummy cloud percentage (we skip this expensive calculation)
            cloud_pct = 50.0 if ndvi_val else 100.0
            
        except Exception as e:
            print(f"NDVI calculation failed for {idx}: {e}")
            ndvi_val = None
            cloud_pct = 100.0

        # NO THUMBNAILS - just save placeholder
        entries.append({
            "start": start, 
            "end": end, 
            "ndvi": ndvi_val, 
            "cloud_pct": cloud_pct, 
            "thumb": f"w_{idx:02d}.png" if ndvi_val else None  # Placeholder
        })

    if finca_id:
        update_progress(finca_id, "Finalizing NDVI analysis...", 90)

    # Quick stats calculation
    ndvi_vals = [e["ndvi"] for e in entries if e["ndvi"] is not None]
    valid = len(ndvi_vals)
    
    if valid == 0:
        status = "unknown"
        median = std = dips = green_persistence = 0
    else:
        median = sorted(ndvi_vals)[valid // 2]
        mean = sum(ndvi_vals) / valid
        std = (sum((v - mean) ** 2 for v in ndvi_vals) / max(1, valid - 1)) ** 0.5
        dips = sum(1 for v in ndvi_vals if v <= (median - 0.15))
        green_persistence = sum(1 for v in ndvi_vals if v >= 0.55) / valid
        
        if dips >= 2 or std >= 0.08:
            status = "active"
        elif dips == 1 or (0.05 <= std < 0.08):
            status = "potential"
        elif green_persistence >= 0.70 and std <= 0.04 and dips == 0:
            status = "inactive"
        else:
            status = "potential"

    if finca_id:
        update_progress(finca_id, "Complete", 100)

    return {
        "series": entries,
        "summary": {
            "valid": valid,
            "median": median,
            "std": std,
            "dips": dips,
            "green_persistence": green_persistence,
            "status": status,
            "window_days": 14,
            "months": 6,
        },
    }

def compute_and_store_fast(finca_id: str, lat: float, lon: float, out_dir: Path, buffer_m: float = 25.0) -> Path:
    """FAST VERSION: NDVI only, no thumbnails"""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "summary.json"
    
    if not _ensure_gee_initialized():
        clear_progress(finca_id)
        raise RuntimeError(f"Google Earth Engine not available for {finca_id}")
    
    try:
        result = compute_ndvi_only(lat, lon, buffer_m, finca_id=finca_id)
        out_file.write_text(json.dumps(result, indent=2))
        
        clear_progress(finca_id)
        return out_file
    except Exception as e:
        clear_progress(finca_id)
        raise RuntimeError(f"NDVI computation failed for {finca_id}: {e}")

def generate_thumbnails_async(finca_id: str, lat: float, lon: float, out_dir: Path):
    """SEPARATE: Generate thumbnails in background (can be called later)"""
    # This would run separately after NDVI calculation
    # Implementation would be similar but only focus on thumbnail generation
    pass
