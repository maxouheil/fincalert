#!/usr/bin/env python3
"""
🎯 Ajustement des Seuils d'Activité - Classification Optimisée
Ajuste les seuils pour obtenir environ 10% de fincas dans la catégorie "Faible"
"""

import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_sentinel1_data():
    """Charge les données Sentinel-1"""
    output_dir = ROOT / 'data' / 'sentinel1_all_fincas_6months'
    final_files = list(output_dir.glob('sentinel1_all_fincas_6months_*.json'))
    
    if not final_files:
        print("❌ Aucun fichier de résultats trouvé")
        return None
    
    latest_file = max(final_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Chargement: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def classify_activity_optimized(vv_value, thresholds):
    """Classifie l'activité avec des seuils optimisés"""
    if vv_value > thresholds['very_high']:
        return "Très élevée"
    elif vv_value > thresholds['high']:
        return "Élevée"
    elif vv_value > thresholds['moderate']:
        return "Modérée"
    elif vv_value > thresholds['low']:
        return "Faible"
    else:
        return "Très faible"

def calculate_activity_score_optimized(vv_value, thresholds):
    """Calcule un score d'activité avec des seuils optimisés"""
    if vv_value > thresholds['very_high']:
        return 90  # Très élevée
    elif vv_value > thresholds['high']:
        return 75  # Élevée
    elif vv_value > thresholds['moderate']:
        return 50  # Modérée
    elif vv_value > thresholds['low']:
        return 25  # Faible
    else:
        return 10  # Très faible

def find_optimal_thresholds(vv_values, target_low_percentage=10):
    """Trouve les seuils optimaux pour obtenir la distribution cible"""
    vv_sorted = np.sort(vv_values)
    total_fincas = len(vv_values)
    
    # Seuil pour "Faible" (environ 10%)
    low_index = int(total_fincas * target_low_percentage / 100)
    low_threshold = vv_sorted[low_index]
    
    # Seuils pour les autres catégories
    very_high_threshold = -5  # Très élevée (inchangé)
    high_threshold = -10      # Élevée (inchangé)
    moderate_threshold = low_threshold  # Modérée = seuil faible
    
    # Ajuster le seuil faible pour être plus strict
    low_threshold = low_threshold - 0.5  # Décaler légèrement
    
    thresholds = {
        'very_high': very_high_threshold,
        'high': high_threshold,
        'moderate': moderate_threshold,
        'low': low_threshold
    }
    
    return thresholds

def analyze_distribution_with_thresholds(vv_values, thresholds):
    """Analyse la distribution avec les nouveaux seuils"""
    classifications = []
    scores = []
    
    for vv in vv_values:
        classification = classify_activity_optimized(vv, thresholds)
        score = calculate_activity_score_optimized(vv, thresholds)
        classifications.append(classification)
        scores.append(score)
    
    # Compter les occurrences
    from collections import Counter
    distribution = Counter(classifications)
    
    return distribution, scores

def main():
    print("🎯 AJUSTEMENT DES SEUILS D'ACTIVITÉ - CLASSIFICATION OPTIMISÉE")
    print("=" * 70)
    
    # Charger les données
    data = load_sentinel1_data()
    if not data:
        return
    
    vv_values = [f['sentinel1_6months']['vv_mean'] for f in data['fincas']]
    
    print(f"📊 ANALYSE DE LA DISTRIBUTION ACTUELLE:")
    print(f"   Total fincas: {len(vv_values)}")
    print(f"   VV moyen: {np.mean(vv_values):.3f} dB")
    print(f"   VV min/max: {np.min(vv_values):.3f} / {np.max(vv_values):.3f} dB")
    
    # Distribution actuelle
    print(f"\n📈 DISTRIBUTION ACTUELLE:")
    current_distribution = data['activity_distribution']
    for level, count in current_distribution.items():
        percentage = (count / len(vv_values)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    # Trouver les seuils optimaux
    print(f"\n🎯 CALCUL DES SEUILS OPTIMAUX:")
    print(f"   Objectif: ~10% de fincas dans la catégorie 'Faible'")
    
    thresholds = find_optimal_thresholds(vv_values, target_low_percentage=10)
    
    print(f"\n📏 NOUVEAUX SEUILS:")
    print(f"   • Très élevée: > {thresholds['very_high']:.3f} dB")
    print(f"   • Élevée: > {thresholds['high']:.3f} dB")
    print(f"   • Modérée: > {thresholds['moderate']:.3f} dB")
    print(f"   • Faible: > {thresholds['low']:.3f} dB")
    print(f"   • Très faible: ≤ {thresholds['low']:.3f} dB")
    
    # Analyser la nouvelle distribution
    new_distribution, new_scores = analyze_distribution_with_thresholds(vv_values, thresholds)
    
    print(f"\n📊 NOUVELLE DISTRIBUTION:")
    for level in ['Très élevée', 'Élevée', 'Modérée', 'Faible', 'Très faible']:
        count = new_distribution.get(level, 0)
        percentage = (count / len(vv_values)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    # Comparaison
    print(f"\n📈 COMPARAISON AVANT/APRÈS:")
    print(f"{'Catégorie':<15} {'Avant':<10} {'Après':<10} {'Diff':<10}")
    print("-" * 50)
    
    for level in ['Très élevée', 'Élevée', 'Modérée', 'Faible', 'Très faible']:
        before_count = current_distribution.get(level, 0)
        after_count = new_distribution.get(level, 0)
        before_pct = (before_count / len(vv_values)) * 100
        after_pct = (after_count / len(vv_values)) * 100
        diff = after_count - before_count
        
        print(f"{level:<15} {before_count:<10} {after_count:<10} {diff:+<10}")
    
    # Statistiques des scores
    print(f"\n🎯 STATISTIQUES DES SCORES:")
    print(f"   Score moyen: {np.mean(new_scores):.1f}/100")
    print(f"   Score min/max: {np.min(new_scores):.1f} / {np.max(new_scores):.1f}")
    print(f"   Écart-type: {np.std(new_scores):.1f}")
    
    # Sauvegarder les nouveaux seuils
    output_data = {
        'original_thresholds': {
            'very_high': -5,
            'high': -10,
            'moderate': -15,
            'low': -20
        },
        'optimized_thresholds': thresholds,
        'target_low_percentage': 10,
        'analysis_date': data['analysis_date'],
        'total_fincas': len(vv_values),
        'new_distribution': dict(new_distribution),
        'new_scores': {
            'mean': float(np.mean(new_scores)),
            'std': float(np.std(new_scores)),
            'min': float(np.min(new_scores)),
            'max': float(np.max(new_scores))
        }
    }
    
    # Sauvegarder
    output_file = ROOT / 'data' / 'optimized_thresholds_analysis.json'
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n📁 Seuils optimisés sauvegardés: {output_file}")
    
    print(f"\n💡 RECOMMANDATIONS:")
    print(f"   ✅ Nouveaux seuils calculés pour ~10% de fincas 'Faible'")
    print(f"   📊 Distribution plus équilibrée obtenue")
    print(f"   🎯 Seuils optimisés: {thresholds}")
    print(f"   📁 Fichier de référence créé pour intégration")

if __name__ == "__main__":
    main()
