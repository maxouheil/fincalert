#!/usr/bin/env python3
"""
📊 Monitoring de l'Analyse Sentinel-1 - Toutes les Fincas
Surveille la progression de l'analyse radar en cours
"""

import json
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

def check_analysis_progress():
    """Vérifie la progression de l'analyse"""
    output_dir = ROOT / 'data' / 'sentinel1_all_fincas_6months'
    
    if not output_dir.exists():
        print("❌ Dossier d'analyse non trouvé")
        return
    
    # Chercher les fichiers intermédiaires
    intermediate_files = list(output_dir.glob('sentinel1_intermediate_*.json'))
    
    if not intermediate_files:
        print("⏳ Aucun fichier intermédiaire trouvé - analyse en cours...")
        return
    
    # Prendre le fichier le plus récent
    latest_file = max(intermediate_files, key=lambda x: x.stat().st_mtime)
    
    print(f"📄 Fichier intermédiaire: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    print(f"📅 Date: {data['analysis_date']}")
    print(f"📊 Progression: {data['progress']}")
    print(f"✅ Succès: {data['success_count']}")
    print(f"❌ Échecs: {data['error_count']}")
    
    # Calculer le pourcentage
    progress_parts = data['progress'].split('/')
    if len(progress_parts) == 2:
        current = int(progress_parts[0])
        total = int(progress_parts[1])
        percentage = (current / total) * 100
        print(f"📈 Pourcentage: {percentage:.1f}%")
        
        # Estimation du temps restant
        if data['success_count'] > 0:
            avg_time_per_finca = 2  # secondes estimées par finca
            remaining_fincas = total - current
            estimated_time = remaining_fincas * avg_time_per_finca
            print(f"⏱️ Temps estimé restant: {estimated_time/60:.1f} minutes")
    
    # Afficher quelques statistiques des fincas analysées
    if data['fincas']:
        print(f"\n📊 STATISTIQUES DES FINCAS ANALYSÉES:")
        vv_values = [f['sentinel1_6months']['vv_mean'] for f in data['fincas']]
        activity_levels = [f['sentinel1_6months']['activity_level'] for f in data['fincas']]
        
        print(f"📊 VV moyen: {sum(vv_values)/len(vv_values):.3f} dB")
        print(f"📈 VV min/max: {min(vv_values):.3f} / {max(vv_values):.3f} dB")
        
        # Distribution des niveaux d'activité
        level_counts = {}
        for level in activity_levels:
            level_counts[level] = level_counts.get(level, 0) + 1
        
        print(f"🎯 Distribution d'activité:")
        for level, count in level_counts.items():
            percentage = (count / len(data['fincas'])) * 100
            print(f"   • {level}: {count} fincas ({percentage:.1f}%)")

def check_final_results():
    """Vérifie s'il y a des résultats finaux"""
    output_dir = ROOT / 'data' / 'sentinel1_all_fincas_6months'
    
    if not output_dir.exists():
        return False
    
    # Chercher les fichiers finaux
    final_files = list(output_dir.glob('sentinel1_all_fincas_6months_*.json'))
    
    if not final_files:
        return False
    
    # Prendre le fichier le plus récent
    latest_file = max(final_files, key=lambda x: x.stat().st_mtime)
    
    print(f"🎉 ANALYSE TERMINÉE!")
    print(f"📄 Fichier final: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    print(f"📅 Date: {data['analysis_date']}")
    print(f"📁 Total fincas: {data['total_fincas']}")
    print(f"✅ Succès: {data['successful_analyses']}")
    print(f"❌ Échecs: {data['failed_analyses']}")
    print(f"📈 Taux de succès: {data['success_rate']:.1f}%")
    
    print(f"\n📊 STATISTIQUES FINALES:")
    vv_stats = data['vv_statistics']
    score_stats = data['score_statistics']
    
    print(f"📊 VV moyen: {vv_stats['mean']:.3f} dB")
    print(f"📈 VV min/max: {vv_stats['min']:.3f} / {vv_stats['max']:.3f} dB")
    print(f"🎯 Score moyen: {score_stats['mean']:.1f}/100")
    
    print(f"\n🎯 Distribution d'activité:")
    for level, count in data['activity_distribution'].items():
        percentage = (count / data['successful_analyses']) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    return True

def main():
    """Fonction principale"""
    print("📊 MONITORING ANALYSE SENTINEL-1 - TOUTES LES FINCAS")
    print("=" * 70)
    
    while True:
        # Vérifier s'il y a des résultats finaux
        if check_final_results():
            break
        
        # Vérifier la progression
        check_analysis_progress()
        
        print(f"\n⏳ Attente 30 secondes avant prochaine vérification...")
        time.sleep(30)

if __name__ == "__main__":
    main()
