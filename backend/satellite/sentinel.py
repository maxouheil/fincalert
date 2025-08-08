import ee
import os
from dotenv import load_dotenv

load_dotenv()

def initialize_gee():
    """Best-effort initialize Google Earth Engine; no-op if not configured."""
    try:
        service_account = os.getenv('GEE_SERVICE_ACCOUNT')
        private_key = os.getenv('GEE_PRIVATE_KEY')
        # If credentials are not configured, skip initialization
        if not service_account or not private_key:
            return
        credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
        ee.Initialize(credentials)
    except Exception:
        # Do not fail the app if GEE is unavailable
        return

def get_sentinel_imagery(bounds, start_date, end_date):
    """
    Fetch Sentinel-2 imagery for the specified region and date range.
    
    Args:
        bounds (dict): GeoJSON-style bounds for Western Ibiza
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format
    
    Returns:
        ee.Image: Median composite of Sentinel-2 imagery
    """
    # Convert bounds to ee.Geometry
    aoi = ee.Geometry.Rectangle(bounds)
    
    # Get Sentinel-2 collection
    s2 = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterBounds(aoi) \
        .filterDate(start_date, end_date) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    
    # Create median composite
    composite = s2.median()
    
    return composite

def create_image_tiles(composite, bounds, zoom_level=15):
    """
    Create map tiles from Sentinel-2 composite for the specified region.
    
    Args:
        composite (ee.Image): Sentinel-2 composite image
        bounds (dict): GeoJSON-style bounds
        zoom_level (int): Zoom level for tiles
    
    Returns:
        str: URL for map tiles
    """
    # Define visualization parameters
    vis_params = {
        'min': 0,
        'max': 3000,
        'bands': ['B4', 'B3', 'B2']
    }
    
    # Create map tiles
    map_id = composite.getMapId(vis_params)
    
    return map_id['tile_fetcher'].url_format