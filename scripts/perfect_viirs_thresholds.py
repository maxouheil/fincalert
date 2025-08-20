#!/usr/bin/env python3
"""
🎯 Seuils VIIRS Parfaits
Calcule les seuils parfaits pour avoir EXACTEMENT 10% élevé
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_and_analyze_viirs():
    """Charge et analyse les données VIIRS"""
    viirs_files = list(ROOT.glob('data/luminosity_analysis/luminosity_*.json'))
    main_files = [f for f in viirs_files if 'summary' not in f.name and 'intermediate' not in f.name]
    latest_file = max(main_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    # Extraire les luminosités avec les IDs
    finca_data = []
    for finca in data:
        if finca['status'] == 'success':
            finca_data.append({
                'id': finca['finca_id'],
                'luminosity': finca['metrics']['mean_luminosity']
            })
    
    # Trier par luminosité (du plus sombre au plus lumineux)
    finca_data.sort(key=lambda x: x['luminosity'])
    
    return finca_data


def calculate_perfect_thresholds(finca_data):
    """Calcule les seuils parfaits pour 10%, 20%, 70%"""
    n_total = len(finca_data)
    
    # Pour 10% élevé (abandon élevé) = 2 fincas sur 20
    n_eleve = int(np.ceil(n_total * 0.10))  # Arrondir vers le haut
    
    # Pour 20% moyen (abandon moyen) = 4 fincas sur 20  
    n_moyen = int(np.round(n_total * 0.20))
    
    print(f"📊 Calcul parfait:")
    print(f"   • Total: {n_total} fincas")
    print(f"   • Élevé (10%): {n_eleve} fincas")
    print(f"   • Moyen (20%): {n_moyen} fincas")
    print(f"   • Faible (70%): {n_total - n_eleve - n_moyen} fincas")
    
    # Afficher les fincas dans chaque catégorie
    print(f"\n📋 Répartition des fincas:")
    
    print(f"🔴 Abandon ÉLEVÉ ({n_eleve} fincas):")
    for i in range(n_eleve):
        finca = finca_data[i]
        print(f"   • {finca['id']}: {finca['luminosity']:.3f}")
    
    print(f"\n🟡 Abandon MOYEN ({n_moyen} fincas):")
    for i in range(n_eleve, n_eleve + n_moyen):
        finca = finca_data[i]
        print(f"   • {finca['id']}: {finca['luminosity']:.3f}")
    
    print(f"\n🟢 Abandon FAIBLE ({n_total - n_eleve - n_moyen} fincas):")
    for i in range(n_eleve + n_moyen, n_total):
        finca = finca_data[i]
        print(f"   • {finca['id']}: {finca['luminosity']:.3f}")
    
    # Calculer les seuils
    if n_eleve > 0:
        # Seuil entre élevé et moyen
        threshold_eleve = (finca_data[n_eleve - 1]['luminosity'] + finca_data[n_eleve]['luminosity']) / 2
    else:
        threshold_eleve = finca_data[0]['luminosity']
    
    if n_eleve + n_moyen < n_total:
        # Seuil entre moyen et faible
        threshold_moyen = (finca_data[n_eleve + n_moyen - 1]['luminosity'] + finca_data[n_eleve + n_moyen]['luminosity']) / 2
    else:
        threshold_moyen = finca_data[-1]['luminosity']
    
    print(f"\n💡 Seuils parfaits calculés:")
    print(f"   • Élevé: luminosité ≤ {threshold_eleve:.6f}")
    print(f"   • Moyen: {threshold_eleve:.6f} < luminosité ≤ {threshold_moyen:.6f}")
    print(f"   • Faible: luminosité > {threshold_moyen:.6f}")
    
    return threshold_eleve, threshold_moyen, n_eleve, n_moyen


def test_perfect_distribution(finca_data, threshold_eleve, threshold_moyen):
    """Teste la distribution parfaite"""
    categories = {'Élevé': 0, 'Moyen': 0, 'Faible': 0}
    
    for finca in finca_data:
        lum = finca['luminosity']
        if lum <= threshold_eleve:
            categories['Élevé'] += 1
        elif lum <= threshold_moyen:
            categories['Moyen'] += 1
        else:
            categories['Faible'] += 1
    
    total = len(finca_data)
    print(f"\n✅ Test de la distribution parfaite:")
    for cat, count in categories.items():
        percentage = (count / total) * 100
        print(f"   • {cat}: {count} fincas ({percentage:.1f}%)")
    
    return categories


def generate_perfect_config(threshold_eleve, threshold_moyen, n_eleve, n_moyen):
    """Génère la configuration parfaite"""
    config = {
        'viirs_perfect_thresholds': {
            'luminosity_thresholds': {
                'abandon_eleve_max': threshold_eleve,
                'abandon_moyen_max': threshold_moyen
            },
            'scoring_function': {
                'eleve': {'luminosity_range': f'≤ {threshold_eleve:.6f}', 'score': 5, 'percentage': 10.0},
                'moyen': {'luminosity_range': f'{threshold_eleve:.6f} < x ≤ {threshold_moyen:.6f}', 'score': 3, 'percentage': 20.0},
                'faible': {'luminosity_range': f'> {threshold_moyen:.6f}', 'score': 1, 'percentage': 70.0}
            },
            'distribution_perfect': {
                'eleve_count': n_eleve,
                'moyen_count': n_moyen,
                'faible_count': 20 - n_eleve - n_moyen,
                'total_fincas': 20
            }
        },
        'implementation': {
            'logic': 'Lower luminosity = Higher abandonment risk',
            'interpretation': 'Dark areas indicate potential abandonment',
            'scoring_scale': '1 (low risk) to 5 (high risk)'
        },
        'metadata': {
            'optimization_date': datetime.now().isoformat(),
            'method': 'perfect_percentile_distribution',
            'achieved_distribution': '10_20_70_exact',
            'data_source': 'viirs_top20_final'
        }
    }
    
    return config


def save_perfect_config(config):
    """Sauvegarde la configuration parfaite"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'optimized_thresholds'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = output_dir / f"viirs_perfect_thresholds_{timestamp}.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config_file


def create_perfect_implementation(threshold_eleve, threshold_moyen):
    """Crée l'implémentation parfaite"""
    code = f'''#!/usr/bin/env python3
"""
🌙 VIIRS Scoring Optimisé - Distribution Parfaite 10/20/70
Implémentation des seuils optimisés pour VIIRS
"""

def calculate_viirs_abandon_score_perfect(mean_luminosity):
    """
    Calcule le score d'abandon VIIRS avec seuils optimisés
    
    Distribution: 10% Élevé, 20% Moyen, 70% Faible
    
    Args:
        mean_luminosity (float): Luminosité moyenne VIIRS (nW/cm²/sr)
    
    Returns:
        tuple: (score, category, percentage_group)
    """
    
    # Seuils optimisés pour distribution parfaite
    THRESHOLD_ELEVE = {threshold_eleve:.6f}  # 10% les plus sombres
    THRESHOLD_MOYEN = {threshold_moyen:.6f}  # 30% les plus sombres
    
    if mean_luminosity <= THRESHOLD_ELEVE:
        return 5, "Élevé", "10% les plus sombres (abandon très probable)"
    elif mean_luminosity <= THRESHOLD_MOYEN:
        return 3, "Moyen", "20% moyennement sombres (abandon possible)"
    else:
        return 1, "Faible", "70% les plus lumineux (activité probable)"


def integrate_viirs_in_combined_scoring(viirs_score, ndvi_score, sentinel1_score):
    """
    Intègre le score VIIRS dans le scoring combiné
    
    Args:
        viirs_score (int): Score VIIRS (1, 3, ou 5)
        ndvi_score (float): Score NDVI (0-100)
        sentinel1_score (float): Score Sentinel-1 (0-100)
    
    Returns:
        dict: Scoring combiné avec VIIRS
    """
    
    # Pondération suggérée
    weights = {{
        'ndvi': 0.50,      # 50% NDVI (principal)
        'sentinel1': 0.35,  # 35% Sentinel-1
        'viirs': 0.15      # 15% VIIRS (données secondaires)
    }}
    
    # Normaliser le score VIIRS sur 100
    viirs_normalized = (viirs_score - 1) * 25  # 1->0, 3->50, 5->100
    
    # Score combiné
    combined_score = (
        ndvi_score * weights['ndvi'] +
        sentinel1_score * weights['sentinel1'] +
        viirs_normalized * weights['viirs']
    )
    
    return {{
        'combined_score': combined_score,
        'components': {{
            'ndvi': {{'score': ndvi_score, 'weight': weights['ndvi']}},
            'sentinel1': {{'score': sentinel1_score, 'weight': weights['sentinel1']}},
            'viirs': {{'score': viirs_normalized, 'weight': weights['viirs']}}
        }},
        'weights_used': weights
    }}


# Exemple d'utilisation
if __name__ == "__main__":
    # Test avec différentes luminosités
    test_luminosities = [0.5, 0.75, 1.0, 2.0, 5.0, 10.0]
    
    print("🌙 Test des seuils VIIRS optimisés:")
    print("-" * 50)
    
    for lum in test_luminosities:
        score, category, group = calculate_viirs_abandon_score_perfect(lum)
        print(f"Luminosité {{lum:4.1f}}: Score {{score}} - {{category}} - {{group}}")
    
    print("\\n🎯 Intégration dans scoring combiné:")
    print("-" * 50)
    
    # Exemple avec scores fictifs
    result = integrate_viirs_in_combined_scoring(
        viirs_score=3,     # Moyen
        ndvi_score=45,     # Moyen
        sentinel1_score=60 # Élevé
    )
    
    print(f"Score combiné: {{result['combined_score']:.1f}}/100")
    for comp, data in result['components'].items():
        print(f"  {{comp.upper()}}: {{data['score']:.1f}} (poids: {{data['weight']:.0%}})")
'''
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'optimized_thresholds'
    
    impl_file = output_dir / f"viirs_perfect_implementation_{timestamp}.py"
    with open(impl_file, 'w') as f:
        f.write(code)
    
    return impl_file


def main():
    """Fonction principale"""
    print("🎯 SEUILS VIIRS PARFAITS")
    print("=" * 40)
    print("Objectif: EXACTEMENT 10% Élevé, 20% Moyen, 70% Faible")
    
    try:
        # 1. Charger et analyser
        finca_data = load_and_analyze_viirs()
        
        # 2. Calculer les seuils parfaits
        threshold_eleve, threshold_moyen, n_eleve, n_moyen = calculate_perfect_thresholds(finca_data)
        
        # 3. Tester la distribution
        test_perfect_distribution(finca_data, threshold_eleve, threshold_moyen)
        
        # 4. Générer la config parfaite
        config = generate_perfect_config(threshold_eleve, threshold_moyen, n_eleve, n_moyen)
        
        # 5. Sauvegarder
        config_file = save_perfect_config(config)
        
        # 6. Créer l'implémentation
        impl_file = create_perfect_implementation(threshold_eleve, threshold_moyen)
        
        print(f"\n🎉 SEUILS PARFAITS CALCULÉS!")
        print(f"📄 Config: {config_file}")
        print(f"💻 Code: {impl_file}")
        
        print(f"\n🎯 RÉSUMÉ FINAL:")
        print(f"   • Abandon Élevé: ≤ {threshold_eleve:.6f} ({n_eleve} fincas, 10%)")
        print(f"   • Abandon Moyen: ≤ {threshold_moyen:.6f} ({n_moyen} fincas, 20%)")
        print(f"   • Abandon Faible: > {threshold_moyen:.6f} ({20-n_eleve-n_moyen} fincas, 70%)")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
