"""
NDVI SCORE ONLY - Ultra-rapide pour scoring à grande échelle
Objectif: Calculer score d'abandon sans images pour 600 fincas
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import concurrent.futures
import threading

import ee

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
    mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    return img.updateMask(mask)

def compute_ndvi_score_fast(lat: float, lon: float, buffer_m: float = 25.0, finca_id: str = None) -> Dict:
    """
    ULTRA-RAPIDE: Calcul score NDVI seulement
    NO IMAGES, NO THUMBNAILS, MINIMAL GETINFO CALLS
    """
    if not _ensure_gee_initialized():
        raise RuntimeError("GEE not configured")

    if finca_id:
        update_progress(finca_id, "Initializing fast NDVI calculation...", 10)

    pt = ee.Geometry.Point([lon, lat])
    roi = pt.buffer(buffer_m)
    
    windows = _date_windows(months=6, window_days=14)
    
    if finca_id:
        update_progress(finca_id, "Processing batch NDVI calculations...", 30)

    # STRATEGY: Batch all NDVI calculations into ONE big getInfo() call
    ndvi_calculations = []
    
    for idx, (start, end) in enumerate(windows):
        col = (
            ee.ImageCollection("COPERNICUS/S2_SR")
            .filterBounds(roi)
            .filterDate(start, end)
            .map(_mask_s2_clouds)
        )
        
        # Add to batch calculation list
        median = col.median()
        ndvi = median.normalizedDifference(["B8", "B4"]).rename("NDVI")
        
        ndvi_mean = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=50,  # Large scale for speed
            bestEffort=True,
            maxPixels=1e4  # Very limited pixels for speed
        ).get('NDVI')
        
        ndvi_calculations.append({
            'start': start,
            'end': end,
            'ndvi_calc': ndvi_mean,
            'index': idx
        })

    if finca_id:
        update_progress(finca_id, "Executing batch calculation...", 60)

    # CRITICAL: Single batch getInfo() call for ALL NDVI values
    try:
        batch_dict = ee.Dictionary({
            f'ndvi_{i}': calc['ndvi_calc'] 
            for i, calc in enumerate(ndvi_calculations)
        })
        
        # ONE SINGLE getInfo() call for all NDVI values
        all_ndvi_results = batch_dict.getInfo()
        
        if finca_id:
            update_progress(finca_id, "Processing results...", 80)
        
        # Process results
        entries = []
        ndvi_values = []
        
        for i, calc in enumerate(ndvi_calculations):
            ndvi_val = all_ndvi_results.get(f'ndvi_{i}')
            
            if ndvi_val is not None:
                ndvi_val = float(ndvi_val)
                ndvi_values.append(ndvi_val)
            
            entries.append({
                "start": calc['start'],
                "end": calc['end'],
                "ndvi": ndvi_val,
                "cloud_pct": 50.0 if ndvi_val else 100.0,  # Placeholder
                "thumb": None  # NO IMAGES
            })

    except Exception as e:
        print(f"Batch NDVI calculation failed: {e}")
        # Fallback to individual calculations with timeout
        entries = []
        ndvi_values = []
        
        for calc in ndvi_calculations:
            try:
                ndvi_val = calc['ndvi_calc'].getInfo()
                if ndvi_val is not None:
                    ndvi_val = float(ndvi_val)
                    ndvi_values.append(ndvi_val)
            except:
                ndvi_val = None
            
            entries.append({
                "start": calc['start'],
                "end": calc['end'],
                "ndvi": ndvi_val,
                "cloud_pct": 50.0 if ndvi_val else 100.0,
                "thumb": None
            })

    if finca_id:
        update_progress(finca_id, "Calculating abandon score...", 90)

    # Fast statistics calculation
    valid = len(ndvi_values)
    
    if valid == 0:
        status = "unknown"
        median = std = dips = green_persistence = abandon_score = 0
    else:
        ndvi_values.sort()
        median = ndvi_values[valid // 2]
        mean = sum(ndvi_values) / valid
        std = (sum((v - mean) ** 2 for v in ndvi_values) / max(1, valid - 1)) ** 0.5
        dips = sum(1 for v in ndvi_values if v <= (median - 0.15))
        green_persistence = sum(1 for v in ndvi_values if v >= 0.55) / valid
        
        # Use new realistic algorithm
        status, abandon_score = _calculate_abandon_score_realistic(median, std, dips, green_persistence)

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
            "abandon_score": abandon_score,
            "window_days": 14,
            "months": 6,
        },
    }

def _calculate_abandon_score_realistic(median_ndvi: float, std: float, dips: int, green_persistence: float) -> tuple:
    """
    Calculate activity status and abandon score using realistic algorithm
    Returns: (status, score)
    
    Distribution target: 46% Active, 38% Semi-active, 16% Inactive
    """
    # Calculate coefficient of variation (CV)
    cv_percent = (std / median_ndvi) * 100.0 if median_ndvi > 0 else 0.0
    
    # INACTIVE/ABANDONNÉE (Score 70-85) - Target ~15%
    if (cv_percent < 12 and dips == 0) or \
       (median_ndvi >= 0.4 and cv_percent < 8) or \
       (green_persistence >= 0.5) or \
       (median_ndvi >= 0.3 and cv_percent < 6):
        # Abandoned finca: stable vegetation, no activity
        base_score = 72.0
        # Bonus for extreme stability
        stability_bonus = max(0, (12 - cv_percent) * 0.8) if cv_percent < 12 else 0
        # Bonus for dense vegetation
        vegetation_bonus = (median_ndvi - 0.2) * 15 if median_ndvi > 0.2 else 0
        score = min(85.0, base_score + stability_bonus + vegetation_bonus)
        return "inactive", score
    
    # ACTIVE (Score 15-35) - Target ~45%
    elif (cv_percent >= 25) or \
         (cv_percent >= 18 and dips >= 1) or \
         (cv_percent >= 20 and median_ndvi < 0.25):
        # Active finca: high variation, detected activity
        base_score = 25.0
        activity_bonus = min(8.0, (cv_percent - 18) * 0.3) if cv_percent > 18 else 0
        dips_bonus = min(5.0, dips * 2.5)
        score = max(15.0, base_score - activity_bonus - dips_bonus)
        return "active", score
    
    # SEMI-ACTIVE (Score 40-65) - Target ~40%
    else:
        # Semi-active finca: moderate usage, transition
        base_score = 52.0
        
        # CV adjustment
        if cv_percent < 15:
            cv_adjustment = (15 - cv_percent) * 0.6
        else:
            cv_adjustment = -(cv_percent - 15) * 0.3
        
        # Dips adjustment
        dips_adjustment = -dips * 2 if dips > 0 else 3
        
        score = base_score + cv_adjustment + dips_adjustment
        score = max(40.0, min(65.0, score))
        return "semi-active", score

def _calculate_abandon_score(status: str, std: float, dips: int, green_persistence: float) -> float:
    """Legacy function for backward compatibility - should not be used with new algorithm"""
    if status == "inactive":
        return 85.0 + min(15.0, green_persistence * 15.0)
    elif status == "potential":
        return 80.0 - min(40.0, std * 500.0) + dips * 10.0
    elif status == "active":
        return max(5.0, 25.0 - std * 200.0 - dips * 5.0)
    else:
        return 50.0  # unknown

def batch_process_fincas(finca_coords: List[Dict], max_workers: int = 5) -> Dict:
    """
    Process multiple fincas in parallel for abandon scoring
    finca_coords: [{"id": "finca_001", "lat": 38.9, "lon": 1.3}, ...]
    """
    results = {}
    
    def process_single_finca(finca_data):
        finca_id = finca_data["id"]
        lat = finca_data["lat"]
        lon = finca_data["lon"]
        
        try:
            start_time = time.time()
            result = compute_ndvi_score_fast(lat, lon, finca_id=finca_id)
            duration = time.time() - start_time
            
            return {
                "finca_id": finca_id,
                "success": True,
                "duration": duration,
                "result": result
            }
        except Exception as e:
            return {
                "finca_id": finca_id,
                "success": False,
                "error": str(e),
                "duration": 0
            }

    # Parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_single_finca, finca) for finca in finca_coords]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results[result["finca_id"]] = result
            
            if result["success"]:
                score = result["result"]["summary"]["abandon_score"]
                status = result["result"]["summary"]["status"]
                print(f"✅ {result['finca_id']}: {status} (score: {score:.1f}) in {result['duration']:.1f}s")
            else:
                print(f"❌ {result['finca_id']}: {result['error']}")

    return results

if __name__ == "__main__":
    # Test with sample fincas
    test_fincas = [
        {"id": "finca_test_001", "lat": 38.92, "lon": 1.28},
        {"id": "finca_test_002", "lat": 38.91, "lon": 1.29},
        {"id": "finca_test_003", "lat": 38.93, "lon": 1.27},
    ]
    
    print("🚀 Testing batch abandon scoring...")
    start_total = time.time()
    
    results = batch_process_fincas(test_fincas, max_workers=3)
    
    total_time = time.time() - start_total
    successful = sum(1 for r in results.values() if r["success"])
    
    print(f"\n📊 BATCH RESULTS:")
    print(f"✅ Successful: {successful}/{len(test_fincas)}")
    print(f"⏱️  Total time: {total_time:.1f}s")
    print(f"📈 Average per finca: {total_time/len(test_fincas):.1f}s")
    
    if successful > 0:
        avg_duration = sum(r["duration"] for r in results.values() if r["success"]) / successful
        print(f"📈 Average successful duration: {avg_duration:.1f}s")
        
        # Estimate for 600 fincas
        estimated_600 = (avg_duration * 600) / 60  # minutes
        print(f"🎯 Estimated time for 600 fincas: {estimated_600:.1f} minutes")
