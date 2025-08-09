#!/usr/bin/env python3
"""
Test automatique - 5 fincas seulement
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from satellite.ndvi_score_only import batch_process_fincas

def load_test_fincas() -> list:
    """Load 5 test fincas"""
    fincas_file = Path(__file__).parent.parent / "data" / "fincas_extreme_west.geojson"
    
    with open(fincas_file) as f:
        data = json.load(f)
    
    # Take first 5 fincas
    finca_coords = []
    for i, feature in enumerate(data["features"][:5]):
        props = feature["properties"]
        
        if "lat" in props and "lon" in props:
            lat, lon = props["lat"], props["lon"]
        else:
            geom = feature["geometry"]
            coords = geom["coordinates"][0]
            lat = sum(pt[1] for pt in coords) / len(coords)
            lon = sum(pt[0] for pt in coords) / len(coords)
        
        finca_coords.append({
            "id": props.get("id", f"finca_{i+1:05d}"),
            "lat": lat,
            "lon": lon,
            "surface_m2": props.get("surface_estimee_m2", 0)
        })
    
    return finca_coords

def main():
    print("🧪 TEST AUTOMATIQUE - 5 FINCAS")
    print("=" * 40)
    
    # Load test fincas
    test_fincas = load_test_fincas()
    print(f"📍 Fincas à tester:")
    for finca in test_fincas:
        print(f"  - {finca['id']}: {finca['lat']:.4f}, {finca['lon']:.4f}")
    
    print(f"\n🚀 Démarrage du calcul...")
    start_time = time.time()
    
    try:
        # Process with 3 workers for test
        results = batch_process_fincas(test_fincas, max_workers=3)
        
        total_time = time.time() - start_time
        successful = sum(1 for r in results.values() if r["success"])
        
        print(f"\n📊 RÉSULTATS:")
        print(f"✅ Réussis: {successful}/{len(test_fincas)}")
        print(f"⏱️  Temps total: {total_time:.1f}s")
        
        if successful > 0:
            avg_time = sum(r["duration"] for r in results.values() if r["success"]) / successful
            print(f"📈 Temps moyen: {avg_time:.1f}s par finca")
        
        print(f"\n🎯 DÉTAILS PAR FINCA:")
        for finca_id, result in results.items():
            if result["success"]:
                summary = result["result"]["summary"]
                score = summary["abandon_score"]
                status = summary["status"]
                std = summary["std"]
                print(f"  ✅ {finca_id}: Score {score:.1f} | Status: {status} | Std: {std:.3f} | {result['duration']:.1f}s")
            else:
                print(f"  ❌ {finca_id}: {result['error']}")
        
        # Estimation pour 631 fincas
        if successful > 0:
            est_time_631 = (avg_time * 631) / 60  # minutes
            print(f"\n📈 ESTIMATION POUR 631 FINCAS:")
            print(f"⏱️  Temps estimé: {est_time_631:.1f} minutes")
            print(f"⚡ Avec 10 workers: {est_time_631/2:.1f} minutes")
        
        # Save test results
        output_dir = Path(__file__).parent.parent / "data" / "test_results"
        output_dir.mkdir(exist_ok=True)
        
        test_file = output_dir / f"test_5_fincas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(test_file, 'w') as f:
            json.dump({
                "test_metadata": {
                    "total_fincas": len(test_fincas),
                    "successful": successful,
                    "total_duration_s": total_time,
                    "avg_duration_s": avg_time if successful > 0 else 0,
                    "tested_at": datetime.utcnow().isoformat()
                },
                "results": results
            }, f, indent=2)
        
        print(f"\n💾 Résultats sauvés: {test_file}")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")

if __name__ == "__main__":
    main()
