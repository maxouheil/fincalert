#!/usr/bin/env python3
"""
Enhanced Batch NDVI Scoring - Stockage complet en base
Stocke: NDVI 12 périodes + écart-type + score + métadonnées
"""
import json
import sys
import time
from datetime import datetime
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
            "surface_m2": props.get("surface_estimee_m2", 0),
            "neighborhood": props.get("neighborhood", "unknown")
        })
    
    return finca_coords

def create_database_record(finca_data: dict, ndvi_result: dict) -> dict:
    """
    Créer l'enregistrement complet pour la base de données
    """
    if not ndvi_result.get("success", False):
        return {
            "finca_id": finca_data["id"],
            "lat": finca_data["lat"],
            "lon": finca_data["lon"],
            "surface_m2": finca_data["surface_m2"],
            "neighborhood": finca_data["neighborhood"],
            "status": "error",
            "error_message": ndvi_result.get("error", "Unknown error"),
            "processed_at": datetime.utcnow().isoformat(),
            "processing_duration_s": ndvi_result.get("duration", 0)
        }
    
    result_data = ndvi_result["result"]
    series = result_data["series"]
    summary = result_data["summary"]
    
    # Extraire les 12 valeurs NDVI
    ndvi_12_periods = []
    for i, period in enumerate(series):
        ndvi_12_periods.append({
            "period_index": i + 1,
            "start_date": period["start"],
            "end_date": period["end"],
            "ndvi_value": period["ndvi"],
            "cloud_percentage": period["cloud_pct"]
        })
    
    return {
        # Métadonnées finca
        "finca_id": finca_data["id"],
        "lat": finca_data["lat"],
        "lon": finca_data["lon"],
        "surface_m2": finca_data["surface_m2"],
        "neighborhood": finca_data["neighborhood"],
        
        # Traitement
        "processed_at": datetime.utcnow().isoformat(),
        "processing_duration_s": ndvi_result["duration"],
        "status": "success",
        
        # NDVI 12 périodes (DEMANDÉ)
        "ndvi_timeseries": ndvi_12_periods,
        
        # Métriques statistiques (DEMANDÉ)
        "median_ndvi": summary["median"],
        "std_deviation": summary["std"],  # ÉCART-TYPE DEMANDÉ
        "dips_count": summary["dips"],
        "green_persistence": summary["green_persistence"],
        "valid_periods": summary["valid"],
        
        # Classification et score (DEMANDÉ)
        "activity_status": summary["status"],  # active/potential/inactive
        "abandon_score": summary["abandon_score"],  # SCORE DEMANDÉ 0-100
        
        # Métadonnées analyse
        "analysis_window_days": summary["window_days"],
        "analysis_months": summary["months"],
        "algorithm_version": "v1.0"
    }

def save_to_database(records: list, output_dir: Path):
    """
    Sauvegarder tous les enregistrements dans différents formats
    """
    output_dir.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. JSON complet (toutes les données)
    full_json = output_dir / f"fincas_abandon_analysis_{timestamp}.json"
    with open(full_json, 'w') as f:
        json.dump({
            "metadata": {
                "total_fincas": len(records),
                "successful": len([r for r in records if r["status"] == "success"]),
                "failed": len([r for r in records if r["status"] == "error"]),
                "generated_at": datetime.utcnow().isoformat(),
                "algorithm_version": "v1.0"
            },
            "fincas": records
        }, f, indent=2)
    
    # 2. CSV simplifié (scores + données principales)
    csv_file = output_dir / f"fincas_abandon_scores_{timestamp}.csv"
    with open(csv_file, 'w') as f:
        f.write("finca_id,lat,lon,surface_m2,neighborhood,abandon_score,activity_status,std_deviation,median_ndvi,valid_periods,processing_duration_s\n")
        
        for record in records:
            if record["status"] == "success":
                f.write(f"{record['finca_id']},{record['lat']},{record['lon']},{record['surface_m2']},{record['neighborhood']},{record['abandon_score']},{record['activity_status']},{record['std_deviation']},{record['median_ndvi']},{record['valid_periods']},{record['processing_duration_s']}\n")
    
    # 3. Résumé statistique
    summary_file = output_dir / f"analysis_summary_{timestamp}.json"
    successful_records = [r for r in records if r["status"] == "success"]
    
    if successful_records:
        abandon_scores = [r["abandon_score"] for r in successful_records]
        summary_stats = {
            "total_analyzed": len(successful_records),
            "abandon_score_stats": {
                "min": min(abandon_scores),
                "max": max(abandon_scores),
                "average": sum(abandon_scores) / len(abandon_scores),
                "median": sorted(abandon_scores)[len(abandon_scores) // 2]
            },
            "status_distribution": {
                "active": len([r for r in successful_records if r["activity_status"] == "active"]),
                "potential": len([r for r in successful_records if r["activity_status"] == "potential"]),
                "inactive": len([r for r in successful_records if r["activity_status"] == "inactive"]),
                "unknown": len([r for r in successful_records if r["activity_status"] == "unknown"])
            },
            "high_abandon_risk": len([r for r in successful_records if r["abandon_score"] >= 70]),
            "processing_stats": {
                "total_duration_s": sum(r["processing_duration_s"] for r in successful_records),
                "avg_duration_s": sum(r["processing_duration_s"] for r in successful_records) / len(successful_records)
            }
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_stats, f, indent=2)
    
    return full_json, csv_file, summary_file

def main():
    print("🎯 ENHANCED BATCH NDVI ABANDON SCORING")
    print("=" * 60)
    print("Stockage: NDVI 12 périodes + écart-type + score")
    
    # Load all fincas
    print("\n📂 Loading fincas data...")
    try:
        all_fincas = load_all_fincas()
        print(f"✅ Loaded {len(all_fincas)} fincas")
    except Exception as e:
        print(f"❌ Failed to load fincas: {e}")
        return
    
    # Option: Tester avec un petit échantillon d'abord
    test_mode = input(f"\n🔍 Test mode? (y/N) - Process only first 5 fincas: ").lower() == 'y'
    
    if test_mode:
        all_fincas = all_fincas[:5]
        print(f"🧪 TEST MODE: Processing {len(all_fincas)} fincas")
    
    # Process in batches
    batch_size = 20  # Smaller batches for better monitoring
    max_workers = 8   # Conservative for stability
    
    output_dir = Path(__file__).parent.parent / "data" / "abandon_analysis"
    
    print(f"\n🚀 Processing {len(all_fincas)} fincas in batches of {batch_size}")
    print(f"⚡ Using {max_workers} parallel workers")
    print(f"💾 Output directory: {output_dir}")
    
    all_database_records = []
    total_start_time = time.time()
    
    for i in range(0, len(all_fincas), batch_size):
        batch = all_fincas[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_fincas) + batch_size - 1) // batch_size
        
        print(f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} fincas)")
        
        try:
            batch_results = batch_process_fincas(batch, max_workers=max_workers)
            
            # Transformer en enregistrements de base de données
            for finca in batch:
                result = batch_results.get(finca["id"], {"success": False, "error": "No result"})
                db_record = create_database_record(finca, result)
                all_database_records.append(db_record)
            
            successful = sum(1 for r in batch_results.values() if r["success"])
            print(f"✅ Batch {batch_num} complete: {successful}/{len(batch)} successful")
            
        except Exception as e:
            print(f"❌ Batch {batch_num} failed: {e}")
            # Ajouter des enregistrements d'erreur
            for finca in batch:
                error_record = create_database_record(finca, {"success": False, "error": str(e), "duration": 0})
                all_database_records.append(error_record)
    
    # Sauvegarder les résultats
    print(f"\n💾 Saving results to database...")
    total_duration = time.time() - total_start_time
    
    try:
        json_file, csv_file, summary_file = save_to_database(all_database_records, output_dir)
        
        # Statistiques finales
        total_processed = len(all_database_records)
        successful = len([r for r in all_database_records if r["status"] == "success"])
        failed = total_processed - successful
        
        print(f"\n📊 FINAL RESULTS:")
        print(f"✅ Successfully processed: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"⏱️  Total duration: {total_duration/60:.1f} minutes")
        
        if successful > 0:
            avg_duration = sum(r["processing_duration_s"] for r in all_database_records if r["status"] == "success") / successful
            abandon_scores = [r["abandon_score"] for r in all_database_records if r["status"] == "success"]
            high_risk = len([s for s in abandon_scores if s >= 70])
            
            print(f"📈 Average processing time: {avg_duration:.1f}s per finca")
            print(f"🚨 High abandon risk (≥70): {high_risk} fincas")
            print(f"📈 Average abandon score: {sum(abandon_scores)/len(abandon_scores):.1f}")
        
        print(f"\n💾 Files created:")
        print(f"📄 Complete data: {json_file}")
        print(f"📊 CSV scores: {csv_file}")
        print(f"📈 Summary: {summary_file}")
        
    except Exception as e:
        print(f"❌ Failed to save results: {e}")

if __name__ == "__main__":
    main()
