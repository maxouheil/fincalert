from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import re

import requests

from ..satellite.sentinel import initialize_gee, get_sentinel_imagery
from ..detection.building_detector import BuildingDetector

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