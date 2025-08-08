import requests
import geopandas as gpd
from shapely.geometry import box, Point
import numpy as np

class BuildingDetector:
    def __init__(self):
        """Initialize the building detector with Microsoft Building Footprints."""
        self.min_area = 50  # minimum area in m²
        self.max_area = 150  # maximum area in m²
        self.min_isolation = 10  # minimum distance to nearest building in meters

    def fetch_buildings(self, bounds):
        """
        Fetch building footprints from Microsoft's API for the given bounds.
        
        Args:
            bounds (tuple): (min_lon, min_lat, max_lon, max_lat)
            
        Returns:
            GeoDataFrame: Buildings with their footprints and metadata
        """
        # Microsoft Building Footprints API endpoint
        url = f"https://atlas.microsoft.com/wfs/datasets/microsoft/building-footprints/collections/address/items"
        
        # Create GeoJSON polygon from bounds
        bbox = box(*bounds)
        
        # TODO: Implement actual API call when credentials are available
        # For MVP, we'll create sample data
        return self._create_sample_data(bounds)

    def filter_fincas(self, buildings_gdf):
        """
        Filter buildings to identify potential fincas based on criteria.
        
        Args:
            buildings_gdf (GeoDataFrame): Buildings with their footprints
            
        Returns:
            GeoDataFrame: Filtered fincas meeting all criteria
        """
        # Calculate building areas
        buildings_gdf['area'] = buildings_gdf.geometry.area
        
        # Filter by area
        area_filter = (buildings_gdf['area'] >= self.min_area) & \
                     (buildings_gdf['area'] <= self.max_area)
        
        potential_fincas = buildings_gdf[area_filter].copy()
        
        # Calculate distances to nearest buildings
        potential_fincas['nearest_distance'] = self._calculate_nearest_distances(potential_fincas)
        
        # Filter by isolation
        isolation_filter = potential_fincas['nearest_distance'] >= self.min_isolation
        
        return potential_fincas[isolation_filter]

    def _calculate_nearest_distances(self, gdf):
        """Calculate distance to nearest building for each building."""
        distances = []
        for idx, row in gdf.iterrows():
            other_buildings = gdf[gdf.index != idx]
            if len(other_buildings) > 0:
                distances.append(
                    min(row.geometry.distance(other.geometry) 
                        for _, other in other_buildings.iterrows())
                )
            else:
                distances.append(float('inf'))
        return distances

    def _create_sample_data(self, bounds):
        """Create sample building data for testing."""
        min_lon, min_lat, max_lon, max_lat = bounds
        
        # Create random buildings within bounds
        n_buildings = 50
        geometries = []
        
        for _ in range(n_buildings):
            lon = np.random.uniform(min_lon, max_lon)
            lat = np.random.uniform(min_lat, max_lat)
            area = np.random.uniform(30, 200)
            
            # Create a simple square building
            point = Point(lon, lat)
            buffer_size = np.sqrt(area) / 2
            geometry = point.buffer(buffer_size)
            geometries.append(geometry)
        
        return gpd.GeoDataFrame(
            geometry=geometries,
            crs="EPSG:4326"
        )