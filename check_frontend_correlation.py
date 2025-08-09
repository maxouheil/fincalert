#!/usr/bin/env python3
"""
Script pour vérifier la corrélation exactement comme calculée dans le frontend
"""

import json
import numpy as np

def load_and_analyze():
    """Charger les données et analyser avec la logique frontend exacte"""
    
    with open('/Users/sou/Desktop/Fincalert/data/abandon_analysis_FULL/fincas_abandon_analysis_FULL_20250809_120932.json', 'r') as f:
        data = json.load(f)
    
    fincas = data['fincas']
    
    print("🔍 ANALYSE FRONTEND - CORRÉLATION NDVI-ABANDON")
    print("=" * 55)
    
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
        
        # Calculer EXACTEMENT comme dans le frontend
        if median_ndvi > 0:
            variation_percent = round((std_dev / median_ndvi) * 100)
        else:
            variation_percent = 23  # Valeur par défaut
        
        finca_data = {
            'id': finca['finca_id'],
            'score': score,
            'std_dev': std_dev,
            'median_ndvi': median_ndvi,
            'variation_percent': variation_percent,
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
            
        variations = [f['variation_percent'] for f in category_data]
        scores = [f['score'] for f in category_data]
        median_ndvis = [f['median_ndvi'] for f in category_data]
        
        print(f"{emoji} {name.upper()} - Analyse détaillée:")
        print(f"   Nombre: {len(category_data)}")
        print(f"   Score moyen: {np.mean(scores):.1f}")
        print(f"   Variation moyenne: {np.mean(variations):.1f}%")
        print(f"   NDVI médian moyen: {np.mean(median_ndvis):.3f}")
        
        # Afficher quelques exemples détaillés
        print(f"   Exemples détaillés:")
        for i, finca in enumerate(sorted(category_data, key=lambda x: x['score'], reverse=True)[:3]):
            print(f"     {finca['id']}: Score {finca['score']:.1f}, Variation {finca['variation_percent']}%, NDVI {finca['median_ndvi']:.3f}")
        print()
    
    analyze_category(high_risk, "Risque élevé", "🔴")
    analyze_category(medium_risk, "Risque moyen", "🟡")
    analyze_category(low_risk, "Risque faible", "🟢")
    
    # Vérifier la corrélation globale
    all_fincas = high_risk + medium_risk + low_risk
    scores = [f['score'] for f in all_fincas]
    variations = [f['variation_percent'] for f in all_fincas]
    median_ndvis = [f['median_ndvi'] for f in all_fincas]
    
    correlation_score_variation = np.corrcoef(scores, variations)[0, 1]
    correlation_score_ndvi = np.corrcoef(scores, median_ndvis)[0, 1]
    
    print(f"🔗 CORRÉLATIONS:")
    print(f"   Score ↔ Variation%: {correlation_score_variation:.3f}")
    print(f"   Score ↔ NDVI médian: {correlation_score_ndvi:.3f}")
    print()
    
    # Analyser la logique du score
    print("📋 LOGIQUE DU SCORE D'ABANDON:")
    print("   Si NDVI élevé + variation faible → Abandonné (végétation naturelle stable)")
    print("   Si NDVI faible + variation élevée → Actif (cultivation/travail du sol)")
    print()
    
    # Vérifier cette logique
    print("🧪 VÉRIFICATION DE LA LOGIQUE:")
    
    # Cas attendus pour fincas abandonnées (score élevé)
    high_ndvi_low_var = [f for f in high_risk if f['median_ndvi'] > 0.3 and f['variation_percent'] < 30]
    print(f"   Fincas abandonnées logiques (NDVI élevé + variation faible): {len(high_ndvi_low_var)}")
    
    # Cas attendus pour fincas actives (score faible)  
    low_ndvi_high_var = [f for f in low_risk if f['median_ndvi'] < 0.3 and f['variation_percent'] > 20]
    print(f"   Fincas actives logiques (NDVI faible + variation élevée): {len(low_ndvi_high_var)}")
    
    print()
    print("🔍 EXEMPLES REPRÉSENTATIFS:")
    
    if high_ndvi_low_var:
        print("   Abandonnées typiques:")
        for f in high_ndvi_low_var[:3]:
            print(f"     {f['id']}: Score {f['score']:.1f}, NDVI {f['median_ndvi']:.3f}, Var {f['variation_percent']}%")
    
    if low_ndvi_high_var:
        print("   Actives typiques:")
        for f in low_ndvi_high_var[:3]:
            print(f"     {f['id']}: Score {f['score']:.1f}, NDVI {f['median_ndvi']:.3f}, Var {f['variation_percent']}%")

if __name__ == "__main__":
    load_and_analyze()
