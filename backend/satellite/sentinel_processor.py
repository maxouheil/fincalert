import ee
import geemap
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class SentinelProcessor:
    def __init__(self, bounds: dict | None = None, grid_size_deg: float = 0.02):
        """Initialize the Sentinel-2 data processor.

        Args:
            bounds: Optional dict with 'west', 'south', 'east', 'north'.
            grid_size_deg: Grid size in degrees (~0.02 ~= 2km).
        """
        self.initialize_gee()

        # Default Ibiza West bounds
        default_bounds = {
            'west': 1.2,
            'south': 38.8,
            'east': 1.4,
            'north': 39.0,
        }

        self.bounds = bounds or default_bounds
        self.grid_size = grid_size_deg  # approximately 2km in degrees
        
    def initialize_gee(self):
        """Initialize Google Earth Engine with service account, falling back to project root json file."""
        try:
            # Try env var, else default to project root json
            env_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not env_path:
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                env_path = os.path.join(project_root, 'gee-service-account.json')

            credentials = ee.ServiceAccountCredentials(
                email=None,
                key_file=env_path
            )
            ee.Initialize(credentials)
        except Exception as e:
            raise Exception(f"Failed to initialize Earth Engine: {str(e)}")
    
    def create_processing_grid(self) -> List[Dict]:
        """Create a grid of 2x2 km tiles for processing."""
        tiles = []
        
        for lat in range(
            int(self.bounds['south'] * 100),
            int(self.bounds['north'] * 100),
            int(self.grid_size * 100)
        ):
            for lon in range(
                int(self.bounds['west'] * 100),
                int(self.bounds['east'] * 100),
                int(self.grid_size * 100)
            ):
                tile = {
                    'west': lon / 100,
                    'south': lat / 100,
                    'east': (lon / 100) + self.grid_size,
                    'north': (lat / 100) + self.grid_size
                }
                tiles.append(tile)
        
        return tiles
    
    def get_sentinel_imagery(
        self,
        bounds: Dict[str, float],
        start_date: str,
        end_date: str
    ) -> ee.Image:
        """
        Get Sentinel-2 imagery for a specific tile and date range.
        
        Args:
            bounds: Dictionary with west, south, east, north coordinates
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            ee.Image: Processed Sentinel-2 image
        """
        # Create geometry
        geometry = ee.Geometry.Rectangle([
            bounds['west'],
            bounds['south'],
            bounds['east'],
            bounds['north']
        ])
        
        # Get Sentinel-2 collection
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(geometry) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        # Create cloud-free composite
        composite = collection.median()
        
        # Select bands for building detection
        bands = ['B2', 'B3', 'B4', 'B8']  # Blue, Green, Red, NIR
        return composite.select(bands)
    
    def process_tile(
        self,
        tile: Dict[str, float],
        start_date: str = None,
        end_date: str = None
    ) -> ee.Image:
        """
        Process a single tile to prepare for building detection.
        
        Args:
            tile: Dictionary with tile bounds
            start_date: Optional start date (defaults to 6 months ago)
            end_date: Optional end date (defaults to current date)
            
        Returns:
            ee.Image: Processed image ready for building detection
        """
        # Set default dates if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get Sentinel imagery
        image = self.get_sentinel_imagery(tile, start_date, end_date)
        
        # Add NDVI for vegetation masking
        ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        image = image.addBands(ndvi)
        
        # Create building likelihood score
        # This is a simple example - you might want to use more sophisticated methods
        building_score = image.expression(
            '(1 - NDVI) * (NIR / RED)',
            {
                'NDVI': image.select('NDVI'),
                'NIR': image.select('B8'),
                'RED': image.select('B4')
            }
        ).rename('building_score')
        
        return image.addBands(building_score)
    
    def export_tile_to_geotiff(
        self,
        image: ee.Image,
        tile: Dict[str, float],
        output_path: str
    ):
        """
        Export a processed tile to GeoTIFF format.
        
        Args:
            image: Processed ee.Image
            tile: Dictionary with tile bounds
            output_path: Path to save the GeoTIFF
        """
        try:
            # Get the URL for downloading
            url = image.getDownloadURL({
                'scale': 10,  # 10m resolution
                'region': ee.Geometry.Rectangle([
                    tile['west'],
                    tile['south'],
                    tile['east'],
                    tile['north']
                ]),
                'format': 'GEO_TIFF'
            })
            
            # Download the file
            import requests
            response = requests.get(url)
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
        except Exception as e:
            raise Exception(f"Failed to export tile: {str(e)}")