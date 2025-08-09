#!/usr/bin/env python3
"""
Test script to identify NDVI computation bottlenecks
"""
import time
import ee
from pathlib import Path
import requests
import json

# Try to initialize GEE
try:
    project_root = Path(__file__).parent.parent.parent
    key_file = project_root / 'gee-service-account.json'
    credentials = ee.ServiceAccountCredentials(email=None, key_file=str(key_file))
    ee.Initialize(credentials)
    print("✅ GEE initialized")
except Exception as e:
    print(f"❌ GEE initialization failed: {e}")
    exit(1)

def test_gee_operations():
    """Test individual GEE operations to find bottlenecks"""
    lat, lon = 38.92, 1.28
    buffer_m = 25.0
    
    print("\n🔍 Testing GEE operations...")
    
    # 1. Basic geometry operations
    start = time.time()
    pt = ee.Geometry.Point([lon, lat])
    roi = pt.buffer(buffer_m)
    roi_coords = roi.coordinates().getInfo()
    print(f"⏱️  ROI creation + coordinates: {time.time() - start:.2f}s")
    
    # 2. Collection filtering
    start = time.time()
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR")
        .filterBounds(roi)
        .filterDate("2025-07-01", "2025-07-15")  # Recent 2-week window
    )
    count = col.size().getInfo()
    print(f"⏱️  Collection filter + count: {time.time() - start:.2f}s (found {count} images)")
    
    if count == 0:
        print("❌ No images found, skipping further tests")
        return
    
    # 3. Cloud masking + median
    start = time.time()
    def mask_clouds(img):
        scl = img.select("SCL")
        mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
        return img.updateMask(mask)
    
    masked_col = col.map(mask_clouds)
    median = masked_col.median()
    print(f"⏱️  Cloud masking + median: {time.time() - start:.2f}s")
    
    # 4. NDVI calculation
    start = time.time()
    ndvi = median.normalizedDifference(["B8", "B4"]).rename("NDVI")
    print(f"⏱️  NDVI calculation: {time.time() - start:.2f}s")
    
    # 5. Statistics computation (THE BOTTLENECK?)
    start = time.time()
    ndvi_mean = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=20,
        bestEffort=True
    ).get('NDVI').getInfo()
    print(f"⏱️  NDVI stats (.getInfo()): {time.time() - start:.2f}s")
    
    # 6. Thumbnail generation (ANOTHER BOTTLENECK?)
    start = time.time()
    try:
        vis = median.visualize(bands=["B4", "B3", "B2"], min=0, max=2000)
        url = vis.getThumbURL({
            "region": roi_coords,
            "dimensions": "180x120",
            "format": "png"
        })
        r = requests.get(url, timeout=5)
        if r.ok:
            print(f"⏱️  Thumbnail generation: {time.time() - start:.2f}s (success)")
        else:
            print(f"⏱️  Thumbnail generation: {time.time() - start:.2f}s (failed: {r.status_code})")
    except Exception as e:
        print(f"⏱️  Thumbnail generation: {time.time() - start:.2f}s (error: {e})")

def test_simple_vs_complex():
    """Compare simple vs complex operations"""
    lat, lon = 38.92, 1.28
    roi = ee.Geometry.Point([lon, lat]).buffer(25.0)
    
    print("\n🚀 Testing operation complexity...")
    
    # Simple operation
    start = time.time()
    simple_test = ee.Number(1).add(1).getInfo()
    print(f"⏱️  Simple operation: {time.time() - start:.2f}s")
    
    # Medium complexity
    start = time.time()
    col = ee.ImageCollection("COPERNICUS/S2_SR").filterBounds(roi).limit(1)
    count = col.size().getInfo()
    print(f"⏱️  Collection query: {time.time() - start:.2f}s")
    
    # High complexity (typical NDVI operation)
    start = time.time()
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR")
        .filterBounds(roi)
        .filterDate("2025-07-01", "2025-07-15")
    )
    if col.size().getInfo() > 0:
        ndvi = col.median().normalizedDifference(["B8", "B4"])
        result = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=50,  # Faster scale
            bestEffort=True
        ).getInfo()
        print(f"⏱️  Full NDVI pipeline: {time.time() - start:.2f}s")

if __name__ == "__main__":
    print("🎯 NDVI Bottleneck Analysis")
    print("=" * 40)
    
    test_simple_vs_complex()
    test_gee_operations()
    
    print("\n📊 ANALYSIS COMPLETE")
    print("Check which operations take the most time!")
