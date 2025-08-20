#!/usr/bin/env python3
"""
🎯 Optimisation des Seuils VIIRS
Analyse la distribution des scores VIIRS et optimise les seuils pour avoir ~10% faible
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_current_viirs_data():
    """Charge les données VIIRS existantes"""
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


def analyze_current_distribution(viirs_data):
    """Analyse la distribution actuelle des scores VIIRS"""
    print(f"\n📊 ANALYSE DE LA DISTRIBUTION ACTUELLE")
    print("=" * 50)
    
    # Extraire les métriques
    luminosities = []
    scores = []
    trends = []
    active_months = []
    
    for finca in viirs_data:
        if finca['status'] == 'success':
            metrics = finca['metrics']
            luminosities.append(metrics['mean_luminosity'])
            scores.append(finca['score'])
            trends.append(metrics['trend'])
            active_months.append(metrics['active_months'] / metrics['total_months'])
    
    # Statistiques de base
    print(f"📈 Luminosité moyenne:")
    print(f"   • Min: {min(luminosities):.3f}")
    print(f"   • Max: {max(luminosities):.3f}")
    print(f"   • Moyenne: {np.mean(luminosities):.3f}")
    print(f"   • Médiane: {np.median(luminosities):.3f}")
    print(f"   • Écart-type: {np.std(luminosities):.3f}")
    
    # Distribution des scores actuels
    score_counts = pd.Series(scores).value_counts().sort_index()
    total_fincas = len(scores)
    
    print(f"\n🎯 Distribution des scores actuels:")
    for score, count in score_counts.items():
        percentage = (count / total_fincas) * 100
        print(f"   • Score {score}: {count} fincas ({percentage:.1f}%)")
    
    # Percentiles de luminosité
    percentiles = [10, 20, 30, 50, 70, 80, 90]
    print(f"\n📊 Percentiles de luminosité:")
    for p in percentiles:
        value = np.percentile(luminosities, p)
        print(f"   • P{p}: {value:.3f}")
    
    return {
        'luminosities': luminosities,
        'scores': scores,
        'trends': trends,
        'active_months': active_months,
        'total_fincas': total_fincas
    }


def calculate_optimal_thresholds(data):
    """Calcule les seuils optimaux pour avoir ~10% faible, ~20% moyen, ~70% élevé"""
    print(f"\n🎯 CALCUL DES SEUILS OPTIMAUX")
    print("=" * 40)
    
    luminosities = np.array(data['luminosities'])
    
    # Distribution cible
    target_distribution = {
        'faible': 0.10,      # 10% des fincas
        'moyen': 0.20,       # 20% des fincas  
        'eleve': 0.70        # 70% des fincas
    }
    
    print(f"🎯 Distribution cible:")
    print(f"   • Faible: {target_distribution['faible']:.0%}")
    print(f"   • Moyen: {target_distribution['moyen']:.0%}")
    print(f"   • Élevé: {target_distribution['eleve']:.0%}")
    
    # Calculer les seuils basés sur les percentiles
    # Plus la luminosité est FAIBLE, plus le risque d'abandon est ÉLEVÉ
    # Donc : Faible luminosité = Score élevé d'abandon
    
    # Seuil pour les 10% les plus sombres (score élevé d'abandon)
    threshold_high = np.percentile(luminosities, 10)  # 10% les plus faibles
    
    # Seuil pour les 30% les plus sombres (score moyen d'abandon) 
    threshold_medium = np.percentile(luminosities, 30)  # 30% les plus faibles
    
    # Le reste (70%) aura un score faible d'abandon
    
    print(f"\n💡 Seuils calculés (luminosité):")
    print(f"   • Seuil Élevé (≤{threshold_high:.3f}): 10% les plus sombres → Score abandon élevé")
    print(f"   • Seuil Moyen ({threshold_high:.3f} < x ≤ {threshold_medium:.3f}): 20% → Score abandon moyen")
    print(f"   • Seuil Faible (>{threshold_medium:.3f}): 70% les plus lumineux → Score abandon faible")
    
    return {
        'threshold_high_abandon': threshold_high,     # Luminosité faible = abandon élevé
        'threshold_medium_abandon': threshold_medium, # Luminosité moyenne = abandon moyen
        'target_distribution': target_distribution
    }


def apply_new_scoring_system(data, thresholds):
    """Applique le nouveau système de scoring avec les seuils optimisés"""
    print(f"\n🔄 APPLICATION DU NOUVEAU SYSTÈME DE SCORING")
    print("=" * 50)
    
    luminosities = data['luminosities']
    new_scores = []
    new_categories = []
    
    threshold_high = thresholds['threshold_high_abandon']
    threshold_medium = thresholds['threshold_medium_abandon']
    
    for luminosity in luminosities:
        if luminosity <= threshold_high:
            # Luminosité très faible = Abandon élevé = Score 4-5
            score = 5  # Score d'abandon élevé
            category = 'Élevé'
        elif luminosity <= threshold_medium:
            # Luminosité faible-moyenne = Abandon moyen = Score 2-3
            score = 3  # Score d'abandon moyen
            category = 'Moyen'
        else:
            # Luminosité élevée = Abandon faible = Score 0-1
            score = 1  # Score d'abandon faible
            category = 'Faible'
        
        new_scores.append(score)
        new_categories.append(category)
    
    # Analyser la nouvelle distribution
    category_counts = pd.Series(new_categories).value_counts()
    total = len(new_categories)
    
    print(f"📊 Nouvelle distribution:")
    for category in ['Faible', 'Moyen', 'Élevé']:
        count = category_counts.get(category, 0)
        percentage = (count / total) * 100
        print(f"   • {category}: {count} fincas ({percentage:.1f}%)")
    
    return new_scores, new_categories


def generate_optimized_viirs_config(thresholds):
    """Génère la configuration optimisée pour VIIRS"""
    config = {
        'viirs_optimized_thresholds': {
            'luminosity_thresholds': {
                'very_dark': thresholds['threshold_high_abandon'],      # ≤ P10 = Abandon élevé
                'dark': thresholds['threshold_medium_abandon'],         # ≤ P30 = Abandon moyen
                'moderate': thresholds['threshold_medium_abandon'] * 2, # > P30 = Abandon faible
                'bright': thresholds['threshold_medium_abandon'] * 5,   # Très lumineux
                'very_bright': thresholds['threshold_medium_abandon'] * 10  # Extrêmement lumineux
            },
            'scoring_weights': {
                'mean_luminosity': 0.40,     # Poids principal
                'trend': 0.25,               # Tendance temporelle
                'active_months': 0.20,       # Mois actifs
                'variability': 0.15          # Variabilité
            },
            'target_distribution': {
                'faible': 0.70,    # 70% abandon faible (lumineux)
                'moyen': 0.20,     # 20% abandon moyen
                'eleve': 0.10      # 10% abandon élevé (sombre)
            }
        },
        'metadata': {
            'optimization_date': datetime.now().isoformat(),
            'method': 'percentile_based_optimization',
            'target': '10_percent_high_abandon',
            'data_source': 'viirs_top20_analysis'
        }
    }
    
    return config


def save_optimized_config(config):
    """Sauvegarde la configuration optimisée"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Créer le dossier de sortie
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'optimized_thresholds'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder la configuration
    config_file = output_dir / f"viirs_optimized_thresholds_{timestamp}.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Configuration sauvegardée: {config_file}")
    return config_file


def create_distribution_visualization(data, new_scores, new_categories, thresholds):
    """Crée des visualisations de la distribution"""
    print(f"\n📊 Création des visualisations...")
    
    # Créer le dossier de sortie
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'optimized_thresholds'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configuration du graphique
    plt.style.use('default')
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Optimisation des Seuils VIIRS', fontsize=16, fontweight='bold')
    
    # 1. Distribution de la luminosité avec seuils
    ax1 = axes[0, 0]
    luminosities = data['luminosities']
    ax1.hist(luminosities, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.axvline(thresholds['threshold_high_abandon'], color='red', linestyle='--', 
                label=f'Seuil Élevé: {thresholds["threshold_high_abandon"]:.3f}')
    ax1.axvline(thresholds['threshold_medium_abandon'], color='orange', linestyle='--',
                label=f'Seuil Moyen: {thresholds["threshold_medium_abandon"]:.3f}')
    ax1.set_xlabel('Luminosité Moyenne (nW/cm²/sr)')
    ax1.set_ylabel('Nombre de Fincas')
    ax1.set_title('Distribution de la Luminosité avec Seuils')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Comparaison ancienne vs nouvelle distribution
    ax2 = axes[0, 1]
    old_scores = data['scores']
    old_counts = pd.Series(old_scores).value_counts().sort_index()
    new_counts = pd.Series(new_categories).value_counts()
    
    # Graphique en barres comparatif
    x = np.arange(len(new_counts))
    width = 0.35
    
    old_percentages = [(old_counts.get(i, 0) / len(old_scores)) * 100 for i in [0, 1, 2, 3, 4, 5]]
    new_percentages = [(new_counts.get(cat, 0) / len(new_categories)) * 100 for cat in ['Faible', 'Moyen', 'Élevé']]
    
    # Simplifier l'affichage
    ax2.bar(['Faible', 'Moyen', 'Élevé'], new_percentages, alpha=0.8, color=['green', 'orange', 'red'])
    ax2.set_ylabel('Pourcentage (%)')
    ax2.set_title('Nouvelle Distribution des Scores')
    ax2.grid(True, alpha=0.3)
    
    # Ajouter les pourcentages sur les barres
    for i, v in enumerate(new_percentages):
        ax2.text(i, v + 1, f'{v:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    # 3. Scatter plot luminosité vs nouveau score
    ax3 = axes[1, 0]
    colors = {'Faible': 'green', 'Moyen': 'orange', 'Élevé': 'red'}
    for category in ['Faible', 'Moyen', 'Élevé']:
        mask = np.array(new_categories) == category
        ax3.scatter(np.array(luminosities)[mask], np.array(new_scores)[mask], 
                   c=colors[category], label=category, alpha=0.6)
    ax3.set_xlabel('Luminosité Moyenne')
    ax3.set_ylabel('Nouveau Score d\'Abandon')
    ax3.set_title('Luminosité vs Nouveau Score')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 4. Résumé statistique
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Texte du résumé
    summary_text = f"""
RÉSUMÉ DE L'OPTIMISATION

Seuils Optimisés:
• Abandon Élevé: ≤ {thresholds['threshold_high_abandon']:.3f}
• Abandon Moyen: ≤ {thresholds['threshold_medium_abandon']:.3f}
• Abandon Faible: > {thresholds['threshold_medium_abandon']:.3f}

Distribution Cible vs Réelle:
• Faible: 70% → {new_percentages[0]:.1f}%
• Moyen: 20% → {new_percentages[1]:.1f}%
• Élevé: 10% → {new_percentages[2]:.1f}%

Données Analysées:
• Total fincas: {len(luminosities)}
• Luminosité min: {min(luminosities):.3f}
• Luminosité max: {max(luminosities):.3f}
• Luminosité moyenne: {np.mean(luminosities):.3f}
"""
    
    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes, fontsize=11,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    plt.tight_layout()
    
    # Sauvegarder le graphique
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_file = output_dir / f"viirs_threshold_optimization_{timestamp}.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Visualisation sauvegardée: {plot_file}")
    return plot_file


def main():
    """Fonction principale"""
    print("🎯 OPTIMISATION DES SEUILS VIIRS")
    print("=" * 50)
    print("Objectif: 10% Élevé, 20% Moyen, 70% Faible")
    
    try:
        # 1. Charger les données VIIRS existantes
        viirs_data = load_current_viirs_data()
        if not viirs_data:
            return
        
        # 2. Analyser la distribution actuelle
        data = analyze_current_distribution(viirs_data)
        
        # 3. Calculer les seuils optimaux
        thresholds = calculate_optimal_thresholds(data)
        
        # 4. Appliquer le nouveau système de scoring
        new_scores, new_categories = apply_new_scoring_system(data, thresholds)
        
        # 5. Générer la configuration optimisée
        config = generate_optimized_viirs_config(thresholds)
        
        # 6. Sauvegarder la configuration
        config_file = save_optimized_config(config)
        
        # 7. Créer les visualisations
        plot_file = create_distribution_visualization(data, new_scores, new_categories, thresholds)
        
        print(f"\n🎉 OPTIMISATION TERMINÉE AVEC SUCCÈS!")
        print(f"📄 Configuration: {config_file}")
        print(f"📊 Visualisation: {plot_file}")
        
        # Résumé final
        category_counts = pd.Series(new_categories).value_counts()
        total = len(new_categories)
        
        print(f"\n📈 RÉSUMÉ FINAL:")
        print(f"   • Abandon Faible: {category_counts.get('Faible', 0)} fincas ({(category_counts.get('Faible', 0)/total)*100:.1f}%)")
        print(f"   • Abandon Moyen: {category_counts.get('Moyen', 0)} fincas ({(category_counts.get('Moyen', 0)/total)*100:.1f}%)")
        print(f"   • Abandon Élevé: {category_counts.get('Élevé', 0)} fincas ({(category_counts.get('Élevé', 0)/total)*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
