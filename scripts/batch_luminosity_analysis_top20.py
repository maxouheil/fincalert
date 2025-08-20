#!/usr/bin/env python3
"""
🌙 Batch Analysis - Top 20 Fincas
Analyse la luminosité nocturne des 20 premières fincas avec données VIIRS DNB réelles
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.satellite.nocturnal_luminosity import NocturnalLuminosityAnalyzer


def load_fincas_data():
    """Charge les données des fincas depuis le GeoJSON"""
    geojson_path = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    
    if not geojson_path.exists():
        raise FileNotFoundError(f"Fichier GeoJSON non trouvé: {geojson_path}")
    
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"📊 Total fincas disponibles: {len(features)}")
    
    return features


def analyze_top20_fincas():
    """Analyse les 20 premières fincas"""
    print("🌙 ANALYSE LUMINOSITÉ NOCTURNE - TOP 20 FINCAS")
    print("=" * 60)
    
    # Charger les données
    features = load_fincas_data()
    
    # Prendre les 20 premières fincas
    top20_features = features[:20]
    print(f"🧪 Analyse des {len(top20_features)} premières fincas")
    
    # Initialiser l'analyseur
    analyzer = NocturnalLuminosityAnalyzer()
    results = []
    
    # Timestamp pour les fichiers de sortie
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Créer le dossier de sortie
    output_dir = ROOT / 'data' / 'luminosity_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    
    for i, feature in enumerate(top20_features, 1):
        props = feature.get('properties', {})
        finca_id = props.get('id')
        lat = props.get('lat')
        lon = props.get('lon')
        
        if not all([finca_id, lat, lon]):
            print(f"⚠️  [{i}/20] Données manquantes pour {finca_id}")
            continue
        
        print(f"\n📍 [{i}/20] {finca_id}")
        print(f"   Coordonnées: {lat:.6f}, {lon:.6f}")
        
        try:
            # Analyse avec vraies données VIIRS (12 mois)
            result = analyzer.analyze_finca_luminosity(
                finca_id, lat, lon, months=12, demo=False
            )
            
            results.append(result)
            
            if result['status'] == 'success':
                score = result['score']
                reason = result['reason'][:50] + "..." if len(result['reason']) > 50 else result['reason']
                print(f"   ✅ Score: {score}/5 - {reason}")
                
                # Afficher quelques métriques clés
                metrics = result['metrics']
                print(f"   📈 Luminosité: {metrics['mean_luminosity']:.3f} (niveau: {metrics['luminosity_level']})")
                print(f"   📅 Mois actifs: {metrics['active_months']}/{metrics['total_months']}")
                print(f"   📊 Pattern: {metrics['seasonal_pattern']}")
                
            else:
                print(f"   ❌ Erreur: {result['error_message']}")
                
        except Exception as e:
            print(f"   💥 Exception: {str(e)}")
            results.append({
                'finca_id': finca_id,
                'status': 'error',
                'error_message': str(e)
            })
        
        # Sauvegarde intermédiaire tous les 5 fincas
        if i % 5 == 0:
            intermediate_file = output_dir / f"luminosity_top20_intermediate_{timestamp}.json"
            with open(intermediate_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"   💾 Sauvegarde intermédiaire: {intermediate_file}")
    
    total_time = time.time() - start_time
    
    # Statistiques finales
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    print(f"\n📊 RÉSULTATS FINAUX:")
    print(f"   ✅ Succès: {successful}/{len(results)}")
    print(f"   ❌ Échecs: {failed}/{len(results)}")
    print(f"   ⏱️  Temps total: {total_time:.1f}s")
    print(f"   ⚡ Temps moyen: {total_time/len(results):.1f}s par finca")
    
    if successful > 0:
        scores = [r['score'] for r in results if r['status'] == 'success']
        print(f"   📈 Score moyen: {sum(scores)/len(scores):.1f}/5")
        print(f"   📊 Distribution des scores:")
        for score in range(6):
            count = sum(1 for s in scores if s == score)
            if count > 0:
                print(f"      {score}/5: {count} fincas")
    
    # Sauvegarder les résultats finaux
    final_file = output_dir / f"luminosity_top20_{timestamp}.json"
    with open(final_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Créer un résumé CSV
    csv_file = output_dir / f"luminosity_top20_{timestamp}.csv"
    create_csv_summary(results, csv_file)
    
    # Créer un résumé JSON
    summary_file = output_dir / f"luminosity_top20_summary_{timestamp}.json"
    create_json_summary(results, total_time, timestamp, summary_file)
    
    print(f"\n💾 FICHIERS GÉNÉRÉS:")
    print(f"   📄 Résultats complets: {final_file}")
    print(f"   📊 Résumé CSV: {csv_file}")
    print(f"   📈 Résumé JSON: {summary_file}")
    
    return results


def create_csv_summary(results, csv_file):
    """Crée un résumé CSV des résultats"""
    import csv
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'finca_id', 'status', 'score', 'mean_luminosity', 'std_luminosity',
            'trend', 'active_months', 'total_months', 'luminosity_level',
            'seasonal_pattern', 'reason'
        ])
        
        for result in results:
            if result['status'] == 'success':
                metrics = result['metrics']
                writer.writerow([
                    result['finca_id'],
                    result['status'],
                    result['score'],
                    metrics['mean_luminosity'],
                    metrics['std_luminosity'],
                    metrics['trend'],
                    metrics['active_months'],
                    metrics['total_months'],
                    metrics['luminosity_level'],
                    metrics['seasonal_pattern'],
                    result['reason']
                ])
            else:
                writer.writerow([
                    result['finca_id'],
                    result['status'],
                    0, 0, 0, 0, 0, 0, 'error', 'error', result.get('error_message', '')
                ])


def create_json_summary(results, total_time, timestamp, summary_file):
    """Crée un résumé JSON des résultats"""
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    if successful:
        scores = [r['score'] for r in successful]
        luminosities = [r['metrics']['mean_luminosity'] for r in successful]
        levels = [r['metrics']['luminosity_level'] for r in successful]
        
        summary = {
            "timestamp": timestamp,
            "analysis_type": "luminosity_nocturne_top20",
            "total_fincas": len(results),
            "successful_analyses": len(successful),
            "failed_analyses": len(failed),
            "success_rate": len(successful) / len(results),
            "processing_time": {
                "total_seconds": total_time,
                "average_per_finca": total_time / len(results)
            },
            "score_statistics": {
                "mean_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
                "score_distribution": {
                    str(i): sum(1 for s in scores if s == i) 
                    for i in range(6)
                }
            },
            "luminosity_statistics": {
                "mean_luminosity": sum(luminosities) / len(luminosities),
                "min_luminosity": min(luminosities),
                "max_luminosity": max(luminosities),
                "level_distribution": {
                    level: sum(1 for l in levels if l == level)
                    for level in set(levels)
                }
            },
            "files_generated": [
                f"luminosity_top20_{timestamp}.json",
                f"luminosity_top20_{timestamp}.csv",
                f"luminosity_top20_summary_{timestamp}.json"
            ]
        }
    else:
        summary = {
            "timestamp": timestamp,
            "analysis_type": "luminosity_nocturne_top20",
            "total_fincas": len(results),
            "successful_analyses": 0,
            "failed_analyses": len(failed),
            "success_rate": 0,
            "error": "Aucune analyse réussie"
        }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)


def main():
    """Fonction principale"""
    try:
        results = analyze_top20_fincas()
        print(f"\n🎉 Analyse terminée avec succès!")
        print(f"📊 {len([r for r in results if r['status'] == 'success'])}/{len(results)} fincas analysées")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
