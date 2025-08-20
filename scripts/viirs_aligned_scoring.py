#!/usr/bin/env python3
"""
🌙 VIIRS Scoring Aligné - Système Optimisé
Aligné sur la logique NDVI/Sentinel-1: Score BAS = Risque d'abandon ÉLEVÉ
Distribution améliorée: 15% Faible, 25% Moyen, 60% Fort
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_viirs_data():
    """Charge les données VIIRS existantes"""
    viirs_files = list(ROOT.glob('data/luminosity_analysis/luminosity_*.json'))
    main_files = [f for f in viirs_files if 'summary' not in f.name and 'intermediate' not in f.name]
    latest_file = max(main_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    # Extraire les données avec détails
    finca_data = []
    for finca in data:
        if finca['status'] == 'success':
            metrics = finca['metrics']
            finca_data.append({
                'id': finca['finca_id'],
                'luminosity': metrics['mean_luminosity'],
                'trend': metrics['trend'],
                'active_months': metrics['active_months'],
                'total_months': metrics['total_months'],
                'std_luminosity': metrics['std_luminosity'],
                'seasonal_pattern': metrics['seasonal_pattern']
            })
    
    return finca_data


def create_aligned_scoring_system(finca_data):
    """Crée un système de scoring aligné sur NDVI/Sentinel-1"""
    print("🎯 SYSTÈME VIIRS ALIGNÉ")
    print("=" * 40)
    print("Logique: Luminosité FAIBLE = Score BAS = Risque d'abandon ÉLEVÉ")
    print("Distribution: 15% Faible, 25% Moyen, 60% Fort")
    
    # Trier par luminosité (du plus sombre au plus lumineux)
    # Plus sombre = plus de risque d'abandon = score plus bas
    sorted_fincas = sorted(finca_data, key=lambda x: x['luminosity'])
    
    n_total = len(sorted_fincas)
    n_faible = int(np.round(n_total * 0.15))   # 15% Faible (risque élevé)
    n_moyen = int(np.round(n_total * 0.25))    # 25% Moyen (risque modéré)
    n_fort = n_total - n_faible - n_moyen      # 60% Fort (risque faible)
    
    print(f"\n📊 Distribution cible:")
    print(f"   • Faible (risque élevé): {n_faible} fincas (15%)")
    print(f"   • Moyen (risque modéré): {n_moyen} fincas (25%)")
    print(f"   • Fort (risque faible): {n_fort} fincas (60%)")
    
    # Assigner les catégories selon le ranking
    categories = []
    for i, finca in enumerate(sorted_fincas):
        if i < n_faible:
            category = 'Faible'
            score = 15  # Score bas = risque élevé
            risk_level = 'Élevé'
        elif i < n_faible + n_moyen:
            category = 'Moyen'
            score = 50  # Score moyen = risque modéré
            risk_level = 'Modéré'
        else:
            category = 'Fort'
            score = 85  # Score élevé = risque faible
            risk_level = 'Faible'
        
        categories.append({
            'rank': i + 1,
            'id': finca['id'],
            'category': category,
            'score': score,
            'risk_level': risk_level,
            'luminosity': finca['luminosity'],
            'trend': finca['trend'],
            'active_ratio': finca['active_months'] / finca['total_months']
        })
    
    return categories


def display_aligned_classification(categories):
    """Affiche la classification alignée"""
    print(f"\n📊 CLASSIFICATION VIIRS ALIGNÉE")
    print("=" * 60)
    
    # Grouper par catégorie
    by_category = {}
    for cat in categories:
        category = cat['category']
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(cat)
    
    # Afficher chaque catégorie
    for category in ['Faible', 'Moyen', 'Fort']:
        if category in by_category:
            fincas = by_category[category]
            count = len(fincas)
            percentage = (count / len(categories)) * 100
            
            print(f"\n🔴 Luminosité {category.upper()} ({count} fincas, {percentage:.0f}%):")
            print(f"   Score: {fincas[0]['score']}/100 - Risque d'abandon: {fincas[0]['risk_level']}")
            for finca in fincas:
                print(f"   #{finca['rank']:2d} {finca['id']}: "
                      f"Lum={finca['luminosity']:.3f}, "
                      f"Trend={finca['trend']:6.2f}, "
                      f"Active={finca['active_ratio']:.2f}")


def calculate_aligned_thresholds(categories):
    """Calcule les seuils pour le système aligné"""
    # Analyser les seuils naturels
    faible_fincas = [c for c in categories if c['category'] == 'Faible']
    moyen_fincas = [c for c in categories if c['category'] == 'Moyen']
    fort_fincas = [c for c in categories if c['category'] == 'Fort']
    
    # Seuils de luminosité
    max_faible_lum = max(f['luminosity'] for f in faible_fincas)
    max_moyen_lum = max(f['luminosity'] for f in moyen_fincas)
    min_fort_lum = min(f['luminosity'] for f in fort_fincas)
    
    print(f"\n💡 Seuils VIIRS alignés:")
    print(f"   • Luminosité Faible: ≤ {max_faible_lum:.3f} (Score 15, Risque Élevé)")
    print(f"   • Luminosité Moyen: ≤ {max_moyen_lum:.3f} (Score 50, Risque Modéré)")
    print(f"   • Luminosité Fort: > {min_fort_lum:.3f} (Score 85, Risque Faible)")
    
    return {
        'luminosity_thresholds': {
            'faible_max': max_faible_lum,
            'moyen_max': max_moyen_lum,
            'fort_min': min_fort_lum
        },
        'scoring': {
            'faible': {'score': 15, 'risk': 'Élevé', 'description': 'Luminosité très faible = Abandon probable'},
            'moyen': {'score': 50, 'risk': 'Modéré', 'description': 'Luminosité faible-moyenne = Abandon possible'},
            'fort': {'score': 85, 'risk': 'Faible', 'description': 'Luminosité normale/élevée = Activité probable'}
        }
    }


def generate_aligned_implementation(categories, thresholds):
    """Génère l'implémentation alignée"""
    
    # Préparer les valeurs pour le template
    faible_max = thresholds['luminosity_thresholds']['faible_max']
    moyen_max = thresholds['luminosity_thresholds']['moyen_max']
    
    code = f'''#!/usr/bin/env python3
"""
🌙 VIIRS Scoring Aligné - Système Optimisé
Aligné sur NDVI/Sentinel-1: Score BAS = Risque d'abandon ÉLEVÉ
Distribution: 15% Faible, 25% Moyen, 60% Fort
"""

def calculate_viirs_abandon_score_aligned(mean_luminosity, trend=0.0, active_months_ratio=1.0):
    """
    Calcule le score d'abandon VIIRS aligné sur NDVI/Sentinel-1
    
    Logique: Luminosité FAIBLE = Score BAS = Risque d'abandon ÉLEVÉ
    
    Args:
        mean_luminosity (float): Luminosité moyenne VIIRS (nW/cm²/sr)
        trend (float): Tendance temporelle (optionnel)
        active_months_ratio (float): Ratio mois actifs (optionnel)
    
    Returns:
        tuple: (score, category, risk_level, reason)
    """
    
    # Seuils optimisés pour distribution 15/25/60
    LUMINOSITY_FAIBLE_MAX = {faible_max:.6f}
    LUMINOSITY_MOYEN_MAX = {moyen_max:.6f}
    
    # Cas 1: Luminosité très faible
    if mean_luminosity <= LUMINOSITY_FAIBLE_MAX:
        # Critères secondaires pour affiner
        secondary_score = 0
        
        # Tendance négative = plus abandonné
        if trend < -5.0:
            secondary_score += 2
        elif trend < 0.0:
            secondary_score += 1
        
        # Moins actif = plus abandonné
        if active_months_ratio < 0.5:
            secondary_score += 2
        elif active_months_ratio < 0.8:
            secondary_score += 1
        
        if secondary_score >= 3:
            return 10, "Faible", "Élevé", f"Luminosité très faible ({{mean_luminosity:.3f}}) + critères défavorables"
        else:
            return 15, "Faible", "Élevé", f"Luminosité très faible ({{mean_luminosity:.3f}}) = Abandon probable"
    
    # Cas 2: Luminosité faible-moyenne
    elif mean_luminosity <= LUMINOSITY_MOYEN_MAX:
        # Généralement moyen, sauf si critères très favorables
        if trend > 0 and active_months_ratio > 0.8:
            return 60, "Moyen", "Modéré", f"Luminosité faible ({{mean_luminosity:.3f}}) mais critères favorables"
        else:
            return 50, "Moyen", "Modéré", f"Luminosité faible-moyenne ({{mean_luminosity:.3f}}) = Abandon possible"
    
    # Cas 3: Luminosité normale/élevée
    else:
        return 85, "Fort", "Faible", f"Luminosité normale/élevée ({{mean_luminosity:.3f}}) = Activité probable"


def calculate_viirs_score_simple_aligned(mean_luminosity):
    """
    Version simplifiée alignée (sans critères secondaires)
    
    Args:
        mean_luminosity (float): Luminosité moyenne VIIRS
    
    Returns:
        tuple: (score, category, risk_level)
    """
    
    if mean_luminosity <= {faible_max:.6f}:
        return 15, "Faible", "Élevé"
    elif mean_luminosity <= {moyen_max:.6f}:
        return 50, "Moyen", "Modéré"
    else:
        return 85, "Fort", "Faible"


def integrate_viirs_aligned(viirs_score, ndvi_score, sentinel1_score):
    """
    Intégration VIIRS alignée dans le scoring combiné
    
    Pondération V1: NDVI 33.33% + Sentinel-1 33.33% + VIIRS 33.33%
    
    Args:
        viirs_score (int): Score VIIRS (10, 50, ou 85)
        ndvi_score (float): Score NDVI (0-100)
        sentinel1_score (float): Score Sentinel-1 (0-100)
    
    Returns:
        dict: Scoring combiné optimisé
    """
    
    # Pondération égale V1
    weights = {{
        'ndvi': 0.3333,      # 33.33% NDVI
        'sentinel1': 0.3333, # 33.33% Sentinel-1
        'viirs': 0.3334      # 33.34% VIIRS (pour arrondir à 100%)
    }}
    
    # Score combiné
    combined_score = (
        ndvi_score * weights['ndvi'] +
        sentinel1_score * weights['sentinel1'] +
        viirs_score * weights['viirs']
    )
    
    return {{
        'combined_score': round(combined_score, 1),
        'components': {{
            'ndvi': {{'score': ndvi_score, 'weight': weights['ndvi'], 'contribution': ndvi_score * weights['ndvi']}},
            'sentinel1': {{'score': sentinel1_score, 'weight': weights['sentinel1'], 'contribution': sentinel1_score * weights['sentinel1']}},
            'viirs': {{'score': viirs_score, 'weight': weights['viirs'], 'contribution': viirs_score * weights['viirs']}}
        }},
        'interpretation': get_combined_interpretation_aligned(combined_score),
        'weights_used': weights
    }}


def get_combined_interpretation_aligned(score):
    """Interprète le score combiné aligné"""
    if score >= 80:
        return {{'level': 'Très faible', 'description': 'Activité très probable', 'color': '#059669'}}
    elif score >= 60:
        return {{'level': 'Faible', 'description': 'Activité probable', 'color': '#10B981'}}
    elif score >= 40:
        return {{'level': 'Modéré', 'description': 'Situation mitigée', 'color': '#3B82F6'}}
    elif score >= 20:
        return {{'level': 'Élevé', 'description': 'Abandon probable', 'color': '#FB923C'}}
    else:
        return {{'level': 'Très élevé', 'description': 'Abandon très probable', 'color': '#DC2626'}}


# Tests et exemples
if __name__ == "__main__":
    print("🌙 Test du système VIIRS aligné")
    print("-" * 40)
    
    # Test avec différentes luminosités
    test_cases = [
        {{"name": "Très sombre", "lum": 0.5, "trend": -2.0, "active": 0.3}},
        {{"name": "Sombre", "lum": 0.7, "trend": -1.0, "active": 0.6}},
        {{"name": "Moyen", "lum": 1.0, "trend": 0.0, "active": 0.8}},
        {{"name": "Lumineux", "lum": 5.0, "trend": 1.0, "active": 1.0}},
        {{"name": "Très lumineux", "lum": 15.0, "trend": 2.0, "active": 1.0}}
    ]
    
    for case in test_cases:
        score, category, risk, reason = calculate_viirs_abandon_score_aligned(
            case["lum"], case["trend"], case["active"]
        )
        print(f"{{case['name']}}: Score {{score}} - {{category}} - Risque {{risk}} - {{reason}}")
    
    print("\\n🎯 Test intégration combinée:")
    print("-" * 40)
    
    result = integrate_viirs_aligned(15, 45, 60)
    print(f"Score combiné: {{result['combined_score']}}/100")
    print(f"Interprétation: {{result['interpretation']['level']}} - {{result['interpretation']['description']}}")
'''
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'optimized_thresholds'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    impl_file = output_dir / f"viirs_aligned_implementation_{timestamp}.py"
    with open(impl_file, 'w') as f:
        f.write(code)
    
    return impl_file


def save_aligned_configuration(categories, thresholds):
    """Sauvegarde la configuration alignée"""
    config = {
        'viirs_aligned_system': {
            'method': 'aligned_scoring_with_ndvi_sentinel1',
            'logic': 'low_luminosity = low_score = high_abandonment_risk',
            'distribution_achieved': {
                'faible': {'count': len([c for c in categories if c['category'] == 'Faible']), 'percentage': 15.0},
                'moyen': {'count': len([c for c in categories if c['category'] == 'Moyen']), 'percentage': 25.0}, 
                'fort': {'count': len([c for c in categories if c['category'] == 'Fort']), 'percentage': 60.0}
            },
            'scoring_system': {
                'faible': {'score': 15, 'risk': 'Élevé', 'description': 'Luminosité très faible = Abandon probable'},
                'moyen': {'score': 50, 'risk': 'Modéré', 'description': 'Luminosité faible-moyenne = Abandon possible'},
                'fort': {'score': 85, 'risk': 'Faible', 'description': 'Luminosité normale/élevée = Activité probable'}
            },
            'thresholds': thresholds,
            'classification_details': categories
        },
        'integration_weights': {
            'ndvi': 0.3333,
            'sentinel1': 0.3333,
            'viirs': 0.3334
        },
        'metadata': {
            'creation_date': datetime.now().isoformat(),
            'method': 'aligned_scoring_system',
            'status': 'final_aligned',
            'total_fincas_analyzed': len(categories),
            'alignment': 'ndvi_sentinel1_logic'
        }
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'optimized_thresholds'
    
    config_file = output_dir / f"viirs_aligned_system_{timestamp}.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config_file


def main():
    """Fonction principale"""
    print("🌙 VIIRS SCORING ALIGNÉ")
    print("=" * 40)
    print("Aligné sur NDVI/Sentinel-1: Score BAS = Risque ÉLEVÉ")
    print("Distribution: 15% Faible, 25% Moyen, 60% Fort")
    
    try:
        # 1. Charger les données
        finca_data = load_viirs_data()
        print(f"📊 {len(finca_data)} fincas chargées")
        
        # 2. Créer le système aligné
        categories = create_aligned_scoring_system(finca_data)
        
        # 3. Afficher la classification
        display_aligned_classification(categories)
        
        # 4. Calculer les seuils
        thresholds = calculate_aligned_thresholds(categories)
        
        # 5. Générer l'implémentation
        impl_file = generate_aligned_implementation(categories, thresholds)
        
        # 6. Sauvegarder la configuration
        config_file = save_aligned_configuration(categories, thresholds)
        
        # Vérifier la distribution
        by_category = {}
        for cat in categories:
            category = cat['category']
            by_category[category] = by_category.get(category, 0) + 1
        
        total = len(categories)
        print(f"\n✅ DISTRIBUTION FINALE VÉRIFIÉE:")
        for category in ['Faible', 'Moyen', 'Fort']:
            count = by_category.get(category, 0)
            percentage = (count / total) * 100
            print(f"   • {category}: {count} fincas ({percentage:.0f}%)")
        
        print(f"\n🎯 SEUILS FINAUX ALIGNÉS:")
        print(f"   • Luminosité Faible: ≤ {thresholds['luminosity_thresholds']['faible_max']:.3f} (Score 15, Risque Élevé)")
        print(f"   • Luminosité Moyen: ≤ {thresholds['luminosity_thresholds']['moyen_max']:.3f} (Score 50, Risque Modéré)")
        print(f"   • Luminosité Fort: > {thresholds['luminosity_thresholds']['fort_min']:.3f} (Score 85, Risque Faible)")
        
        print(f"\n🎉 SYSTÈME ALIGNÉ CRÉÉ AVEC SUCCÈS!")
        print(f"📄 Configuration: {config_file}")
        print(f"💻 Implémentation: {impl_file}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
