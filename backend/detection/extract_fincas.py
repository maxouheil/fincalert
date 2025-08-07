import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import requests
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import unary_union


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


@dataclass
class FincaCriteria:
    min_area_m2: float = 50.0
    max_area_m2: float = 150.0
    min_isolation_m: float = 15.0
    max_cluster_radius_m: float = 250.0
    max_density_in_radius: int = 6  # drop if more than this many neighbors within radius


def fetch_osm_buildings(bounds: Dict[str, float]) -> gpd.GeoDataFrame:
    """Fetch OSM building footprints within a bounding box.

    Returns GeoDataFrame in EPSG:4326 with Polygon/MultiPolygon geometries.
    """
    south = bounds["south"]
    west = bounds["west"]
    north = bounds["north"]
    east = bounds["east"]

    query = f"""
    [out:json][timeout:120];
    (
      way["building"]({south},{west},{north},{east});
      relation["building"]({south},{west},{north},{east});
    );
    out body geom;
    """
    resp = requests.post(OVERPASS_URL, data={"data": query})
    resp.raise_for_status()
    data = resp.json()

    features: List[Tuple[str, Polygon | MultiPolygon]] = []

    for el in data.get("elements", []):
        geom = el.get("geometry")
        if not geom:
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in geom]
        # Close polygon if not closed
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        try:
            polygon = Polygon(coords)
            if polygon.is_valid and not polygon.is_empty:
                features.append((str(el.get("id")), polygon))
        except Exception:
            continue

    if not features:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    gdf = gpd.GeoDataFrame(
        {"osm_id": [fid for fid, _ in features]},
        geometry=[geom for _, geom in features],
        crs="EPSG:4326",
    )
    return gdf


def filter_fincas(
    buildings_wgs84: gpd.GeoDataFrame, criteria: FincaCriteria
) -> gpd.GeoDataFrame:
    """Apply area, isolation, and density filters and return fincas GeoDataFrame."""
    if buildings_wgs84.empty:
        return buildings_wgs84

    # Project to metric CRS for Ibiza (UTM 31N)
    buildings = buildings_wgs84.to_crs(32631)

    # Area filter
    buildings["area_m2"] = buildings.geometry.area
    a = criteria
    buildings = buildings[(buildings["area_m2"] >= a.min_area_m2) & (buildings["area_m2"] <= a.max_area_m2)]
    if buildings.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    # Isolation filter (nearest neighbor distance)
    centroids = buildings.geometry.centroid
    coords = np.array([[p.x, p.y] for p in centroids])
    diff = coords[:, None, :] - coords[None, :, :]
    dists = np.hypot(diff[..., 0], diff[..., 1])
    np.fill_diagonal(dists, np.inf)
    min_nn = np.min(dists, axis=1)
    buildings["nearest_m"] = min_nn
    buildings = buildings[buildings["nearest_m"] >= a.min_isolation_m]
    if buildings.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    # Recompute distances after isolation filter so dimensions match
    centroids = buildings.geometry.centroid
    coords = np.array([[p.x, p.y] for p in centroids])
    diff = coords[:, None, :] - coords[None, :, :]
    dists = np.hypot(diff[..., 0], diff[..., 1])
    np.fill_diagonal(dists, np.inf)

    # Density filter: drop features with too many neighbors within radius
    within = (dists <= a.max_cluster_radius_m).astype(int)
    counts = within.sum(axis=1) - 1  # exclude self
    buildings["neighbors_in_radius"] = counts
    buildings = buildings[buildings["neighbors_in_radius"] <= a.max_density_in_radius]

    # Prepare final schema in WGS84
    out = buildings.to_crs(4326).copy()
    out["lat"] = out.geometry.centroid.y
    out["lon"] = out.geometry.centroid.x
    out.rename(
        columns={
            "nearest_m": "distance_plus_proche_voisin_m",
            "area_m2": "surface_estimee_m2",
        },
        inplace=True,
    )
    out["id"] = [f"finca_{i:05d}" for i in range(1, len(out) + 1)]
    out["qualifiee_finca"] = True
    return out[
        [
            "id",
            "lat",
            "lon",
            "surface_estimee_m2",
            "distance_plus_proche_voisin_m",
            "qualifiee_finca",
            "geometry",
        ]
    ]


def run_pipeline(
    bounds: Dict[str, float], criteria: Optional[FincaCriteria] = None, output_path: str = ""
) -> str:
    criteria = criteria or FincaCriteria()
    buildings = fetch_osm_buildings(bounds)
    fincas = filter_fincas(buildings, criteria)
    if not output_path:
        output_path = "data/fincas_extreme_west.geojson"
    fincas.to_file(output_path, driver="GeoJSON")
    return output_path


if __name__ == "__main__":
    # Extreme west of Ibiza (west of Sant Antoni) — same as exporter ROI
    bounds = {"west": 1.16, "south": 38.86, "east": 1.30, "north": 39.05}
    path = run_pipeline(bounds, FincaCriteria(min_isolation_m=15.0))
    print(f"Wrote {path}")

