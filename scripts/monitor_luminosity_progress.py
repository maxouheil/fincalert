#!/usr/bin/env python3
"""
📊 Monitor Luminosity Progress
Script de monitoring pour suivre la progression de l'analyse de luminosité en temps réel
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


def find_latest_luminosity_file():
    """Trouve le fichier de luminosité le plus récent"""
    luminosity_dir = ROOT / 'data' / 'luminosity_analysis'
    
    if not luminosity_dir.exists():
        return None
    
    # Chercher les fichiers intermédiaires
    intermediate_files = list(luminosity_dir.glob("luminosity_all631_intermediate_*.json"))
    
    if not intermediate_files:
        return None
    
    # Retourner le plus récent
    return max(intermediate_files, key=lambda x: x.stat().st_mtime)


def monitor_progress():
    """Monitore la progression en temps réel"""
    print("📊 MONITORING PROGRESSION LUMINOSITÉ - TOUTES LES 631 FINCAS")
    print("=" * 70)
    print("🔄 Actualisation automatique toutes les 10 secondes")
    print("⏹️  Ctrl+C pour arrêter le monitoring")
    print("=" * 70)
    
    last_file_size = 0
    last_update_time = time.time()
    
    try:
        while True:
            # Trouver le fichier le plus récent
            latest_file = find_latest_luminosity_file()
            
            if latest_file:
                # Lire le fichier
                try:
                    with open(latest_file, 'r') as f:
                        data = json.load(f)
                    
                    # Calculer les statistiques
                    total_fincas = len(data)
                    successful = sum(1 for r in data if r['status'] == 'success')
                    failed = sum(1 for r in data if r['status'] == 'error')
                    success_rate = (successful / total_fincas * 100) if total_fincas > 0 else 0
                    
                    # Calculer la progression
                    progress = (total_fincas / 631) * 100
                    
                    # Barre de progression
                    bar_length = 40
                    filled_length = int(bar_length * total_fincas // 631)
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    
                    # Effacer la ligne précédente
                    print('\r', end='', flush=True)
                    
                    # Afficher les informations
                    current_time = datetime.now().strftime('%H:%M:%S')
                    print(f"[{current_time}] [{bar}] {total_fincas:3d}/631 ({progress:5.1f}%)", end='', flush=True)
                    print(f" | ✅ {successful:3d} ❌ {failed:3d} | {success_rate:5.1f}% succès", end='', flush=True)
                    
                    # Afficher les détails si le fichier a changé
                    current_file_size = latest_file.stat().st_size
                    if current_file_size != last_file_size:
                        print(f"\n📁 Fichier: {latest_file.name}")
                        print(f"📊 Progression: {total_fincas}/631 ({progress:.1f}%)")
                        print(f"✅ Succès: {successful}, ❌ Erreurs: {failed}")
                        print(f"📈 Taux de succès: {success_rate:.1f}%")
                        
                        # Afficher les dernières fincas analysées
                        if successful > 0:
                            recent_successful = [r for r in data[-10:] if r['status'] == 'success']
                            if recent_successful:
                                print(f"🔄 Dernières fincas analysées:")
                                for result in recent_successful[-5:]:
                                    metrics = result['metrics']
                                    print(f"   {result['finca_id']}: Score {result['score']}/5, "
                                          f"Luminosité {metrics['mean_luminosity']:.3f} ({metrics['luminosity_level']})")
                        
                        last_file_size = current_file_size
                        last_update_time = time.time()
                    
                    # Afficher le temps écoulé
                    elapsed = time.time() - last_update_time
                    if elapsed > 30:  # Afficher le temps toutes les 30 secondes
                        print(f"\n⏱️  Dernière mise à jour: {elapsed:.0f}s")
                        last_update_time = time.time()
                    
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"\n⚠️  Erreur lecture fichier: {e}")
            
            else:
                print(f"\r[{datetime.now().strftime('%H:%M:%S')}] ⏳ En attente du début de l'analyse...", end='', flush=True)
            
            # Attendre 10 secondes
            time.sleep(10)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Monitoring arrêté par l'utilisateur")
        
        # Afficher un résumé final
        latest_file = find_latest_luminosity_file()
        if latest_file:
            try:
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                
                total_fincas = len(data)
                successful = sum(1 for r in data if r['status'] == 'success')
                failed = sum(1 for r in data if r['status'] == 'error')
                
                print(f"\n📊 RÉSUMÉ FINAL:")
                print(f"   📈 Total fincas analysées: {total_fincas}/631")
                print(f"   ✅ Succès: {successful}")
                print(f"   ❌ Erreurs: {failed}")
                print(f"   📁 Fichier: {latest_file.name}")
                
            except Exception as e:
                print(f"❌ Erreur lecture résumé final: {e}")


def show_final_results():
    """Affiche les résultats finaux de l'analyse"""
    luminosity_dir = ROOT / 'data' / 'luminosity_analysis'
    
    if not luminosity_dir.exists():
        print("❌ Dossier d'analyse non trouvé")
        return
    
    # Chercher le fichier final
    final_files = list(luminosity_dir.glob("luminosity_all631_*.json"))
    final_files = [f for f in final_files if 'intermediate' not in f.name and 'summary' not in f.name]
    
    if not final_files:
        print("❌ Aucun fichier de résultats final trouvé")
        return
    
    latest_file = max(final_files, key=lambda x: x.stat().st_mtime)
    
    print(f"📊 RÉSULTATS FINAUX - {latest_file.name}")
    print("=" * 60)
    
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        total_fincas = len(data)
        successful = sum(1 for r in data if r['status'] == 'success')
        failed = sum(1 for r in data if r['status'] == 'error')
        
        print(f"📈 Total fincas: {total_fincas}")
        print(f"✅ Succès: {successful} ({successful/total_fincas*100:.1f}%)")
        print(f"❌ Erreurs: {failed} ({failed/total_fincas*100:.1f}%)")
        
        if successful > 0:
            successful_results = [r for r in data if r['status'] == 'success']
            scores = [r['score'] for r in successful_results]
            luminosities = [r['metrics']['mean_luminosity'] for r in successful_results]
            
            print(f"\n📈 STATISTIQUES DES SCORES:")
            print(f"   📊 Score moyen: {sum(scores)/len(scores):.1f}/5")
            print(f"   📈 Score min/max: {min(scores)}/{max(scores)}")
            
            print(f"\n💡 STATISTIQUES DE LUMINOSITÉ:")
            print(f"   📊 Luminosité moyenne: {sum(luminosities)/len(luminosities):.3f}")
            print(f"   📈 Luminosité min/max: {min(luminosities):.3f}/{max(luminosities):.3f}")
            
            # Distribution des scores
            print(f"\n📊 DISTRIBUTION DES SCORES:")
            for score in range(6):
                count = sum(1 for s in scores if s == score)
                if count > 0:
                    percentage = count / len(scores) * 100
                    print(f"   {score}/5: {count} fincas ({percentage:.1f}%)")
        
    except Exception as e:
        print(f"❌ Erreur lecture résultats: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor luminosity analysis progress")
    parser.add_argument("--final", action="store_true", help="Show final results only")
    
    args = parser.parse_args()
    
    if args.final:
        show_final_results()
    else:
        monitor_progress()
