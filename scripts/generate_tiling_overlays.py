#!/usr/bin/env python3
"""
Generate vehicle detection overlays using tiling approach
Compare with previous results for visual QA
"""

import os
import sys
import json
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2

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
        print(f"Error downloading image: {e}")
        return False

def draw_detections(image: Image.Image, detections: list, color: tuple = (255, 0, 0), thickness: int = 3):
    """Draw bounding boxes on image"""
    draw = ImageDraw.Draw(image)
    
    for detection in detections:
        bbox = detection['bbox']
        confidence = detection['confidence']
        class_name = detection['class']
        
        # Draw rectangle
        draw.rectangle(bbox, outline=color, width=thickness)
        
        # Draw label
        label = f"{class_name} {confidence:.2f}"
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Get text size
        bbox_text = draw.textbbox((0, 0), label, font=font)
        text_width = bbox_text[2] - bbox_text[0]
        text_height = bbox_text[3] - bbox_text[1]
        
        # Draw background rectangle for text
        text_x = bbox[0]
        text_y = bbox[1] - text_height - 5
        draw.rectangle([text_x, text_y, text_x + text_width, text_y + text_height], 
                      fill=color)
        
        # Draw text
        draw.text((text_x, text_y), label, fill=(255, 255, 255), font=font)

def generate_tiling_overlay(finca_id: str, lat: float, lon: float, 
                          tile_size: int = 1024, overlap: float = 0.3) -> dict:
    """Generate overlay using tiling approach"""
    
    # Build URL (same as previous overlays)
    url = build_mapbox_url(lat, lon, zoom=21, width=1280, height=1280)
    
    # Create output directory
    output_dir = ROOT / 'data' / 'overlays' / 'tiling_test'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download original image
    original_path = output_dir / f"{finca_id}_original.jpg"
    if not download_image(url, original_path):
        return None
    
    # Load image
    original_image = Image.open(original_path)
    print(f"  Original image: {original_image.size}")
    
    # Resize to 2560x2560 for better tiling (same as test script)
    original_image = original_image.resize((2560, 2560), Image.Resampling.LANCZOS)
    print(f"  Resized to: {original_image.size}")
    
    # Initialize detector
    detector = YOLOVehicleDetector()
    
    # Test 1: Original image detection
    print(f"  Testing original image...")
    original_result = detector.detect_vehicles_from_url(url)
    original_detections = original_result.get('detections', [])
    print(f"    Original: {len(original_detections)} vehicles")
    
    # Test 2: Tiling approach
    print(f"  Testing tiling approach...")
    
    # Import SAHI
    try:
        from sahi.slicing import slice_image
    except ImportError:
        print("SAHI not installed. Installing...")
        os.system("pip install sahi")
        from sahi.slicing import slice_image
    
    # Slice image
    slices = slice_image(
        image=np.array(original_image),
        slice_height=tile_size,
        slice_width=tile_size,
        overlap_height_ratio=overlap,
        overlap_width_ratio=overlap
    )
    
    print(f"    Created {len(slices)} tiles of {tile_size}x{tile_size}")
    
    # Process tiles
    all_tile_detections = []
    tiles_dir = output_dir / f"{finca_id}_tiles"
    tiles_dir.mkdir(exist_ok=True)
    
    for i, slice_obj in enumerate(slices):
        # Save tile
        tile_path = tiles_dir / f"tile_{i:03d}.jpg"
        tile_image = Image.fromarray(slice_obj['image'])
        tile_image.save(str(tile_path))
        
        # Detect on tile
        tile_result = detector.detect_vehicles_from_path(str(tile_path))
        tile_detections = tile_result.get('detections', [])
        
        if tile_detections:
            print(f"    Tile {i}: {len(tile_detections)} vehicles")
            
            # Adjust coordinates to original image
            slice_bbox = slice_obj['bbox']
            for detection in tile_detections:
                # Adjust bbox coordinates
                bbox = detection['bbox']
                adjusted_bbox = [
                    bbox[0] + slice_bbox[0],  # x1
                    bbox[1] + slice_bbox[1],  # y1
                    bbox[2] + slice_bbox[0],  # x2
                    bbox[3] + slice_bbox[1]   # y2
                ]
                detection['bbox'] = adjusted_bbox
                all_tile_detections.append(detection)
    
    print(f"    Tiles total: {len(all_tile_detections)} vehicles")
    
    # Create overlays
    # Original overlay
    original_overlay = original_image.copy()
    draw_detections(original_overlay, original_detections, color=(255, 0, 0), thickness=5)
    original_overlay_path = output_dir / f"{finca_id}_original_overlay.jpg"
    original_overlay.save(original_overlay_path)
    
    # Tiling overlay
    tiling_overlay = original_image.copy()
    draw_detections(tiling_overlay, all_tile_detections, color=(0, 255, 0), thickness=5)
    tiling_overlay_path = output_dir / f"{finca_id}_tiling_overlay.jpg"
    tiling_overlay.save(tiling_overlay_path)
    
    # Combined overlay
    combined_overlay = original_image.copy()
    draw_detections(combined_overlay, original_detections, color=(255, 0, 0), thickness=5)
    draw_detections(combined_overlay, all_tile_detections, color=(0, 255, 0), thickness=3)
    combined_overlay_path = output_dir / f"{finca_id}_combined_overlay.jpg"
    combined_overlay.save(combined_overlay_path)
    
    return {
        'finca_id': finca_id,
        'original_detections': len(original_detections),
        'tile_detections': len(all_tile_detections),
        'improvement': len(all_tile_detections) - len(original_detections),
        'num_tiles': len(slices),
        'files': {
            'original': str(original_overlay_path),
            'tiling': str(tiling_overlay_path),
            'combined': str(combined_overlay_path)
        }
    }

def main():
    print("🚀 Generating Tiling Overlays")
    print("=" * 50)
    
    # Load fincas with known vehicles (from previous tests)
    test_fincas = [
        {'id': 'finca_00002', 'lat': 38.939295555878665, 'lon': 1.2367587116397556},  # Had 1 car
        {'id': 'finca_00004', 'lat': 38.98716280051603, 'lon': 1.294956620839063},    # Had 1 car
        {'id': 'finca_00009', 'lat': 38.939295555878665, 'lon': 1.2367587116397556},  # Test case
        {'id': 'finca_00010', 'lat': 38.98716280051603, 'lon': 1.294956620839063},    # Test case
        {'id': 'finca_00015', 'lat': 38.939295555878665, 'lon': 1.2367587116397556},  # Test case
    ]
    
    results = []
    
    for finca in test_fincas:
        print(f"\nTesting {finca['id']}...")
        result = generate_tiling_overlay(
            finca['id'], 
            finca['lat'], 
            finca['lon'],
            tile_size=1024,  # Larger tiles for better detection
            overlap=0.3
        )
        
        if result:
            results.append(result)
            print(f"✅ {finca['id']}: {result['original_detections']} → {result['tile_detections']} (+{result['improvement']})")
        else:
            print(f"❌ {finca['id']}: Failed")
    
    # Summary
    print(f"\n📊 Tiling Overlay Results")
    print("=" * 50)
    
    total_original = sum(r['original_detections'] for r in results)
    total_tiles = sum(r['tile_detections'] for r in results)
    total_improvement = sum(r['improvement'] for r in results)
    
    print(f"Original detections: {total_original}")
    print(f"Tiling detections: {total_tiles}")
    improvement_pct = total_improvement/total_original*100 if total_original > 0 else 0
    print(f"Improvement: {total_improvement} (+{improvement_pct:.1f}%)")
    
    print(f"\n📁 Overlays saved in: {ROOT / 'data' / 'overlays' / 'tiling_test'}")
    print("Files:")
    print("  - *_original_overlay.jpg: Original detection (red)")
    print("  - *_tiling_overlay.jpg: Tiling detection (green)")
    print("  - *_combined_overlay.jpg: Both overlays combined")
    
    # Save results
    results_file = ROOT / 'data' / 'overlays' / 'tiling_test' / 'results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Results saved to: {results_file}")

if __name__ == "__main__":
    main()
