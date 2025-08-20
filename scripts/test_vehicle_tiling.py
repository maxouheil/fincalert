#!/usr/bin/env python3
"""
Test vehicle detection with tiling approach using SAHI.
"""

import os
import sys
import json
from pathlib import Path
import requests
from PIL import Image
import numpy as np

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from backend.detection.yolo_vehicle_detector import YOLOVehicleDetector
from scripts.batch_vehicle_detection_all import build_mapbox_url

def download_image(url: str, save_path: Path) -> bool:
    """Download image from URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"  Error downloading image: {e}")
        return False

def test_tiling_on_finca(finca_id: str, lat: float, lon: float, tile_size: int = 512, overlap: float = 0.3):
    """Test tiling approach on a single finca"""
    
    print(f"Testing tiling on {finca_id}...")
    
    # Download original image
    url = build_mapbox_url(lon, lat, zoom=21, width=1280, height=1280)
    image_path = ROOT / "data" / "test_results" / "tiling_test" / f"{finca_id}_original.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not download_image(url, image_path):
        return None
    
    # Load image with SAHI
    try:
        from sahi.utils.cv import read_image
        from sahi.slicing import slice_image
        
        image = read_image(str(image_path))
        
        # Slice image
        slices = slice_image(
            image=image,
            slice_height=tile_size,
            slice_width=tile_size,
            overlap_height_ratio=overlap,
            overlap_width_ratio=overlap
        )
        
        print(f"  Original image: {image.shape}")
        print(f"  Created {len(slices)} tiles of {tile_size}x{tile_size}")
        
        # Save tiles for inspection
        tiles_dir = image_path.parent / f"{finca_id}_tiles"
        tiles_dir.mkdir(exist_ok=True)
        
        for i, slice_obj in enumerate(slices):
            tile_path = tiles_dir / f"tile_{i:03d}.jpg"
            # Convert numpy array to PIL Image
            tile_image = Image.fromarray(slice_obj['image'])
            tile_image.save(str(tile_path))
        
        # Test detection on original vs tiles
        detector = YOLOVehicleDetector()
        
        # Test on original image
        print(f"  Testing on original image...")
        original_result = detector.detect_vehicles_from_url(url)
        print(f"    Original: {original_result.get('vehicle_count', 0)} vehicles")
        
        # Test on tiles
        print(f"  Testing on tiles...")
        tile_results = []
        total_tile_vehicles = 0
        
        for i, slice_obj in enumerate(slices):
            # Save tile temporarily
            temp_tile_path = tiles_dir / f"temp_tile_{i}.jpg"
            # Convert numpy array to PIL Image
            tile_image = Image.fromarray(slice_obj['image'])
            tile_image.save(str(temp_tile_path))
            
            # Detect on tile
            tile_result = detector.detect_vehicles_from_path(str(temp_tile_path))
            tile_results.append(tile_result)
            
            if tile_result.get('vehicle_detected', False):
                vehicle_count = tile_result.get('vehicle_count', 0)
                total_tile_vehicles += vehicle_count
                print(f"    Tile {i}: {vehicle_count} vehicles")
            
            # Clean up temp file
            temp_tile_path.unlink()
        
        print(f"    Tiles total: {total_tile_vehicles} vehicles")
        
        return {
            'finca_id': finca_id,
            'original_vehicles': original_result.get('vehicle_count', 0),
            'tile_vehicles': total_tile_vehicles,
            'num_tiles': len(slices),
            'improvement': total_tile_vehicles - original_result.get('vehicle_count', 0)
        }
        
    except ImportError as e:
        print(f"  Error importing SAHI: {e}")
        return None
    except Exception as e:
        print(f"  Error in tiling: {e}")
        return None

def main():
    """Test tiling on a few fincas"""
    
    print("🚀 Testing Vehicle Detection with Tiling")
    print("=" * 50)
    
    # Load fincas
    geojson_path = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    test_fincas = features[:5]  # Test on first 5 fincas
    
    results = []
    
    for finca in test_fincas:
        props = finca.get('properties', {})
        finca_id = props.get('id')
        lat = props.get('lat')
        lon = props.get('lon')
        
        if not finca_id or lat is None or lon is None:
            continue
            
        result = test_tiling_on_finca(
            finca_id, 
            lat, 
            lon,
            tile_size=512,
            overlap=0.3
        )
        if result:
            results.append(result)
        print()
    
    # Summary
    print("📊 Tiling Test Results")
    print("=" * 30)
    
    total_original = sum(r['original_vehicles'] for r in results)
    total_tiles = sum(r['tile_vehicles'] for r in results)
    total_improvement = sum(r['improvement'] for r in results)
    
    print(f"Original detections: {total_original}")
    print(f"Tile detections: {total_tiles}")
    improvement_pct = total_improvement/total_original*100 if total_original > 0 else 0
    print(f"Improvement: {total_improvement} (+{improvement_pct:.1f}%)")
    
    for result in results:
        print(f"  {result['finca_id']}: {result['original_vehicles']} → {result['tile_vehicles']} (+{result['improvement']})")

if __name__ == "__main__":
    main()
