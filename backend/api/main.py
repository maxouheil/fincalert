from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import os

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

# Initialize GEE and building detector
initialize_gee()
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