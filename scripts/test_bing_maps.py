#!/usr/bin/env python3
"""
Test Bing Maps API for high-resolution satellite images.

Bing Maps provides satellite imagery with 0.5m/pixel resolution.
Free tier: 125,000 requests/month
"""

import os
import sys
import requests
import json
from pathlib import Path
from typing import Optional

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def get_bing_maps_url(lat: float, lon: float, zoom: int = 19, size: str = "1024,1024") -> str:
    """
    Generate Bing Maps URL for satellite imagery
    
    Args:
        lat: Latitude
        lon: Longitude  
        zoom: Zoom level (19 = 0.5m/pixel)
        size: Image size (width,height)
    
    Returns:
        Bing Maps URL
    """
    api_key = os.getenv('BING_MAPS_API_KEY')
    if not api_key:
        raise RuntimeError('BING_MAPS_API_KEY not configured')
    
    # Bing Maps Static API
    base_url = "https://dev.virtualearth.net/REST/v1/Imagery/Map/Aerial"
    params = {
        'center': f"{lat},{lon}",
        'zoomLevel': zoom,
        'mapSize': size,
        'format': 'jpeg',
        'key': api_key
    }
    
    # Build URL
    url = f"{base_url}?center={params['center']}&zoomLevel={params['zoomLevel']}&mapSize={params['mapSize']}&format={params['format']}&key={params['key']}"
    
    return url


def download_bing_image(lat: float, lon: float, output_path: Path, zoom: int = 19) -> bool:
    """
    Download satellite image from Bing Maps
    
    Args:
        lat: Latitude
        lon: Longitude
        output_path: Output file path
        zoom: Zoom level
    
    Returns:
        True if successful, False otherwise
    """
    try:
        url = get_bing_maps_url(lat, lon, zoom)
        print(f"Downloading: {url}")
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            output_path.write_bytes(response.content)
            print(f"✅ Downloaded: {output_path}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False


def test_bing_maps():
    """Test Bing Maps with sample coordinates"""
    
    # Sample coordinates (Ibiza)
    test_coords = [
        (38.9087, 1.4324),  # Ibiza Town
        (38.9867, 1.2897),  # San Antonio
        (38.9667, 1.4333),  # Santa Eulalia
    ]
    
    output_dir = ROOT / 'data' / 'test_results' / 'bing_maps_test'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🛰️ Testing Bing Maps API for high-resolution satellite images")
    print(f"Output directory: {output_dir}")
    
    for i, (lat, lon) in enumerate(test_coords, 1):
        print(f"\n📍 Test {i}: {lat}, {lon}")
        
        # Test different zoom levels
        for zoom in [18, 19, 20]:
            output_path = output_dir / f"test_{i}_zoom_{zoom}.jpg"
            
            if download_bing_image(lat, lon, output_path, zoom):
                # Get file size
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"  Zoom {zoom}: {size_mb:.1f}MB")
            else:
                print(f"  Zoom {zoom}: Failed")
    
    print(f"\n💾 Images saved to: {output_dir}")


def compare_resolutions():
    """Compare different satellite image sources"""
    
    print("\n📊 Comparaison des résolutions satellite :")
    print("=" * 50)
    print("Source          | Résolution | Zoom | Qualité")
    print("=" * 50)
    print("Mapbox          | 0.5-1m     | 20-21| Moyenne")
    print("Bing Maps       | 0.5m       | 19   | Bonne")
    print("Google Earth    | 0.5m       | 19   | Bonne")
    print("Planet Labs     | 0.8-3m     | 18-19| Très bonne")
    print("Maxar/WorldView | 0.3m       | 20   | Exceptionnelle")
    print("Airbus/Pléiades | 0.5m       | 19   | Très bonne")
    print("=" * 50)


if __name__ == "__main__":
    compare_resolutions()
    
    # Check if API key is available
    if os.getenv('BING_MAPS_API_KEY'):
        test_bing_maps()
    else:
        print("\n⚠️  BING_MAPS_API_KEY not set")
        print("To test Bing Maps, get a free API key from:")
        print("https://www.bingmapsportal.com/")
        print("\nAlternative: Test with existing Mapbox images")
