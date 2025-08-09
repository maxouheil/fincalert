#!/usr/bin/env python3
"""
LANCEMENT COMPLET - 631 FINCAS
Production ready with monitoring
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
    """Load all 631 fincas"""
    fincas_file = Path(__file__).parent.parent / "data" / "fincas_extreme_west.geojson"
    
    with open(fincas_file) as f:
        data = json.load(f)
    
    finca_coords = []
    for feature in data["features"]:
        props = feature["properties"]
        
        if "lat" in props and "lon" in props:
            lat, lon = props["lat"], props["lon"]
        else:
            geom = feature["geometry"]
            coords = geom["coordinates"][0]
            lat = sum(pt[1] for pt in coords) / len(coords)
            lon = sum(pt[0] for pt in coords) / len(coords)
        
        finca_coords.append({
            "id": props.get("id", f"finca_{len(finca_coords):05d}"),
            "lat": lat,
            "lon": lon,
            "surface_m2": props.get("surface_estimee_m2", 0),
            "neighborhood": props.get("neighborhood", "unknown")
        })
    
    return finca_coords

def create_database_record(finca_data: dict, ndvi_result: dict) -> dict:
    """Create complete database record"""
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
    
    # Extract 12 NDVI values
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
        # Finca metadata
        "finca_id": finca_data["id"],
        "lat": finca_data["lat"],
        "lon": finca_data["lon"],
        "surface_m2": finca_data["surface_m2"],
        "neighborhood": finca_data["neighborhood"],
        
        # Processing
        "processed_at": datetime.utcnow().isoformat(),
        "processing_duration_s": ndvi_result["duration"],
        "status": "success",
        
        # ⭐ NDVI 12 periods (REQUESTED)
        "ndvi_timeseries": ndvi_12_periods,
        
        # ⭐ Statistical metrics (REQUESTED)
        "median_ndvi": summary["median"],
        "std_deviation": summary["std"],  # STANDARD DEVIATION REQUESTED
        "dips_count": summary["dips"],
        "green_persistence": summary["green_persistence"],
        "valid_periods": summary["valid"],
        
        # ⭐ Classification and score (REQUESTED)
        "activity_status": summary["status"],
        "abandon_score": summary["abandon_score"],  # SCORE REQUESTED 0-100
        
        # Analysis metadata
        "analysis_window_days": summary["window_days"],
        "analysis_months": summary["months"],
        "algorithm_version": "v1.0"
    }

def save_results(records: list, output_dir: Path):
    """Save all results in multiple formats"""
    output_dir.mkdir(exist_ok=True, parents=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Complete JSON
    full_json = output_dir / f"fincas_abandon_analysis_FULL_{timestamp}.json"
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
    
    # 2. CSV simplified
    csv_file = output_dir / f"fincas_abandon_scores_FULL_{timestamp}.csv"
    with open(csv_file, 'w') as f:
        f.write("finca_id,lat,lon,surface_m2,neighborhood,abandon_score,activity_status,std_deviation,median_ndvi,valid_periods,processing_duration_s\\n")
        
        for record in records:
            if record["status"] == "success":
                f.write(f"{record['finca_id']},{record['lat']},{record['lon']},{record['surface_m2']},{record['neighborhood']},{record['abandon_score']},{record['activity_status']},{record['std_deviation']},{record['median_ndvi']},{record['valid_periods']},{record['processing_duration_s']}\\n")
    
    # 3. Summary statistics
    summary_file = output_dir / f"analysis_summary_FULL_{timestamp}.json"
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
    print("🚀 FINCALERT - ANALYSE COMPLÈTE 631 FINCAS")
    print("=" * 70)
    print("🎯 Objectif: Calculer scores d'abandon avec NDVI + écart-type")
    print("⏱️  Durée estimée: ~30 minutes")
    print("💾 Stockage: JSON + CSV + Résumé statistique")
    
    # Load all fincas
    print("\\n📂 Chargement des données...")
    try:
        all_fincas = load_all_fincas()
        print(f"✅ Chargé: {len(all_fincas)} fincas")
    except Exception as e:
        print(f"❌ Erreur chargement: {e}")
        return
    
    # Configuration
    batch_size = 25  # Batches plus petits pour monitoring
    max_workers = 10  # Maximum parallélisme
    
    output_dir = Path(__file__).parent.parent / "data" / "abandon_analysis_FULL"
    
    print(f"\\n🚀 DÉMARRAGE PRODUCTION:")
    print(f"📊 Total fincas: {len(all_fincas)}")
    print(f"📦 Taille batch: {batch_size}")
    print(f"⚡ Workers parallèles: {max_workers}")
    print(f"💾 Répertoire sortie: {output_dir}")
    
    # Confirmation avant lancement
    print(f"\\n⚠️  ATTENTION: Processus de production complet!")
    print(f"Coût GEE estimé: ~${len(all_fincas) * 0.02:.2f}")
    
    all_database_records = []
    total_start_time = time.time()
    
    for i in range(0, len(all_fincas), batch_size):
        batch = all_fincas[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(all_fincas) + batch_size - 1) // batch_size
        
        print(f"\\n📦 BATCH {batch_num}/{total_batches} ({len(batch)} fincas)")
        print(f"⏱️  Temps écoulé: {(time.time() - total_start_time)/60:.1f}min")
        
        batch_start = time.time()
        
        try:
            batch_results = batch_process_fincas(batch, max_workers=max_workers)
            
            # Transform to database records
            for finca in batch:
                result = batch_results.get(finca["id"], {"success": False, "error": "No result"})
                db_record = create_database_record(finca, result)
                all_database_records.append(db_record)
            
            successful = sum(1 for r in batch_results.values() if r["success"])
            batch_time = time.time() - batch_start
            
            print(f"✅ Batch {batch_num}: {successful}/{len(batch)} réussis en {batch_time:.1f}s")
            
            # Progress statistics
            total_processed = len(all_database_records)
            total_successful = len([r for r in all_database_records if r["status"] == "success"])
            progress_pct = (batch_num / total_batches) * 100
            
            print(f"📈 Progrès global: {progress_pct:.1f}% | {total_successful}/{total_processed} réussis")
            
            # ETA calculation
            if batch_num > 1:
                elapsed = time.time() - total_start_time
                eta_total = (elapsed / batch_num) * total_batches
                eta_remaining = eta_total - elapsed
                print(f"⏱️  ETA: {eta_remaining/60:.1f}min restantes")
            
        except Exception as e:
            print(f"❌ Batch {batch_num} échoué: {e}")
            # Add error records
            for finca in batch:
                error_record = create_database_record(finca, {"success": False, "error": str(e), "duration": 0})
                all_database_records.append(error_record)
    
    # Final save
    print(f"\\n💾 SAUVEGARDE FINALE...")
    total_duration = time.time() - total_start_time
    
    try:
        json_file, csv_file, summary_file = save_results(all_database_records, output_dir)
        
        # Final statistics
        total_processed = len(all_database_records)
        successful = len([r for r in all_database_records if r["status"] == "success"])
        failed = total_processed - successful
        
        print(f"\\n🎉 ANALYSE COMPLÈTE TERMINÉE!")
        print("=" * 50)
        print(f"✅ Réussis: {successful}")
        print(f"❌ Échecs: {failed}")
        print(f"📊 Taux succès: {(successful/total_processed)*100:.1f}%")
        print(f"⏱️  Durée totale: {total_duration/60:.1f} minutes")
        
        if successful > 0:
            avg_duration = sum(r["processing_duration_s"] for r in all_database_records if r["status"] == "success") / successful
            abandon_scores = [r["abandon_score"] for r in all_database_records if r["status"] == "success"]
            
            print(f"📈 Temps moyen: {avg_duration:.1f}s par finca")
            print(f"📊 Score abandon moyen: {sum(abandon_scores)/len(abandon_scores):.1f}")
            
            # Risk analysis
            high_risk = len([s for s in abandon_scores if s >= 70])
            medium_risk = len([s for s in abandon_scores if 40 <= s < 70])
            low_risk = len([s for s in abandon_scores if s < 40])
            
            print(f"\\n🚨 ANALYSE DES RISQUES:")
            print(f"🔴 Risque élevé (≥70): {high_risk} fincas")
            print(f"🟡 Risque moyen (40-69): {medium_risk} fincas")
            print(f"🟢 Risque faible (<40): {low_risk} fincas")
        
        print(f"\\n💾 FICHIERS GÉNÉRÉS:")
        print(f"📄 Données complètes: {json_file}")
        print(f"📊 Scores CSV: {csv_file}")
        print(f"📈 Résumé: {summary_file}")
        
        print(f"\\n🎯 MISSION ACCOMPLIE!")
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")

if __name__ == "__main__":
    main()
