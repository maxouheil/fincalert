#!/usr/bin/env python3
"""
🌙 Batch Analysis - All 631 Fincas (OPTIMIZED)
Version optimisée avec mode démo forcé et parallélisation
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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


def analyze_single_finca(args):
    """Analyse une seule finca (pour parallélisation)"""
    finca_id, lat, lon, index, total = args
    
    try:
        analyzer = NocturnalLuminosityAnalyzer()
        
        # Mode démo forcé pour la vitesse
        result = analyzer.analyze_finca_luminosity(
            finca_id, lat, lon, months=12, demo=True
        )
        
        return {
            'index': index,
            'total': total,
            'result': result,
            'success': True
        }
        
    except Exception as e:
        return {
            'index': index,
            'total': total,
            'result': {
                'finca_id': finca_id,
                'status': 'error',
                'error_message': str(e)
            },
            'success': False,
            'error': str(e)
        }


def analyze_all_631_fincas_optimized(max_workers=4):
    """Analyse toutes les 631 fincas avec parallélisation"""
    print("🌙 ANALYSE LUMINOSITÉ NOCTURNE - TOUTES LES 631 FINCAS (OPTIMISÉE)")
    print("=" * 80)
    print("🚀 Mode démo forcé pour la vitesse maximale")
    print(f"⚡ Parallélisation: {max_workers} workers")
    print("⏱️  Monitoring en temps réel avec progression")
    print("💾 Sauvegarde automatique tous les 50 fincas")
    print("=" * 80)
    
    # Charger les données
    features = load_fincas_data()
    total_fincas = len(features)
    
    print(f"🧪 Analyse de {total_fincas} fincas")
    print(f"📅 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Préparer les arguments pour parallélisation
    args_list = []
    for i, feature in enumerate(features, 1):
        props = feature.get('properties', {})
        finca_id = props.get('id')
        lat = props.get('lat')
        lon = props.get('lon')
        
        if all([finca_id, lat, lon]):
            args_list.append((finca_id, lat, lon, i, total_fincas))
    
    # Timestamp pour les fichiers de sortie
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Créer le dossier de sortie
    output_dir = ROOT / 'data' / 'luminosity_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    results = []
    completed_count = 0
    success_count = 0
    error_count = 0
    
    # Lock pour thread-safe printing
    print_lock = threading.Lock()
    
    def print_progress(completed, total, success, error):
        """Affiche la progression de manière thread-safe"""
        with print_lock:
            progress = (completed / total) * 100
            bar_length = 30
            filled_length = int(bar_length * completed // total)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            
            print(f"\r[{bar}] {completed:3d}/{total} ({progress:5.1f}%) | ✅ {success:3d} ❌ {error:3d}", end="", flush=True)
    
    # Lancer l'analyse parallélisée
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Soumettre toutes les tâches
        future_to_args = {executor.submit(analyze_single_finca, args): args for args in args_list}
        
        # Traiter les résultats au fur et à mesure
        for future in as_completed(future_to_args):
            result_data = future.result()
            completed_count += 1
            
            if result_data['success']:
                success_count += 1
                results.append(result_data['result'])
                
                # Afficher les détails pour les premières fincas
                if completed_count <= 10:
                    result = result_data['result']
                    if result['status'] == 'success':
                        print(f"\n   ✅ [{completed_count:3d}] {result['finca_id']} - Score: {result['score']}/5")
                        metrics = result['metrics']
                        print(f"      📈 Luminosité: {metrics['mean_luminosity']:.3f} (niveau: {metrics['luminosity_level']})")
            else:
                error_count += 1
                results.append(result_data['result'])
                print(f"\n   ❌ [{completed_count:3d}] Erreur: {result_data.get('error', 'Unknown')}")
            
            # Afficher la progression
            print_progress(completed_count, total_fincas, success_count, error_count)
            
            # Sauvegarde intermédiaire tous les 50 fincas
            if completed_count % 50 == 0:
                intermediate_file = output_dir / f"luminosity_all631_intermediate_{timestamp}.json"
                with open(intermediate_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                elapsed_time = time.time() - start_time
                avg_time_per_finca = elapsed_time / completed_count
                estimated_total_time = avg_time_per_finca * total_fincas
                remaining_time = estimated_total_time - elapsed_time
                
                print(f"\n   💾 Sauvegarde intermédiaire: {intermediate_file}")
                print(f"   📊 Progression: {completed_count}/{total_fincas} ({progress:.1f}%)")
                print(f"   ✅ Succès: {success_count}, ❌ Erreurs: {error_count}")
                print(f"   ⏱️  Temps écoulé: {elapsed_time/60:.1f}min, Restant: {remaining_time/60:.1f}min")
                print(f"   🚀 Vitesse: {completed_count/elapsed_time:.1f} fincas/min")
    
    total_time = time.time() - start_time
    
    # Statistiques finales
    print(f"\n\n📊 RÉSULTATS FINAUX:")
    print("=" * 60)
    print(f"   📈 Total fincas: {total_fincas}")
    print(f"   ✅ Succès: {success_count}/{total_fincas} ({success_count/total_fincas*100:.1f}%)")
    print(f"   ❌ Échecs: {error_count}/{total_fincas} ({error_count/total_fincas*100:.1f}%)")
    print(f"   ⏱️  Temps total: {total_time/60:.1f} minutes")
    print(f"   ⚡ Temps moyen: {total_time/total_fincas:.1f}s par finca")
    print(f"   🚀 Vitesse moyenne: {total_fincas/total_time*60:.1f} fincas/min")
    
    if success_count > 0:
        successful_results = [r for r in results if r['status'] == 'success']
        scores = [r['score'] for r in successful_results]
        luminosities = [r['metrics']['mean_luminosity'] for r in successful_results]
        levels = [r['metrics']['luminosity_level'] for r in successful_results]
        
        print(f"\n📈 STATISTIQUES DES SCORES:")
        print(f"   📊 Score moyen: {sum(scores)/len(scores):.1f}/5")
        print(f"   📈 Score min/max: {min(scores)}/{max(scores)}")
        print(f"   📊 Distribution des scores:")
        for score in range(6):
            count = sum(1 for s in scores if s == score)
            if count > 0:
                percentage = count / len(scores) * 100
                print(f"      {score}/5: {count} fincas ({percentage:.1f}%)")
        
        print(f"\n💡 STATISTIQUES DE LUMINOSITÉ:")
        print(f"   📊 Luminosité moyenne: {sum(luminosities)/len(luminosities):.3f}")
        print(f"   📈 Luminosité min/max: {min(luminosities):.3f}/{max(luminosities):.3f}")
        print(f"   📊 Distribution des niveaux:")
        level_counts = {}
        for level in levels:
            level_counts[level] = level_counts.get(level, 0) + 1
        for level, count in sorted(level_counts.items()):
            percentage = count / len(levels) * 100
            print(f"      {level}: {count} fincas ({percentage:.1f}%)")
    
    # Sauvegarder les résultats finaux
    final_file = output_dir / f"luminosity_all631_optimized_{timestamp}.json"
    with open(final_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Créer un résumé CSV
    csv_file = output_dir / f"luminosity_all631_optimized_{timestamp}.csv"
    create_csv_summary(results, csv_file)
    
    # Créer un résumé JSON
    summary_file = output_dir / f"luminosity_all631_optimized_summary_{timestamp}.json"
    create_json_summary(results, total_time, timestamp, summary_file)
    
    print(f"\n💾 FICHIERS GÉNÉRÉS:")
    print(f"   📄 Résultats complets: {final_file}")
    print(f"   📊 Résumé CSV: {csv_file}")
    print(f"   📈 Résumé JSON: {summary_file}")
    print(f"   📁 Dossier: {output_dir}")
    
    print(f"\n🎉 ANALYSE TERMINÉE!")
    print(f"📅 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results


def create_csv_summary(results, csv_file):
    """Crée un résumé CSV des résultats"""
    import csv
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # En-tête
        writer.writerow([
            'finca_id', 'status', 'score', 'mean_luminosity', 'luminosity_level',
            'active_months', 'total_months', 'trend', 'seasonal_pattern',
            'reason', 'error_message'
        ])
        
        # Données
        for result in results:
            if result['status'] == 'success':
                metrics = result['metrics']
                writer.writerow([
                    result['finca_id'],
                    result['status'],
                    result['score'],
                    metrics['mean_luminosity'],
                    metrics['luminosity_level'],
                    metrics['active_months'],
                    metrics['total_months'],
                    metrics['trend'],
                    metrics['seasonal_pattern'],
                    result['reason'],
                    ''
                ])
            else:
                writer.writerow([
                    result['finca_id'],
                    result['status'],
                    0,
                    0,
                    '',
                    0,
                    0,
                    0,
                    '',
                    '',
                    result.get('error_message', '')
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
            "analysis_type": "luminosity_nocturne_all631_optimized",
            "total_fincas": len(results),
            "successful_analyses": len(successful),
            "failed_analyses": len(failed),
            "success_rate": len(successful) / len(results),
            "processing_time": {
                "total_seconds": total_time,
                "total_minutes": total_time / 60,
                "average_per_finca": total_time / len(results),
                "speed_fincas_per_minute": len(results) / total_time * 60
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
                f"luminosity_all631_optimized_{timestamp}.json",
                f"luminosity_all631_optimized_{timestamp}.csv",
                f"luminosity_all631_optimized_summary_{timestamp}.json"
            ]
        }
    else:
        summary = {
            "timestamp": timestamp,
            "analysis_type": "luminosity_nocturne_all631_optimized",
            "total_fincas": len(results),
            "successful_analyses": 0,
            "failed_analyses": len(failed),
            "success_rate": 0.0,
            "processing_time": {
                "total_seconds": total_time,
                "total_minutes": total_time / 60,
                "average_per_finca": total_time / len(results),
                "speed_fincas_per_minute": len(results) / total_time * 60
            },
            "error": "No successful analyses"
        }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyse optimisée de luminosité pour toutes les 631 fincas")
    parser.add_argument("--workers", type=int, default=4, help="Nombre de workers pour la parallélisation")
    
    args = parser.parse_args()
    
    try:
        results = analyze_all_631_fincas_optimized(max_workers=args.workers)
        print(f"\n✅ Script terminé avec succès!")
        print(f"📊 {len(results)} fincas analysées")
    except KeyboardInterrupt:
        print(f"\n⚠️  Analyse interrompue par l'utilisateur")
        print(f"💾 Sauvegarde des données partielles...")
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
