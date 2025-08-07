import ee
import os
from dotenv import load_dotenv

def initialize_gee():
    """Initialize Google Earth Engine with service account."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Initialize Earth Engine
        credentials = ee.ServiceAccountCredentials(
            email=None,  # Will be read from the JSON file
            key_file=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )
        ee.Initialize(credentials)
        
        # Test the connection by getting some data
        image = ee.Image('USGS/SRTMGL1_003')
        
        # Define Ibiza West bounds (approximate)
        ibiza_west = ee.Geometry.Rectangle([1.2, 38.8, 1.4, 39.0])
        
        # Get the mean elevation for the area
        mean = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=ibiza_west,
            scale=30
        ).get('elevation').getInfo()
        
        print(f"Successfully connected to Earth Engine!")
        print(f"Mean elevation in Ibiza West: {mean} meters")
        return True
        
    except Exception as e:
        print(f"Error initializing Earth Engine: {str(e)}")
        return False

if __name__ == "__main__":
    initialize_gee()