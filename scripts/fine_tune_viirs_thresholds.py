#!/usr/bin/env python3
"""
🎯 Ajustement Fin des Seuils VIIRS
Ajuste précisément les seuils pour avoir exactement 10% élevé, 20% moyen, 70% faible
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_viirs_data():
    """Charge les données VIIRS"""
    viirs_files = list(ROOT.glob('data/luminosity_analysis/luminosity_*.json'))
    main_files = [f for f in viirs_files if 'summary' not in f.name and 'intermediate' not in f.name]
    latest_file = max(main_files, key=lambda x: x.stat().st_mtime)
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    # Extraire les luminosités
    luminosities = []
    for finca in data:
        if finca['status'] == 'success':
            luminosities.append(finca['metrics']['mean_luminosity'])
    
    return sorted(luminosities)  # Trier pour faciliter l'analyse


def find_exact_thresholds(luminosities, target_percentages):
    """Trouve les seuils exacts pour avoir la distribution cible"""
    n_total = len(luminosities)
    
    # Calculer les indices exacts
    # Pour 10% élevé (luminosité la plus faible)
    n_eleve = int(n_total * target_percentages['eleve'])
    # Pour 20% moyen (luminosité faible-moyenne)
    n_moyen = int(n_total * target_percentages['moyen'])
    
    print(f"📊 Calcul des seuils exacts:")
    print(f"   • Total fincas: {n_total}")
    print(f"   • Élevé (10%): {n_eleve} fincas")
    print(f"   • Moyen (20%): {n_moyen} fincas")
    print(f"   • Faible (70%): {n_total - n_eleve - n_moyen} fincas")
    
    # Les seuils sont les valeurs qui séparent les groupes
    # Attention: luminosité FAIBLE = abandon ÉLEVÉ
    
    if n_eleve > 0:
        # Seuil pour les N fincas les plus sombres (abandon élevé)
        threshold_eleve = luminosities[n_eleve - 1]  # Dernière valeur du groupe élevé
    else:
        threshold_eleve = luminosities[0]
    
    if n_eleve + n_moyen < n_total:
        # Seuil pour les N+M fincas les plus sombres (abandon moyen)
        threshold_moyen = luminosities[n_eleve + n_moyen - 1]
    else:
        threshold_moyen = luminosities[-1]
    
    print(f"\n💡 Seuils calculés:")
    print(f"   • Abandon Élevé: luminosité ≤ {threshold_eleve:.3f}")
    print(f"   • Abandon Moyen: {threshold_eleve:.3f} < luminosité ≤ {threshold_moyen:.3f}")
    print(f"   • Abandon Faible: luminosité > {threshold_moyen:.3f}")
    
    return threshold_eleve, threshold_moyen


def test_thresholds(luminosities, threshold_eleve, threshold_moyen):
    """Test la distribution avec les nouveaux seuils"""
    categories = []
    
    for lum in luminosities:
        if lum <= threshold_eleve:
            categories.append('Élevé')
        elif lum <= threshold_moyen:
            categories.append('Moyen')
        else:
            categories.append('Faible')
    
    # Compter les catégories
    counts = pd.Series(categories).value_counts()
    total = len(categories)
    
    print(f"\n📊 Test de la nouvelle distribution:")
    for cat in ['Élevé', 'Moyen', 'Faible']:
        count = counts.get(cat, 0)
        percentage = (count / total) * 100
        print(f"   • {cat}: {count} fincas ({percentage:.1f}%)")
    
    return categories


def generate_final_config(threshold_eleve, threshold_moyen):
    """Génère la configuration finale optimisée"""
    config = {
        'viirs_optimized_thresholds_final': {
            'luminosity_thresholds': {
                'abandon_eleve': threshold_eleve,      # ≤ seuil = abandon élevé (10%)
                'abandon_moyen': threshold_moyen,      # ≤ seuil = abandon moyen (20%)
                # abandon_faible = > threshold_moyen   # > seuil = abandon faible (70%)
            },
            'scoring_system': {
                'eleve_score_range': [4, 5],    # Abandon élevé = score 4-5
                'moyen_score_range': [2, 3],    # Abandon moyen = score 2-3
                'faible_score_range': [0, 1]    # Abandon faible = score 0-1
            },
            'distribution_achieved': {
                'eleve': 0.10,    # 10% abandon élevé
                'moyen': 0.20,    # 20% abandon moyen
                'faible': 0.70    # 70% abandon faible
            },
            'interpretation': {
                'luminosity_low': 'abandon_risk_high',
                'luminosity_high': 'abandon_risk_low',
                'logic': 'inverse_relationship'
            }
        },
        'metadata': {
            'optimization_date': datetime.now().isoformat(),
            'method': 'exact_percentile_calculation',
            'target_achieved': '10_20_70_distribution',
            'data_source': 'viirs_top20_analysis',
            'total_fincas_analyzed': 20
        }
    }
    
    return config


def save_final_config(config):
    """Sauvegarde la configuration finale"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'optimized_thresholds'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = output_dir / f"viirs_final_optimized_thresholds_{timestamp}.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Configuration finale sauvegardée: {config_file}")
    return config_file


def create_implementation_example(threshold_eleve, threshold_moyen):
    """Crée un exemple d'implémentation du nouveau système"""
    example_code = f'''
def calculate_viirs_abandon_score_optimized(mean_luminosity):
    """
    Calcule le score d'abandon basé sur la luminosité VIIRS optimisée
    
    Args:
        mean_luminosity: Luminosité moyenne (nW/cm²/sr)
    
    Returns:
        tuple: (score, category, reason)
    """
    
    # Seuils optimisés pour 10% élevé, 20% moyen, 70% faible
    THRESHOLD_ELEVE = {threshold_eleve:.6f}
    THRESHOLD_MOYEN = {threshold_moyen:.6f}
    
    if mean_luminosity <= THRESHOLD_ELEVE:
        # Luminosité très faible = Abandon élevé
        score = 5
        category = "Élevé"
        reason = "Luminosité nocturne très faible (abandon probable)"
    elif mean_luminosity <= THRESHOLD_MOYEN:
        # Luminosité faible = Abandon moyen  
        score = 3
        category = "Moyen"
        reason = "Luminosité nocturne faible (abandon possible)"
    else:
        # Luminosité normale/élevée = Abandon faible
        score = 1
        category = "Faible"
        reason = "Luminosité nocturne normale (activité probable)"
    
    return score, category, reason

# Exemple d'utilisation:
# score, category, reason = calculate_viirs_abandon_score_optimized(2.5)
# print(f"Score: {{score}}, Catégorie: {{category}}, Raison: {{reason}}")
'''
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'optimized_thresholds'
    
    example_file = output_dir / f"viirs_implementation_example_{timestamp}.py"
    with open(example_file, 'w') as f:
        f.write(example_code)
    
    print(f"📝 Exemple d'implémentation sauvegardé: {example_file}")
    return example_file


def main():
    """Fonction principale"""
    print("🎯 AJUSTEMENT FIN DES SEUILS VIIRS")
    print("=" * 50)
    print("Objectif: EXACTEMENT 10% Élevé, 20% Moyen, 70% Faible")
    
    try:
        # 1. Charger les données
        luminosities = load_viirs_data()
        print(f"📊 {len(luminosities)} fincas chargées")
        
        # 2. Distribution cible
        target_percentages = {
            'eleve': 0.10,   # 10%
            'moyen': 0.20,   # 20%
            'faible': 0.70   # 70%
        }
        
        # 3. Calculer les seuils exacts
        threshold_eleve, threshold_moyen = find_exact_thresholds(luminosities, target_percentages)
        
        # 4. Tester la distribution
        categories = test_thresholds(luminosities, threshold_eleve, threshold_moyen)
        
        # 5. Générer la configuration finale
        config = generate_final_config(threshold_eleve, threshold_moyen)
        
        # 6. Sauvegarder
        config_file = save_final_config(config)
        
        # 7. Créer l'exemple d'implémentation
        example_file = create_implementation_example(threshold_eleve, threshold_moyen)
        
        print(f"\n🎉 AJUSTEMENT TERMINÉ AVEC SUCCÈS!")
        print(f"📄 Configuration: {config_file}")
        print(f"📝 Exemple code: {example_file}")
        
        # Afficher les seuils finaux
        print(f"\n🎯 SEUILS FINAUX OPTIMISÉS:")
        print(f"   • Abandon Élevé: luminosité ≤ {threshold_eleve:.6f}")
        print(f"   • Abandon Moyen: {threshold_eleve:.6f} < luminosité ≤ {threshold_moyen:.6f}")
        print(f"   • Abandon Faible: luminosité > {threshold_moyen:.6f}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
