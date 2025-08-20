#!/usr/bin/env python3
"""
📊 Monitoring en Temps Réel - Analyse Sentinel-1 Toutes les Fincas
Surveille la progression de l'analyse radar en cours avec mise à jour live
"""

import json
import time
import os
from pathlib import Path
from datetime import datetime
import psutil

ROOT = Path(__file__).resolve().parents[1]

def clear_screen():
    """Nettoie l'écran"""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_process_info():
    """Récupère les informations sur le processus Python en cours"""
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] != current_pid and 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'analyze_all_fincas_sentinel1_6months.py' in cmdline:
                    return {
                        'pid': proc.info['pid'],
                        'cpu_percent': proc.cpu_percent(),
                        'memory_percent': proc.memory_percent(),
                        'memory_mb': proc.memory_info().rss / 1024 / 1024
                    }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def check_analysis_progress():
    """Vérifie la progression de l'analyse"""
    output_dir = ROOT / 'data' / 'sentinel1_all_fincas_6months'
    
    if not output_dir.exists():
        return None
    
    # Chercher les fichiers intermédiaires
    intermediate_files = list(output_dir.glob('sentinel1_intermediate_*.json'))
    
    if not intermediate_files:
        return None
    
    # Prendre le fichier le plus récent
    latest_file = max(intermediate_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def check_final_results():
    """Vérifie s'il y a des résultats finaux"""
    output_dir = ROOT / 'data' / 'sentinel1_all_fincas_6months'
    
    if not output_dir.exists():
        return None
    
    # Chercher les fichiers finaux
    final_files = list(output_dir.glob('sentinel1_all_fincas_6months_*.json'))
    
    if not final_files:
        return None
    
    # Prendre le fichier le plus récent
    latest_file = max(final_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def display_progress(data):
    """Affiche la progression en temps réel"""
    clear_screen()
    
    print("🛰️ MONITORING EN TEMPS RÉEL - ANALYSE SENTINEL-1")
    print("=" * 70)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Informations sur le processus
    process_info = get_process_info()
    if process_info:
        print(f"\n💻 PROCESSUS:")
        print(f"   PID: {process_info['pid']}")
        print(f"   CPU: {process_info['cpu_percent']:.1f}%")
        print(f"   RAM: {process_info['memory_mb']:.1f} MB ({process_info['memory_percent']:.1f}%)")
    
    # Progression
    progress_parts = data['progress'].split('/')
    current = int(progress_parts[0])
    total = int(progress_parts[1])
    percentage = (current / total) * 100
    
    print(f"\n📊 PROGRESSION:")
    print(f"   {current}/{total} fincas analysées")
    print(f"   {percentage:.1f}% terminé")
    print(f"   ✅ Succès: {data['success_count']}")
    print(f"   ❌ Échecs: {data['error_count']}")
    
    # Barre de progression
    bar_length = 50
    filled_length = int(bar_length * percentage / 100)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    print(f"   [{bar}] {percentage:.1f}%")
    
    # Estimation du temps restant
    if data['success_count'] > 0:
        avg_time_per_finca = 2  # secondes estimées par finca
        remaining_fincas = total - current
        estimated_time = remaining_fincas * avg_time_per_finca
        
        hours = int(estimated_time // 3600)
        minutes = int((estimated_time % 3600) // 60)
        seconds = int(estimated_time % 60)
        
        print(f"\n⏱️ TEMPS RESTANT ESTIMÉ:")
        if hours > 0:
            print(f"   {hours}h {minutes}m {seconds}s")
        elif minutes > 0:
            print(f"   {minutes}m {seconds}s")
        else:
            print(f"   {seconds}s")
    
    # Statistiques des fincas analysées
    if data['fincas']:
        print(f"\n📈 STATISTIQUES ACTUELLES:")
        vv_values = [f['sentinel1_6months']['vv_mean'] for f in data['fincas']]
        activity_levels = [f['sentinel1_6months']['activity_level'] for f in data['fincas']]
        
        print(f"   📊 VV moyen: {sum(vv_values)/len(vv_values):.3f} dB")
        print(f"   📈 VV min/max: {min(vv_values):.3f} / {max(vv_values):.3f} dB")
        
        # Distribution des niveaux d'activité
        level_counts = {}
        for level in activity_levels:
            level_counts[level] = level_counts.get(level, 0) + 1
        
        print(f"   🎯 Distribution d'activité:")
        for level, count in level_counts.items():
            percentage = (count / len(data['fincas'])) * 100
            print(f"      • {level}: {count} fincas ({percentage:.1f}%)")
    
    print(f"\n🔄 Mise à jour automatique toutes les 5 secondes...")
    print(f"   Appuyez sur Ctrl+C pour arrêter")

def display_final_results(data):
    """Affiche les résultats finaux"""
    clear_screen()
    
    print("🎉 ANALYSE SENTINEL-1 TERMINÉE!")
    print("=" * 70)
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n📊 RÉSULTATS FINAUX:")
    print(f"   📁 Total fincas: {data['total_fincas']}")
    print(f"   ✅ Succès: {data['successful_analyses']}")
    print(f"   ❌ Échecs: {data['failed_analyses']}")
    print(f"   📈 Taux de succès: {data['success_rate']:.1f}%")
    
    print(f"\n📈 STATISTIQUES FINALES:")
    vv_stats = data['vv_statistics']
    score_stats = data['score_statistics']
    
    print(f"   📊 VV moyen: {vv_stats['mean']:.3f} dB")
    print(f"   📈 VV min/max: {vv_stats['min']:.3f} / {vv_stats['max']:.3f} dB")
    print(f"   🎯 Score moyen: {score_stats['mean']:.1f}/100")
    
    print(f"\n🎯 Distribution d'activité:")
    for level, count in data['activity_distribution'].items():
        percentage = (count / data['successful_analyses']) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    print(f"\n📁 Fichiers générés dans: data/sentinel1_all_fincas_6months/")
    print(f"💡 L'analyse est terminée avec succès!")

def main():
    """Fonction principale"""
    print("📊 MONITORING EN TEMPS RÉEL - ANALYSE SENTINEL-1")
    print("=" * 70)
    print("Surveillance de l'analyse radar de toutes les fincas...")
    
    try:
        while True:
            # Vérifier s'il y a des résultats finaux
            final_data = check_final_results()
            if final_data:
                display_final_results(final_data)
                break
            
            # Vérifier la progression
            progress_data = check_analysis_progress()
            if progress_data:
                display_progress(progress_data)
            else:
                clear_screen()
                print("🛰️ MONITORING EN TEMPS RÉEL - ANALYSE SENTINEL-1")
                print("=" * 70)
                print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("\n⏳ En attente du démarrage de l'analyse...")
                print("   L'analyse Sentinel-1 va bientôt commencer")
                print("\n🔄 Mise à jour automatique toutes les 5 secondes...")
                print(f"   Appuyez sur Ctrl+C pour arrêter")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n\n🛑 Monitoring arrêté par l'utilisateur")
        print(f"💡 L'analyse continue en arrière-plan")

if __name__ == "__main__":
    main()
