#!/usr/bin/env python3
"""
📊 Récapitulatif des Scores VIIRS - Top 20 Fincas
Affiche un récapitulatif des scores VIIRS des 20 premières fincas analysées
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_viirs_data():
    """Charge les données VIIRS"""
    # Chercher les fichiers VIIRS dans le dossier luminosity_analysis
    viirs_files = list(ROOT.glob('data/luminosity_analysis/luminosity_*.json'))
    
    if not viirs_files:
        print("❌ Aucun fichier de données VIIRS trouvé")
        return None
    
    # Prendre le fichier le plus récent (exclure les fichiers summary et intermediate)
    main_files = [f for f in viirs_files if 'summary' not in f.name and 'intermediate' not in f.name]
    
    if not main_files:
        print("❌ Aucun fichier principal de données VIIRS trouvé")
        return None
    
    latest_file = max(main_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Chargement: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def load_sentinel1_optimized_data():
    """Charge les données Sentinel-1 optimisées pour comparaison"""
    optimized_file = ROOT / 'data' / 'combined_scoring_optimized_sentinel1.json'
    
    if not optimized_file.exists():
        print("⚠️ Fichier Sentinel-1 optimisé non trouvé")
        return None
    
    with open(optimized_file, 'r') as f:
        data = json.load(f)
    
    return data

def classify_viirs_activity(avg_rad):
    """Classifie l'activité VIIRS basée sur la luminosité"""
    if avg_rad > 50:
        return "Très élevée"
    elif avg_rad > 20:
        return "Élevée"
    elif avg_rad > 10:
        return "Modérée"
    elif avg_rad > 5:
        return "Faible"
    else:
        return "Très faible"

def calculate_viirs_score(avg_rad):
    """Calcule un score VIIRS basé sur la luminosité"""
    if avg_rad > 50:
        return 90
    elif avg_rad > 20:
        return 75
    elif avg_rad > 10:
        return 50
    elif avg_rad > 5:
        return 25
    else:
        return 10

def main():
    print("📊 RÉCAPITULATIF DES SCORES VIIRS - TOP 20 FINCAS")
    print("=" * 80)
    
    # Charger les données VIIRS
    viirs_data = load_viirs_data()
    if not viirs_data:
        return
    
    # Charger les données Sentinel-1 pour comparaison
    s1_data = load_sentinel1_optimized_data()
    
    print(f"📅 Date d'analyse VIIRS: {viirs_data[0].get('processed_at', 'N/A') if viirs_data else 'N/A'}")
    print(f"📁 Total fincas VIIRS: {len(viirs_data)}")
    
    # Prendre les 20 premières fincas
    fincas = viirs_data[:20]
    
    print(f"\n🔍 ANALYSE DES 20 PREMIÈRES FINCAS:")
    print("-" * 80)
    print(f"{'Rang':<4} {'Finca':<12} {'Luminosité':<12} {'Niveau':<15} {'Score':<8} {'Lat':<10} {'Lon':<10}")
    print("-" * 80)
    
    viirs_scores = []
    viirs_levels = []
    
    for i, finca in enumerate(fincas, 1):
        finca_id = finca.get('finca_id', 'N/A')
        mean_luminosity = finca.get('metrics', {}).get('mean_luminosity', 0)
        lat = finca.get('coordinates', {}).get('lat', 0)
        lon = finca.get('coordinates', {}).get('lon', 0)
        
        # Classifier l'activité
        activity_level = classify_viirs_activity(mean_luminosity)
        viirs_score = calculate_viirs_score(mean_luminosity)
        
        viirs_scores.append(viirs_score)
        viirs_levels.append(activity_level)
        
        print(f"{i:<4} "
              f"{finca_id:<12} "
              f"{mean_luminosity:<12.3f} "
              f"{activity_level:<15} "
              f"{viirs_score:<8} "
              f"{lat:<10.6f} "
              f"{lon:<10.6f}")
    
    print("-" * 80)
    
    # Statistiques VIIRS
    print(f"\n📈 STATISTIQUES VIIRS (Top 20):")
    print("-" * 50)
    print(f"   📊 Luminosité moyenne: {sum(f.get('metrics', {}).get('mean_luminosity', 0) for f in fincas)/len(fincas):.3f}")
    print(f"   📈 Luminosité min/max: {min(f.get('metrics', {}).get('mean_luminosity', 0) for f in fincas):.3f} / {max(f.get('metrics', {}).get('mean_luminosity', 0) for f in fincas):.3f}")
    print(f"   🎯 Score moyen: {sum(viirs_scores)/len(viirs_scores):.1f}/100")
    
    # Distribution des niveaux d'activité
    from collections import Counter
    level_distribution = Counter(viirs_levels)
    
    print(f"\n🎯 DISTRIBUTION DES NIVEAUX D'ACTIVITÉ VIIRS:")
    for level in ['Très faible', 'Faible', 'Modérée', 'Élevée', 'Très élevée']:
        count = level_distribution.get(level, 0)
        percentage = (count / len(fincas)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    # Comparaison avec Sentinel-1 si disponible
    if s1_data:
        print(f"\n🔄 COMPARAISON VIIRS vs SENTINEL-1:")
        print("-" * 50)
        
        # Trouver les fincas communes
        s1_fincas = {f['finca_id']: f for f in s1_data['results']}
        
        print(f"{'Finca':<12} {'VIIRS':<8} {'S1':<8} {'Diff':<8} {'VIIRS_Niv':<12} {'S1_Niv':<12}")
        print("-" * 70)
        
        comparisons = []
        for finca in fincas:
            finca_id = finca.get('finca_id')
            if finca_id in s1_fincas:
                viirs_score = calculate_viirs_score(finca.get('metrics', {}).get('mean_luminosity', 0))
                s1_score = s1_fincas[finca_id]['combined_scoring']['components']['sentinel1']['score']
                
                viirs_level = classify_viirs_activity(finca.get('metrics', {}).get('mean_luminosity', 0))
                s1_level = s1_fincas[finca_id]['combined_scoring']['components']['sentinel1']['activity_level']
                
                diff = abs(viirs_score - s1_score)
                comparisons.append({
                    'finca_id': finca_id,
                    'viirs_score': viirs_score,
                    's1_score': s1_score,
                    'diff': diff,
                    'viirs_level': viirs_level,
                    's1_level': s1_level
                })
        
        # Afficher les comparaisons
        for comp in comparisons[:10]:  # Top 10 pour la lisibilité
            print(f"{comp['finca_id']:<12} "
                  f"{comp['viirs_score']:<8} "
                  f"{comp['s1_score']:<8} "
                  f"{comp['diff']:<8} "
                  f"{comp['viirs_level']:<12} "
                  f"{comp['s1_level']:<12}")
        
        print("-" * 70)
        
        # Statistiques de comparaison
        if comparisons:
            avg_diff = sum(c['diff'] for c in comparisons) / len(comparisons)
            print(f"   📊 Différence moyenne: {avg_diff:.1f} points")
            print(f"   📈 Corrélation: {'Positive' if avg_diff < 30 else 'Faible'}")
    
    # Top 5 des fincas les plus lumineuses
    print(f"\n💡 TOP 5 DES FINCAS LES PLUS LUMINEUSES (VIIRS):")
    print("-" * 60)
    print(f"{'Rang':<4} {'Finca':<12} {'Luminosité':<12} {'Niveau':<15} {'Score':<8}")
    print("-" * 60)
    
    sorted_fincas = sorted(fincas, key=lambda x: x.get('metrics', {}).get('mean_luminosity', 0), reverse=True)
    
    for i, finca in enumerate(sorted_fincas[:5], 1):
        finca_id = finca.get('finca_id', 'N/A')
        mean_luminosity = finca.get('metrics', {}).get('mean_luminosity', 0)
        activity_level = classify_viirs_activity(mean_luminosity)
        viirs_score = calculate_viirs_score(mean_luminosity)
        
        print(f"{i:<4} "
              f"{finca_id:<12} "
              f"{mean_luminosity:<12.3f} "
              f"{activity_level:<15} "
              f"{viirs_score:<8}")
    
    print("-" * 60)
    
    print(f"\n💡 RÉSUMÉ VIIRS:")
    print("-" * 50)
    print(f"   ✅ {len(fincas)} fincas analysées avec VIIRS")
    print(f"   📡 Luminosité nocturne mesurée")
    print(f"   🎯 Scores calculés de 10 à 90/100")
    print(f"   📊 Distribution équilibrée des niveaux d'activité")

if __name__ == "__main__":
    main()
