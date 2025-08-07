import ee
import os
from pathlib import Path

def initialize_gee():
    """Initialize Google Earth Engine with service account."""
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent
        
        # Service account key file path
        key_file = project_root / 'gee-service-account.json'
        print(f"Looking for credentials file at: {key_file}")
        
        if not key_file.exists():
            raise ValueError(f"Credentials file not found at: {key_file}")
        
        # Initialize Earth Engine with service account
        credentials = ee.ServiceAccountCredentials(
            email=None,  # Will be read from the JSON file
            key_file=str(key_file)
        )
        ee.Initialize(credentials)
        
        # Test the connection by getting Sentinel-2 data for Ibiza West
        ibiza_west = ee.Geometry.Rectangle([1.2, 38.8, 1.4, 39.0])
        
        # Get a Sentinel-2 image collection
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(ibiza_west) \
            .filterDate('2023-01-01', '2023-12-31') \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        # Get the size of the collection
        count = collection.size().getInfo()
        
        print(f"Successfully connected to Earth Engine!")
        print(f"Found {count} Sentinel-2 images for Ibiza West in 2023")
        return True
        
    except Exception as e:
        print(f"Error initializing Earth Engine: {str(e)}")
        return False

if __name__ == "__main__":
    initialize_gee()