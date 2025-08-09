#!/usr/bin/env python3
"""
Script pour vérifier la corrélation entre variation NDVI et score d'abandon
"""

import json
import statistics
import numpy as np

def calculate_coefficient_of_variation(ndvi_timeseries):
    """Calculer le coefficient de variation NDVI comme affiché dans le frontend"""
    valid_values = [ts['ndvi_value'] for ts in ndvi_timeseries if ts['ndvi_value'] is not None]
    if len(valid_values) < 2:
        return 0
    
    mean_ndvi = statistics.mean(valid_values)
    std_ndvi = statistics.stdev(valid_values)
    
    if mean_ndvi == 0:
        return 0
        
    # Coefficient de variation en pourcentage
    cv = (std_ndvi / mean_ndvi) * 100
    return cv

def load_and_analyze():
    """Charger les données et analyser la corrélation"""
    
    with open('/Users/sou/Desktop/Fincalert/data/abandon_analysis_FULL/fincas_abandon_analysis_FULL_20250809_120932.json', 'r') as f:
        data = json.load(f)
    
    fincas = data['fincas']
    
    print("🔍 ANALYSE DE CORRÉLATION NDVI-ABANDON")
    print("=" * 50)
    
    # Analyser par catégories de risque
    high_risk = []    # Score >= 70 (dots rouges)
    medium_risk = []  # Score 40-69 (dots orange)
    low_risk = []     # Score < 40 (dots verts)
    
    for finca in fincas:
        if finca['status'] != 'success':
            continue
            
        score = finca['abandon_score']
        std_dev = finca['std_deviation']
        median_ndvi = finca['median_ndvi']
        
        # Calculer le coefficient de variation comme dans le frontend
        cv = calculate_coefficient_of_variation(finca['ndvi_timeseries'])
        
        finca_data = {
            'id': finca['finca_id'],
            'score': score,
            'std_dev': std_dev,
            'median_ndvi': median_ndvi,
            'cv_percent': cv,
            'activity_status': finca['activity_status']
        }
        
        if score >= 70:
            high_risk.append(finca_data)
        elif score >= 40:
            medium_risk.append(finca_data)
        else:
            low_risk.append(finca_data)
    
    print(f"📊 DISTRIBUTION DES RISQUES:")
    print(f"🔴 Risque élevé (≥70): {len(high_risk)} fincas")
    print(f"🟡 Risque moyen (40-69): {len(medium_risk)} fincas")  
    print(f"🟢 Risque faible (<40): {len(low_risk)} fincas")
    print()
    
    # Analyser les variations dans chaque catégorie
    def analyze_category(category_data, name, emoji):
        if not category_data:
            return
            
        cv_values = [f['cv_percent'] for f in category_data]
        std_values = [f['std_dev'] for f in category_data]
        scores = [f['score'] for f in category_data]
        
        print(f"{emoji} {name.upper()} - Analyse des variations:")
        print(f"   Nombre: {len(category_data)}")
        print(f"   Score moyen: {np.mean(scores):.1f}")
        print(f"   CV moyen: {np.mean(cv_values):.1f}%")
        print(f"   Std dev moyen: {np.mean(std_values):.4f}")
        
        # Afficher quelques exemples
        print(f"   Exemples:")
        for i, finca in enumerate(sorted(category_data, key=lambda x: x['score'], reverse=True)[:5]):
            print(f"     {finca['id']}: Score {finca['score']:.1f}, CV {finca['cv_percent']:.1f}%, Status: {finca['activity_status']}")
        print()
    
    analyze_category(high_risk, "Risque élevé", "🔴")
    analyze_category(medium_risk, "Risque moyen", "🟡") 
    analyze_category(low_risk, "Risque faible", "🟢")
    
    # Vérifier la corrélation globale
    all_fincas = high_risk + medium_risk + low_risk
    scores = [f['score'] for f in all_fincas]
    cv_values = [f['cv_percent'] for f in all_fincas]
    
    correlation = np.corrcoef(scores, cv_values)[0, 1]
    
    print(f"🔗 CORRÉLATION GLOBALE:")
    print(f"   Corrélation Score ↔ Variation CV: {correlation:.3f}")
    
    if correlation > 0.5:
        print("   ✅ Corrélation positive forte - logique")
    elif correlation > 0.2:
        print("   ⚠️  Corrélation positive modérée")
    elif correlation < -0.2:
        print("   ❌ Corrélation négative - problématique!")
    else:
        print("   ⚠️  Corrélation faible - à investiguer")
    
    print()
    
    # Identifier les cas problématiques
    print("🚨 CAS PROBLÉMATIQUES (Score élevé mais variation faible):")
    problematic = [f for f in high_risk if f['cv_percent'] < 20]
    for finca in sorted(problematic, key=lambda x: x['score'], reverse=True)[:10]:
        print(f"   {finca['id']}: Score {finca['score']:.1f} mais CV seulement {finca['cv_percent']:.1f}%")
    
    if not problematic:
        print("   ✅ Aucun cas problématique trouvé")

if __name__ == "__main__":
    load_and_analyze()
