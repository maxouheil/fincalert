#!/usr/bin/env python3
"""
Batch NDVI Scoring for all 600 fincas
Run this script once to pre-compute all abandon scores
"""
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from satellite.ndvi_score_only import batch_process_fincas

def load_all_fincas() -> list:
    """Load all fincas from the GeoJSON file"""
    fincas_file = Path(__file__).parent.parent / "data" / "fincas_extreme_west.geojson"
    
    if not fincas_file.exists():
        raise FileNotFoundError(f"Fincas file not found: {fincas_file}")
    
    with open(fincas_file) as f:
        data = json.load(f)
    
    # Extract coordinates
    finca_coords = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        
        # Use lat/lon from properties if available, otherwise calculate centroid
        if "lat" in props and "lon" in props:
            lat, lon = props["lat"], props["lon"]
        else:
            # Calculate centroid from polygon coordinates
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])
            if coords and len(coords) > 0:
                # For polygon, take first ring and calculate centroid
                ring = coords[0]
                lat = sum(pt[1] for pt in ring) / len(ring)
                lon = sum(pt[0] for pt in ring) / len(ring)
            else:
                continue
        
        finca_coords.append({
            "id": props.get("id", f"finca_{len(finca_coords):05d}"),
            "lat": lat,
            "lon": lon,
            "surface_m2": props.get("surface_estimee_m2", 0)
        })
    
    return finca_coords

def main():
    print("🎯 BATCH NDVI ABANDON SCORING")
    print("=" * 50)
    
    # Load all fincas
    print("📂 Loading fincas data...")
    try:
        all_fincas = load_all_fincas()
        print(f"✅ Loaded {len(all_fincas)} fincas")
    except Exception as e:
        print(f"❌ Failed to load fincas: {e}")
        return
    
    # Process in batches
    batch_size = 50  # Process 50 at a time
    max_workers = 10  # Parallel workers
    
    output_dir = Path(__file__).parent.parent / "data" / "abandon_scores"
    output_dir.mkdir(exist_ok=True)
    
    print(f"🚀 Processing {len(all_fincas)} fincas in batches of {batch_size}")
    print(f"⚡ Using {max_workers} parallel workers")
    
    all_results = {}
    
    for i in range(0, len(all_fincas), batch_size):
        batch = all_fincas[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_fincas) + batch_size - 1) // batch_size
        
        print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} fincas)")
        
        try:
            batch_results = batch_process_fincas(batch, max_workers=max_workers)
            all_results.update(batch_results)
            
            # Save intermediate results
            batch_file = output_dir / f"batch_{batch_num:03d}.json"
            with open(batch_file, 'w') as f:
                json.dump(batch_results, f, indent=2)
            
            successful = sum(1 for r in batch_results.values() if r["success"])
            print(f"✅ Batch {batch_num} complete: {successful}/{len(batch)} successful")
            
        except Exception as e:
            print(f"❌ Batch {batch_num} failed: {e}")
    
    # Save final consolidated results
    final_file = output_dir / "all_abandon_scores.json"
    with open(final_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    # Statistics
    total_successful = sum(1 for r in all_results.values() if r["success"])
    total_failed = len(all_results) - total_successful
    
    if total_successful > 0:
        avg_duration = sum(r["duration"] for r in all_results.values() if r["success"]) / total_successful
        
        # Analyze abandon scores
        abandon_scores = [
            r["result"]["summary"]["abandon_score"] 
            for r in all_results.values() 
            if r["success"]
        ]
        
        if abandon_scores:
            avg_score = sum(abandon_scores) / len(abandon_scores)
            high_abandon = sum(1 for s in abandon_scores if s >= 70)
            
            print(f"\n📊 FINAL RESULTS:")
            print(f"✅ Successful: {total_successful}")
            print(f"❌ Failed: {total_failed}")
            print(f"⏱️  Average duration: {avg_duration:.1f}s per finca")
            print(f"📈 Average abandon score: {avg_score:.1f}")
            print(f"🚨 High abandon risk (≥70): {high_abandon} fincas")
            print(f"💾 Results saved to: {final_file}")

if __name__ == "__main__":
    main()
