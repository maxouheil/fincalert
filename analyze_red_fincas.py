#!/usr/bin/env python3
"""
Analyser 20 fincas rouges (score élevé) pour vérifier les variations NDVI réelles
"""

import json
import statistics
import numpy as np

def calculate_real_variation(ndvi_timeseries):
    """Calculer la vraie variation NDVI à partir des données brutes"""
    valid_values = [ts['ndvi_value'] for ts in ndvi_timeseries if ts['ndvi_value'] is not None]
    
    if len(valid_values) < 2:
        return {
            'count': len(valid_values),
            'min': None,
            'max': None,
            'range': None,
            'std': None,
            'cv': None,
            'values': valid_values
        }
    
    min_ndvi = min(valid_values)
    max_ndvi = max(valid_values)
    range_ndvi = max_ndvi - min_ndvi
    mean_ndvi = statistics.mean(valid_values)
    std_ndvi = statistics.stdev(valid_values)
    cv = (std_ndvi / mean_ndvi) * 100 if mean_ndvi > 0 else 0
    
    return {
        'count': len(valid_values),
        'min': round(min_ndvi, 4),
        'max': round(max_ndvi, 4),
        'range': round(range_ndvi, 4),
        'mean': round(mean_ndvi, 4),
        'std': round(std_ndvi, 4),
        'cv': round(cv, 1),
        'values': [round(v, 4) for v in valid_values]
    }

def analyze_red_fincas():
    """Analyser 20 fincas avec les scores les plus élevés"""
    
    with open('/Users/sou/Desktop/Fincalert/data/abandon_analysis_FULL/fincas_abandon_analysis_FULL_20250809_120932.json', 'r') as f:
        data = json.load(f)
    
    fincas = data['fincas']
    
    # Filtrer et trier par score décroissant
    valid_fincas = [f for f in fincas if f['status'] == 'success']
    sorted_fincas = sorted(valid_fincas, key=lambda x: x['abandon_score'], reverse=True)
    
    print("🔴 ANALYSE DE 20 FINCAS AVEC LES SCORES LES PLUS ÉLEVÉS")
    print("=" * 65)
    print()
    
    for i, finca in enumerate(sorted_fincas[:20]):
        finca_id = finca['finca_id']
        score = finca['abandon_score']
        backend_std = finca['std_deviation']
        backend_median = finca['median_ndvi']
        
        # Calculer la variation frontend (comme affiché)
        frontend_variation = round((backend_std / backend_median) * 100) if backend_median > 0 else 0
        
        # Calculer les vraies variations à partir des données brutes
        real_stats = calculate_real_variation(finca['ndvi_timeseries'])
        
        print(f"🔍 {finca_id} (Score: {score:.1f})")
        print(f"   📊 Backend - Médian: {backend_median:.4f}, Std: {backend_std:.4f}")
        print(f"   📱 Frontend - Variation affichée: {frontend_variation}%")
        print(f"   📈 Données brutes:")
        print(f"      Periods valides: {real_stats['count']}")
        print(f"      Min NDVI: {real_stats['min']}")
        print(f"      Max NDVI: {real_stats['max']}")
        print(f"      Range: {real_stats['range']}")
        print(f"      Vraie variation (CV): {real_stats['cv']}%")
        print(f"      Valeurs: {real_stats['values'][:6]}{'...' if len(real_stats['values']) > 6 else ''}")
        
        # Vérifier la cohérence
        backend_cv = (backend_std / backend_median) * 100 if backend_median > 0 else 0
        print(f"   ✓ Vérification - Backend CV: {backend_cv:.1f}% vs Calculé: {real_stats['cv']}%")
        
        # Détecter les anomalies
        if real_stats['cv'] and real_stats['cv'] < 10:
            print(f"   ⚠️  VARIATION TRÈS FAIBLE: {real_stats['cv']}% pour un score élevé!")
        elif real_stats['cv'] and real_stats['cv'] > 50:
            print(f"   ⚠️  VARIATION TRÈS ÉLEVÉE: {real_stats['cv']}% pour un score élevé!")
        
        print()
    
    # Analyser la distribution globale des 20 plus hauts scores
    top_20_variations = []
    top_20_scores = []
    
    for finca in sorted_fincas[:20]:
        real_stats = calculate_real_variation(finca['ndvi_timeseries'])
        if real_stats['cv'] is not None:
            top_20_variations.append(real_stats['cv'])
            top_20_scores.append(finca['abandon_score'])
    
    print("📊 STATISTIQUES DES 20 FINCAS LES PLUS À RISQUE:")
    print(f"   Score moyen: {np.mean(top_20_scores):.1f}")
    print(f"   Variation moyenne: {np.mean(top_20_variations):.1f}%")
    print(f"   Variation médiane: {np.median(top_20_variations):.1f}%")
    print(f"   Variation min: {min(top_20_variations):.1f}%")
    print(f"   Variation max: {max(top_20_variations):.1f}%")
    print()
    
    # Compter les fincas avec variation < 10%
    low_variation_count = len([v for v in top_20_variations if v < 10])
    print(f"🚨 FINCAS AVEC VARIATION < 10%: {low_variation_count}/20")
    
    if low_variation_count > 5:
        print("   ✅ Cohérent - Fincas abandonnées = variation faible")
    elif low_variation_count < 2:
        print("   ❌ Problématique - Peu de fincas abandonnées avec variation faible")
    else:
        print("   ⚠️  Mitigé - Résultats variables")

if __name__ == "__main__":
    analyze_red_fincas()
