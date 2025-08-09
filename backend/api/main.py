from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import re

import requests

from ..satellite.sentinel import initialize_gee, get_sentinel_imagery
from ..satellite.ndvi_timeseries_optimized import compute_and_store_optimized as ndvi_compute, get_progress
from pathlib import Path
from ..detection.building_detector import BuildingDetector
from ..detection.yolo_pool_detector import YOLOPoolDetector
from ..detection.yolo_mobile_detector import YOLOMobileDetector
from ..detection.demo_detector import DemoDetector

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize GEE in best-effort mode; don't block the API if it fails
try:
    initialize_gee()
except Exception:
    pass
detector = BuildingDetector()

# Initialize YOLO detectors (lazy loading pour éviter ralentissement startup)
pool_detector = None
mobile_detector = None
demo_detector = DemoDetector()  # Toujours disponible

def get_pool_detector():
    """Lazy loading du détecteur piscines"""
    global pool_detector
    if pool_detector is None:
        pool_detector = YOLOPoolDetector()
    return pool_detector

def get_mobile_detector():
    """Lazy loading du détecteur objets mobiles"""
    global mobile_detector
    if mobile_detector is None:
        mobile_detector = YOLOMobileDetector()
    return mobile_detector

class Finca(BaseModel):
    id: str
    lat: float
    lon: float
    surface_estimee_m2: float
    distance_plus_proche_voisin_m: float
    qualifiee_finca: bool

@app.get("/")
async def root():
    return {"message": "Fincalert API"}

@app.get("/api/fincas", response_model=List[Finca])
async def get_fincas():
    """Get all detected fincas."""
    try:
        # For MVP, we'll read from a static JSON file
        data_path = os.path.join(os.path.dirname(__file__), "../../data/fincas.json")
        with open(data_path, 'r') as f:
            fincas = json.load(f)
        return fincas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/satellite/{finca_id}")
async def get_satellite_image(finca_id: str):
    """Get satellite imagery for a specific finca."""
    try:
        # Get finca coordinates from data
        data_path = os.path.join(os.path.dirname(__file__), "../../data/fincas.json")
        with open(data_path, 'r') as f:
            fincas = json.load(f)
        
        finca = next((f for f in fincas if f["id"] == finca_id), None)
        if not finca:
            raise HTTPException(status_code=404, detail="Finca not found")
        
        # Define bounds around finca (500m buffer)
        bounds = {
            'west': finca['lon'] - 0.005,
            'south': finca['lat'] - 0.005,
            'east': finca['lon'] + 0.005,
            'north': finca['lat'] + 0.005
        }
        
        # Get satellite imagery
        image = get_sentinel_imagery(bounds, "2023-01-01", "2023-12-31")
        
        return {"tile_url": image}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Lazy thumbnail caching (Mapbox static images) ---

def _sanitize_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value.strip())


def _get_cache_dir() -> str:
    # Store under project data cache
    here = os.path.dirname(__file__)
    cache_dir = os.path.normpath(os.path.join(here, "../../data/cache"))
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


@app.get("/api/thumbnail/{finca_id}")
async def get_thumbnail(
    finca_id: str,
    lon: float,
    lat: float,
    width: int = 280,
    height: int = 200,
    scale: int = 2,
):
    """Return a cached Mapbox static image for a finca (and cache on first request)."""
    try:
        token = os.getenv("MAPBOX_TOKEN") or os.getenv("REACT_APP_MAPBOX_TOKEN")
        if not token:
            raise HTTPException(status_code=500, detail="MAPBOX_TOKEN not configured")

        safe_id = _sanitize_id(finca_id)
        suffix = "@2x" if scale and int(scale) >= 2 else ""
        filename = f"{safe_id}{suffix}.jpg"
        cache_dir = _get_cache_dir()
        out_path = os.path.join(cache_dir, filename)

        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return FileResponse(out_path, media_type="image/jpeg")

        # Build Mapbox static image URL
        zoom = 18.5
        base = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},{zoom},0/{width}x{height}"
        url = f"{base}{'@2x' if suffix else ''}?access_token={token}"

        # Download and store
        resp = requests.get(url, stream=True, timeout=30)
        if not resp.ok:
            raise HTTPException(status_code=502, detail=f"Mapbox error: {resp.status_code}")
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return FileResponse(out_path, media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- NDVI 6-month timeseries and status ---

@app.get("/api/ndvi/{finca_id}")
async def get_ndvi_summary(finca_id: str, lat: float, lon: float):
    try:
        # Cache path: data/ndvi/{id}/summary.json
        here = os.path.dirname(__file__)
        ndvi_dir = os.path.normpath(os.path.join(here, "../../data/ndvi", finca_id))
        os.makedirs(ndvi_dir, exist_ok=True)
        out_path = Path(ndvi_dir) / "summary.json"

        # If cached and fresh (< 7 days), return cached
        if out_path.exists():
            mtime = out_path.stat().st_mtime
            import time
            if time.time() - mtime < 7 * 24 * 3600:
                return JSONResponse(json.loads(out_path.read_text()))

        # Compute real NDVI using Google Earth Engine (may take 30-60s per finca)
        print(f"Computing NDVI for {finca_id} at ({lat}, {lon})")
        ndvi_compute(finca_id, lat, lon, Path(ndvi_dir))
        return JSONResponse(json.loads(out_path.read_text()))
    except Exception as e:
        print(f"NDVI computation failed for {finca_id}: {e}")
        raise HTTPException(status_code=503, detail=f"NDVI unavailable: {e}")


@app.get("/api/ndvi/progress/{finca_id}")
async def get_ndvi_progress(finca_id: str):
    """Get real-time progress for NDVI computation"""
    progress_data = get_progress(finca_id)
    return JSONResponse(progress_data)


@app.get("/api/abandon/{finca_id}")
async def get_abandon_data(finca_id: str):
    """Get pre-computed abandon analysis data for a finca"""
    try:
        # Load the pre-computed analysis data
        analysis_dir = Path(__file__).parent.parent.parent / "data" / "abandon_analysis_FULL"
        
        # Find the latest analysis file
        analysis_files = list(analysis_dir.glob("fincas_abandon_analysis_FULL_*.json"))
        if not analysis_files:
            raise HTTPException(status_code=404, detail="No abandon analysis data found")
        
        latest_file = sorted(analysis_files)[-1]
        
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        # Find the specific finca
        finca_data = None
        for finca in data["fincas"]:
            if finca["finca_id"] == finca_id:
                finca_data = finca
                break
        
        if not finca_data:
            raise HTTPException(status_code=404, detail=f"Finca {finca_id} not found in analysis")
        
        if finca_data["status"] != "success":
            raise HTTPException(status_code=503, detail=f"Analysis failed: {finca_data.get('error_message', 'Unknown error')}")
        
        # Return structured data for frontend
        return {
            "finca_id": finca_id,
            "abandon_score": finca_data["abandon_score"],
            "activity_status": finca_data["activity_status"],
            "std_deviation": finca_data["std_deviation"],
            "median_ndvi": finca_data["median_ndvi"],
            "valid_periods": finca_data["valid_periods"],
            "ndvi_timeseries": finca_data["ndvi_timeseries"],
            "processing_duration_s": finca_data["processing_duration_s"],
            "processed_at": finca_data["processed_at"]
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Abandon analysis data not found")
    except Exception as e:
        print(f"Error loading abandon data for {finca_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading abandon data: {e}")


@app.get("/api/ndvi/thumb/{finca_id}/{name}")
async def get_ndvi_thumb(finca_id: str, name: str, hq: bool = False):
    try:
        here = os.path.dirname(__file__)
        ndvi_path = os.path.normpath(os.path.join(here, f"../../data/ndvi/{finca_id}/{name}"))
        
        # If high quality requested and summary exists, generate HQ version
        if hq:
            return await get_hq_thumbnail(finca_id, name)
        
        # Return real thumbnail if it exists
        if os.path.isfile(ndvi_path):
            return FileResponse(ndvi_path, media_type="image/png")
        
        # Return 404 for missing thumbnails - frontend should handle gracefully
        raise HTTPException(status_code=404, detail="Thumbnail not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_hq_thumbnail(finca_id: str, name: str):
    """Generate high-quality thumbnail on-demand using cached NDVI data."""
    try:
        import ee
        from ..satellite.ndvi_timeseries import _ensure_gee_initialized, _mask_s2_clouds
        from io import BytesIO
        from starlette.responses import StreamingResponse
        import requests
        
        if not _ensure_gee_initialized():
            raise HTTPException(status_code=503, detail="GEE not available")
        
        # Parse thumbnail index from name (e.g., "w_05.png" -> 5)
        import re
        match = re.search(r'w_(\d+)\.png', name)
        if not match:
            raise HTTPException(status_code=400, detail="Invalid thumbnail name")
        
        thumb_idx = int(match.group(1))
        
        # Load summary to get period info
        here = os.path.dirname(__file__)
        summary_path = os.path.normpath(os.path.join(here, f"../../data/ndvi/{finca_id}/summary.json"))
        
        if not os.path.isfile(summary_path):
            raise HTTPException(status_code=404, detail="NDVI data not found")
        
        with open(summary_path) as f:
            import json
            summary_data = json.load(f)
        
        series = summary_data.get('series', [])
        if thumb_idx >= len(series) or not series[thumb_idx].get('start'):
            raise HTTPException(status_code=404, detail="Period not found")
        
        period = series[thumb_idx]
        start_date = period['start']
        end_date = period['end']
        
        # Try to get coordinates from summary data or use default
        summary = summary_data.get('summary', {})
        lat = summary.get('lat', 38.9269)  # Will add lat/lon to summary in future
        lon = summary.get('lon', 1.2735)   # For now use default Ibiza coordinates
        
        # Generate high-quality image using GEE
        pt = ee.Geometry.Point([lon, lat])
        roi = pt.buffer(25)  # 25m buffer
        
        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR")
            .filterBounds(roi)
            .filterDate(start_date, end_date)
            .map(_mask_s2_clouds)
        )
        
        if collection.size().getInfo() == 0:
            raise HTTPException(status_code=404, detail="No satellite data for period")
        
        median = collection.median()
        vis = median.visualize(bands=["B4", "B3", "B2"], min=0, max=3000, gamma=1.4)
        
        # Generate 360x240 high-quality image
        url = vis.getThumbURL({
            "region": roi.coordinates().getInfo(),
            "dimensions": "360x240",
            "format": "png",
            "crs": "EPSG:3857"
        })
        
        # Fetch and return the image
        response = requests.get(url, timeout=30)
        if not response.ok:
            raise HTTPException(status_code=503, detail="Failed to generate thumbnail")
        
        return StreamingResponse(
            BytesIO(response.content),
            media_type="image/png",
            headers={"Cache-Control": "max-age=86400"}  # Cache for 24 hours
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thumbnail generation failed: {str(e)}")


# ========== NOUVELLES ROUTES YOLO DETECTION ==========

@app.get("/api/detection/pools/{finca_id}")
async def detect_pools(finca_id: str, use_mapbox: bool = True, demo: bool = True):
    """
    Détecte piscines pour une finca donnée
    Args:
        finca_id: ID de la finca
        use_mapbox: Utiliser Mapbox (True) ou Sentinel-2 (False)
    """
    try:
        # Charger données finca
        here = os.path.dirname(__file__)
        geojson_path = os.path.normpath(os.path.join(here, "../../frontend/public/data/fincas_with_abandon_scores.geojson"))
        
        if not os.path.exists(geojson_path):
            raise HTTPException(status_code=404, detail="Finca data not found")
        
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        
        # Trouver la finca
        finca = None
        for feature in geojson_data.get('features', []):
            if feature.get('properties', {}).get('id') == finca_id:
                finca = feature['properties']
                break
        
        if not finca:
            raise HTTPException(status_code=404, detail=f"Finca {finca_id} not found")
        
        lat, lon = finca['lat'], finca['lon']
        
        if demo:
            # Mode démo avec résultats cohérents
            result = demo_detector.detect_pools_demo(finca_id, lat, lon)
        else:
            # Mode production YOLO
            # Générer URL image haute résolution
            if use_mapbox:
                token = os.getenv("MAPBOX_TOKEN") or os.getenv("REACT_APP_MAPBOX_TOKEN")
                if not token:
                    raise HTTPException(status_code=503, detail="Mapbox token not configured")
                
                # Image haute résolution pour détection
                image_url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},19,0/640x480@2x?access_token={token}"
            else:
                # TODO: Utiliser Sentinel-2 haute résolution si disponible
                raise HTTPException(status_code=501, detail="Sentinel-2 pool detection not yet implemented")
            
            # Détection piscines
            detector = get_pool_detector()
            result = detector.detect_pools_from_url(image_url, finca_id)
        
        return {
            "finca_id": finca_id,
            "coordinates": {"lat": lat, "lon": lon},
            "image_source": "mapbox" if use_mapbox else "sentinel2",
            "detection_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pool detection failed: {str(e)}")


@app.get("/api/detection/mobility/{finca_id}")
async def detect_mobility(finca_id: str, months_gap: int = 6, demo: bool = True):
    """
    Détecte changements objets mobiles pour une finca
    Args:
        finca_id: ID de la finca  
        months_gap: Écart temporel en mois pour comparaison
    """
    try:
        # Charger données finca
        here = os.path.dirname(__file__)
        geojson_path = os.path.normpath(os.path.join(here, "../../frontend/public/data/fincas_with_abandon_scores.geojson"))
        
        if not os.path.exists(geojson_path):
            raise HTTPException(status_code=404, detail="Finca data not found")
        
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        
        # Trouver la finca
        finca = None
        for feature in geojson_data.get('features', []):
            if feature.get('properties', {}).get('id') == finca_id:
                finca = feature['properties']
                break
        
        if not finca:
            raise HTTPException(status_code=404, detail=f"Finca {finca_id} not found")
        
        lat, lon = finca['lat'], finca['lon']
        
        if demo:
            # Mode démo avec résultats cohérents
            result = demo_detector.detect_mobility_demo(finca_id, lat, lon, months_gap)
        else:
            # Mode production YOLO
            # Générer URLs pour deux périodes différentes
            token = os.getenv("MAPBOX_TOKEN") or os.getenv("REACT_APP_MAPBOX_TOKEN")
            if not token:
                raise HTTPException(status_code=503, detail="Mapbox token not configured")
            
            # Images haute résolution (on simule deux dates différentes pour l'instant)
            # TODO: Intégrer avec vraies dates historiques de NDVI
            base_url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},19,0/640x480@2x?access_token={token}"
            
            # Pour l'instant, même image (en production, utiliser dates historiques)
            image_url_t1 = base_url  # Image "ancienne"
            image_url_t2 = base_url  # Image "récente"
            
            # Détection mobilité
            detector = get_mobile_detector()
            result = detector.detect_mobility_from_urls(
                image_url_t1, image_url_t2, finca_id, months_gap
            )
        
        return {
            "finca_id": finca_id,
            "coordinates": {"lat": lat, "lon": lon},
            "time_gap_months": months_gap,
            "detection_result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mobility detection failed: {str(e)}")


@app.get("/api/detection/visual-analysis/{finca_id}")
async def get_visual_analysis(finca_id: str, demo: bool = True):
    """
    Analyse visuelle complète (piscines + mobilité) pour une finca
    """
    try:
        if demo:
            # Mode démo - récupération directe des coordonnées
            here = os.path.dirname(__file__)
            geojson_path = os.path.normpath(os.path.join(here, "../../frontend/public/data/fincas_with_abandon_scores.geojson"))
            
            if not os.path.exists(geojson_path):
                raise HTTPException(status_code=404, detail="Finca data not found")
            
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
            
            # Trouver la finca
            finca = None
            for feature in geojson_data.get('features', []):
                if feature.get('properties', {}).get('id') == finca_id:
                    finca = feature['properties']
                    break
            
            if not finca:
                raise HTTPException(status_code=404, detail=f"Finca {finca_id} not found")
            
            lat, lon = finca['lat'], finca['lon']
            return demo_detector.get_visual_analysis_demo(finca_id, lat, lon)
        else:
            # Mode production - exécuter détections en parallèle
            import asyncio
            
            pool_task = detect_pools(finca_id, use_mapbox=True, demo=False)
            mobility_task = detect_mobility(finca_id, months_gap=6, demo=False)
            
            pool_result, mobility_result = await asyncio.gather(
                pool_task, mobility_task, return_exceptions=True
            )
            
            # Gérer erreurs éventuelles
            if isinstance(pool_result, Exception):
                pool_result = {"error": str(pool_result)}
            if isinstance(mobility_result, Exception):
                mobility_result = {"error": str(mobility_result)}
            
            return {
                "finca_id": finca_id,
                "pools": pool_result,
                "mobility": mobility_result,
                "summary": _generate_visual_summary(pool_result, mobility_result)
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual analysis failed: {str(e)}")


def _generate_visual_summary(pool_result: dict, mobility_result: dict) -> dict:
    """Génère résumé consolidé de l'analyse visuelle"""
    summary = {
        "activity_indicators": [],
        "visual_score": 0.0,
        "confidence": "low"
    }
    
    try:
        # Analyse piscines
        if "detection_result" in pool_result and pool_result["detection_result"].get("pool_detected"):
            pool_state = pool_result["detection_result"]["best_pool"]["state"]
            if pool_state == "blue":
                summary["activity_indicators"].append("🏊 Piscine entretenue")
                summary["visual_score"] += 0.3
            elif pool_state == "green":
                summary["activity_indicators"].append("🏊 Piscine sale")
                summary["visual_score"] += 0.1
            else:
                summary["activity_indicators"].append("🏊 Piscine détectée")
                summary["visual_score"] += 0.2
        
        # Analyse mobilité
        if "detection_result" in mobility_result:
            mobility_score = mobility_result["detection_result"].get("mobility_score", 0)
            mobility_level = mobility_result["detection_result"].get("mobility_level", "low")
            
            if mobility_level == "high":
                summary["activity_indicators"].append("🚗 Activité élevée")
                summary["visual_score"] += 0.4
            elif mobility_level == "medium":
                summary["activity_indicators"].append("🚗 Activité modérée")
                summary["visual_score"] += 0.2
            
            summary["visual_score"] += mobility_score * 0.3
        
        # Classification confiance
        if summary["visual_score"] >= 0.6:
            summary["confidence"] = "high"
        elif summary["visual_score"] >= 0.3:
            summary["confidence"] = "medium"
        else:
            summary["confidence"] = "low"
        
        summary["visual_score"] = min(1.0, summary["visual_score"])
        
    except Exception as e:
        summary["error"] = f"Summary generation failed: {str(e)}"
    
    return summary