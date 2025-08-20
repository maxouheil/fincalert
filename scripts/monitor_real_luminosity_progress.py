#!/usr/bin/env python3
"""
🌙 Monitoring en temps réel - Analyse Luminosité Vraies Données VIIRS
Monitoring robuste avec détection automatique des fichiers
"""

import os
import sys
import json
import time
import glob
from datetime import datetime
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def find_latest_analysis_files():
    """Trouve les fichiers d'analyse les plus récents"""
    analysis_dir = ROOT / 'data' / 'luminosity_analysis'
    
    if not analysis_dir.exists():
        return None, None, None
    
    # Chercher les fichiers intermédiaires
    intermediate_files = list(analysis_dir.glob("luminosity_all631_real_intermediate_*.json"))
    if intermediate_files:
        latest_intermediate = max(intermediate_files, key=lambda x: x.stat().st_mtime)
    else:
        latest_intermediate = None
    
    # Chercher les fichiers finaux
    final_files = list(analysis_dir.glob("luminosity_all631_real_*.json"))
    final_files = [f for f in final_files if 'intermediate' not in f.name and 'summary' not in f.name]
    if final_files:
        latest_final = max(final_files, key=lambda x: x.stat().st_mtime)
    else:
        latest_final = None
    
    # Chercher les fichiers de résumé
    summary_files = list(analysis_dir.glob("luminosity_all631_real_summary_*.json"))
    if summary_files:
        latest_summary = max(summary_files, key=lambda x: x.stat().st_mtime)
    else:
        latest_summary = None
    
    return latest_intermediate, latest_final, latest_summary


def analyze_results_file(file_path):
    """Analyse un fichier de résultats"""
    if not file_path or not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        total = len(data)
        successful = sum(1 for r in data if r.get('status') == 'success')
        failed = sum(1 for r in data if r.get('status') == 'error')
        cached = sum(1 for r in data if r.get('cached', False))
        
        if successful > 0:
            scores = [r['score'] for r in data if r.get('status') == 'success']
            luminosities = [r['metrics']['mean_luminosity'] for r in data if r.get('status') == 'success']
            
            score_stats = {
                'mean': sum(scores) / len(scores),
                'min': min(scores),
                'max': max(scores),
                'distribution': {i: sum(1 for s in scores if s == i) for i in range(6)}
            }
            
            luminosity_stats = {
                'mean': sum(luminosities) / len(luminosities),
                'min': min(luminosities),
                'max': max(luminosities)
            }
        else:
            score_stats = None
            luminosity_stats = None
        
        return {
            'file_path': file_path,
            'total': total,
            'successful': successful,
            'failed': failed,
            'cached': cached,
            'success_rate': successful / total if total > 0 else 0,
            'cache_efficiency': cached / successful if successful > 0 else 0,
            'score_stats': score_stats,
            'luminosity_stats': luminosity_stats,
            'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime)
        }
    except Exception as e:
        print(f"❌ Erreur lecture fichier {file_path}: {e}")
        return None


def check_cache_status():
    """Vérifie l'état du cache"""
    cache_dir = ROOT / 'data' / 'luminosity_cache'
    cache_file = cache_dir / 'luminosity_cache.pkl'
    
    if cache_file.exists():
        try:
            import pickle
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            cache_size = cache_file.stat().st_size / (1024 * 1024)  # MB
            return {
                'entries': len(cache_data),
                'size_mb': cache_size,
                'last_modified': datetime.fromtimestamp(cache_file.stat().st_mtime)
            }
        except Exception as e:
            return {'error': str(e)}
    else:
        return None


def display_progress(intermediate_data, final_data, summary_data, cache_data):
    """Affiche la progression de manière claire"""
    print("\033[2J\033[H")  # Clear screen
    print("🌙 MONITORING ANALYSE LUMINOSITÉ - VRAIES DONNÉES VIIRS")
    print("=" * 70)
    print(f"📅 Dernière mise à jour: {datetime.now().strftime('%H:%M:%S')}")
    print("")
    
    # État général
    if intermediate_data:
        print("📊 PROGRESSION ACTUELLE:")
        print(f"   📈 Fincas analysées: {intermediate_data['total']}/631 ({intermediate_data['total']/631*100:.1f}%)")
        print(f"   ✅ Succès: {intermediate_data['successful']} ({intermediate_data['success_rate']*100:.1f}%)")
        print(f"   ❌ Échecs: {intermediate_data['failed']}")
        print(f"   💾 Cache utilisé: {intermediate_data['cached']} ({intermediate_data['cache_efficiency']*100:.1f}%)")
        print(f"   📅 Dernière modification: {intermediate_data['last_modified'].strftime('%H:%M:%S')}")
        
        # Barre de progression
        progress = intermediate_data['total'] / 631
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        print(f"   [{bar}] {intermediate_data['total']:3d}/631")
        
        if intermediate_data['score_stats']:
            print("")
            print("📈 STATISTIQUES DES SCORES:")
            stats = intermediate_data['score_stats']
            print(f"   📊 Score moyen: {stats['mean']:.1f}/5")
            print(f"   📈 Min/Max: {stats['min']}/{stats['max']}")
            print("   📊 Distribution:")
            for score in range(6):
                count = stats['distribution'].get(score, 0)
                if count > 0:
                    percentage = count / intermediate_data['successful'] * 100
                    print(f"      {score}/5: {count:3d} fincas ({percentage:5.1f}%)")
        
        if intermediate_data['luminosity_stats']:
            print("")
            print("💡 STATISTIQUES DE LUMINOSITÉ:")
            stats = intermediate_data['luminosity_stats']
            print(f"   📊 Moyenne: {stats['mean']:.3f}")
            print(f"   📈 Min/Max: {stats['min']:.3f}/{stats['max']:.3f}")
    
    elif final_data:
        print("✅ ANALYSE TERMINÉE!")
        print(f"   📊 Total fincas: {final_data['total']}")
        print(f"   ✅ Succès: {final_data['successful']} ({final_data['success_rate']*100:.1f}%)")
        print(f"   ❌ Échecs: {final_data['failed']}")
        print(f"   💾 Cache utilisé: {final_data['cached']} ({final_data['cache_efficiency']*100:.1f}%)")
    else:
        print("⏳ En attente du début de l'analyse...")
        print("   💡 L'analyse va commencer automatiquement")
    
    # Cache
    if cache_data:
        print("")
        print("💾 ÉTAT DU CACHE:")
        if 'error' in cache_data:
            print(f"   ❌ Erreur: {cache_data['error']}")
        else:
            print(f"   📊 Entrées: {cache_data['entries']}")
            print(f"   💾 Taille: {cache_data['size_mb']:.1f} MB")
            print(f"   📅 Dernière modification: {cache_data['last_modified'].strftime('%H:%M:%S')}")
    
    # Fichiers
    print("")
    print("📁 FICHIERS:")
    if intermediate_data:
        print(f"   📄 Intermédiaire: {intermediate_data['file_path'].name}")
    if final_data:
        print(f"   📄 Final: {final_data['file_path'].name}")
    if summary_data:
        print(f"   📈 Résumé: {summary_data['file_path'].name}")
    
    print("")
    print("🔄 Actualisation automatique toutes les 5 secondes...")
    print("   💡 Ctrl+C pour arrêter")


def monitor_progress():
    """Monitoring principal"""
    print("🌙 MONITORING ANALYSE LUMINOSITÉ - VRAIES DONNÉES VIIRS")
    print("=" * 70)
    print("🔍 Recherche des fichiers d'analyse...")
    
    last_intermediate_count = 0
    last_final_count = 0
    
    try:
        while True:
            # Trouver les fichiers
            intermediate_file, final_file, summary_file = find_latest_analysis_files()
            
            # Analyser les données
            intermediate_data = analyze_results_file(intermediate_file)
            final_data = analyze_results_file(final_file)
            summary_data = analyze_results_file(summary_file)
            cache_data = check_cache_status()
            
            # Vérifier si l'analyse progresse
            current_intermediate_count = intermediate_data['total'] if intermediate_data else 0
            current_final_count = final_data['total'] if final_data else 0
            
            # Afficher la progression
            display_progress(intermediate_data, final_data, summary_data, cache_data)
            
            # Vérifier si l'analyse est terminée
            if final_data and final_data['total'] == 631:
                print("\n🎉 ANALYSE TERMINÉE AVEC SUCCÈS!")
                print(f"📊 {final_data['total']} fincas analysées")
                print(f"✅ Taux de succès: {final_data['success_rate']*100:.1f}%")
                break
            
            # Vérifier si l'analyse progresse
            if current_intermediate_count > last_intermediate_count:
                print(f"\n🚀 Progression détectée: {current_intermediate_count} fincas")
                last_intermediate_count = current_intermediate_count
            
            if current_final_count > last_final_count:
                print(f"\n✅ Fichier final mis à jour: {current_final_count} fincas")
                last_final_count = current_final_count
            
            # Attendre
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring arrêté par l'utilisateur")
        print("📊 État final:")
        
        intermediate_file, final_file, summary_file = find_latest_analysis_files()
        intermediate_data = analyze_results_file(intermediate_file)
        final_data = analyze_results_file(final_file)
        
        if intermediate_data:
            print(f"   📈 Fincas analysées: {intermediate_data['total']}/631")
            print(f"   ✅ Succès: {intermediate_data['successful']}")
            print(f"   ❌ Échecs: {intermediate_data['failed']}")
        
        if final_data:
            print(f"   📄 Fichier final: {final_data['total']} fincas")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitoring de l'analyse de luminosité optimisée")
    parser.add_argument("--final", action="store_true", help="Afficher seulement les résultats finaux")
    
    args = parser.parse_args()
    
    if args.final:
        # Mode final seulement
        intermediate_file, final_file, summary_file = find_latest_analysis_files()
        
        if final_file:
            final_data = analyze_results_file(final_file)
            if final_data:
                print("📊 RÉSULTATS FINAUX:")
                print(f"   📈 Total fincas: {final_data['total']}")
                print(f"   ✅ Succès: {final_data['successful']} ({final_data['success_rate']*100:.1f}%)")
                print(f"   ❌ Échecs: {final_data['failed']}")
                print(f"   💾 Cache utilisé: {final_data['cached']} ({final_data['cache_efficiency']*100:.1f}%)")
                
                if final_data['score_stats']:
                    print(f"   📊 Score moyen: {final_data['score_stats']['mean']:.1f}/5")
                
                print(f"   📄 Fichier: {final_file}")
        else:
            print("❌ Aucun fichier final trouvé")
    else:
        # Mode monitoring continu
        monitor_progress()
