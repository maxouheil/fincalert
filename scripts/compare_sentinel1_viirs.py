#!/usr/bin/env python3
"""
🔬 Comparaison Sentinel-1 vs VIIRS
Compare les données d'activité radar et de luminosité nocturne
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from scipy.stats import pearsonr, spearmanr

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_viirs_data():
    """Charge les données VIIRS"""
    data_dir = ROOT / 'data' / 'luminosity_analysis'
    json_files = [f for f in data_dir.glob('luminosity_top20_*.json') if 'summary' not in f.name]
    
    if not json_files:
        raise FileNotFoundError("Aucun fichier VIIRS trouvé")
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 VIIRS: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        viirs_data = json.load(f)
    
    return viirs_data


def load_sentinel1_data():
    """Charge les données Sentinel-1"""
    data_dir = ROOT / 'data' / 'sentinel1_analysis'
    json_files = list(data_dir.glob('sentinel1_analysis_summary_*.json'))
    
    if not json_files:
        raise FileNotFoundError("Aucun fichier Sentinel-1 trouvé")
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"📡 Sentinel-1: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        s1_data = json.load(f)
    
    return s1_data


def normalize_activity_scores(viirs_data, s1_data):
    """Normalise les scores pour la comparaison"""
    # Créer un dictionnaire pour faciliter la comparaison
    comparison_data = []
    
    # Index des données Sentinel-1 par finca_id
    s1_dict = {finca['finca_id']: finca for finca in s1_data['fincas']}
    
    for viirs_finca in viirs_data:
        if viirs_finca['status'] == 'success':
            finca_id = viirs_finca['finca_id']
            
            if finca_id in s1_dict:
                s1_finca = s1_dict[finca_id]
                
                # Données VIIRS
                viirs_luminosity = viirs_finca['metrics']['mean_luminosity']
                viirs_score = viirs_finca['score']  # Score d'abandon (0-5)
                
                # Données Sentinel-1
                s1_vv = s1_finca['avg_vv']
                s1_activity = s1_finca['overall_activity']
                
                # Normaliser les scores sur une échelle 0-100
                viirs_normalized = normalize_viirs_score(viirs_luminosity)
                s1_normalized = normalize_s1_score(s1_vv)
                
                comparison_data.append({
                    'finca_id': finca_id,
                    'viirs_luminosity': viirs_luminosity,
                    'viirs_score': viirs_score,
                    'viirs_normalized': viirs_normalized,
                    's1_vv': s1_vv,
                    's1_activity': s1_activity,
                    's1_normalized': s1_normalized,
                    'coordinates': viirs_finca['coordinates']
                })
    
    return comparison_data


def normalize_viirs_score(luminosity):
    """Normalise la luminosité VIIRS sur 0-100 (100 = plus actif)"""
    # Plus la luminosité est élevée, plus l'activité est élevée
    # Utiliser une échelle logarithmique pour les valeurs VIIRS
    if luminosity <= 0:
        return 0
    elif luminosity >= 20:
        return 100
    else:
        return min(100, (np.log(luminosity + 1) / np.log(21)) * 100)


def normalize_s1_score(vv_value):
    """Normalise le VV Sentinel-1 sur 0-100 (100 = plus actif)"""
    # Plus le VV est élevé (moins négatif), plus l'activité est élevée
    # VV typique: -25 dB (très faible) à -5 dB (très élevée)
    if vv_value <= -25:
        return 0
    elif vv_value >= -5:
        return 100
    else:
        return ((vv_value + 25) / 20) * 100


def calculate_correlations(comparison_data):
    """Calcule les corrélations entre les différentes métriques"""
    df = pd.DataFrame(comparison_data)
    
    correlations = {}
    
    # Corrélation Luminosité VIIRS vs VV Sentinel-1
    viirs_lum = df['viirs_luminosity'].values
    s1_vv = df['s1_vv'].values
    correlations['viirs_lum_vs_s1_vv'] = {
        'pearson': pearsonr(viirs_lum, s1_vv),
        'spearman': spearmanr(viirs_lum, s1_vv)
    }
    
    # Corrélation Scores normalisés
    viirs_norm = df['viirs_normalized'].values
    s1_norm = df['s1_normalized'].values
    correlations['normalized_scores'] = {
        'pearson': pearsonr(viirs_norm, s1_norm),
        'spearman': spearmanr(viirs_norm, s1_norm)
    }
    
    # Corrélation Score VIIRS vs VV Sentinel-1
    viirs_score = df['viirs_score'].values
    correlations['viirs_score_vs_s1_vv'] = {
        'pearson': pearsonr(viirs_score, s1_vv),
        'spearman': spearmanr(viirs_score, s1_vv)
    }
    
    return correlations, df


def create_comparison_plots(df, output_dir):
    """Crée des graphiques de comparaison"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('🔬 Comparaison Sentinel-1 vs VIIRS', fontsize=16, fontweight='bold')
    
    # 1. Luminosité VIIRS vs VV Sentinel-1
    ax1.scatter(df['viirs_luminosity'], df['s1_vv'], alpha=0.7, s=100)
    ax1.set_xlabel('Luminosité VIIRS (moyenne)')
    ax1.set_ylabel('VV Sentinel-1 (dB)')
    ax1.set_title('Luminosité vs Backscatter Radar')
    ax1.grid(True, alpha=0.3)
    
    # Ajouter les labels des fincas
    for _, row in df.iterrows():
        ax1.annotate(row['finca_id'], 
                    (row['viirs_luminosity'], row['s1_vv']),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, alpha=0.7)
    
    # 2. Scores normalisés
    ax2.scatter(df['viirs_normalized'], df['s1_normalized'], alpha=0.7, s=100, color='orange')
    ax2.set_xlabel('Score VIIRS Normalisé (0-100)')
    ax2.set_ylabel('Score Sentinel-1 Normalisé (0-100)')
    ax2.set_title('Scores d\'Activité Normalisés')
    ax2.grid(True, alpha=0.3)
    
    # Ligne de corrélation parfaite
    ax2.plot([0, 100], [0, 100], 'r--', alpha=0.5, label='Corrélation parfaite')
    ax2.legend()
    
    # 3. Distribution des activités
    activities = df['s1_activity'].value_counts()
    ax3.bar(activities.index, activities.values, color=['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc'])
    ax3.set_xlabel('Niveau d\'Activité Sentinel-1')
    ax3.set_ylabel('Nombre de Fincas')
    ax3.set_title('Distribution des Niveaux d\'Activité')
    ax3.tick_params(axis='x', rotation=45)
    
    # 4. Score VIIRS vs VV Sentinel-1
    colors = df['viirs_score'].map({0: 'green', 2: 'orange', 3: 'red', 4: 'darkred'})
    ax4.scatter(df['viirs_score'], df['s1_vv'], c=colors, alpha=0.7, s=100)
    ax4.set_xlabel('Score d\'Abandon VIIRS (0-5)')
    ax4.set_ylabel('VV Sentinel-1 (dB)')
    ax4.set_title('Score d\'Abandon vs Backscatter')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Sauvegarder
    output_file = output_dir / 'sentinel1_viirs_comparison.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    return output_file


def create_concordance_analysis(comparison_data, correlations, output_dir):
    """Crée une analyse de concordance détaillée"""
    analysis = {
        'analysis_date': datetime.now().isoformat(),
        'total_fincas': len(comparison_data),
        'correlations': {},
        'concordance_summary': {},
        'fincas_analysis': comparison_data
    }
    
    # Formater les corrélations
    for key, corr in correlations.items():
        analysis['correlations'][key] = {
            'pearson_r': float(corr['pearson'][0]),
            'pearson_p': float(corr['pearson'][1]),
            'spearman_r': float(corr['spearman'][0]),
            'spearman_p': float(corr['spearman'][1])
        }
    
    # Analyse de concordance
    df = pd.DataFrame(comparison_data)
    
    # Classifier les fincas en catégories d'activité
    viirs_high = df['viirs_normalized'] > 60
    viirs_low = df['viirs_normalized'] < 40
    s1_high = df['s1_normalized'] > 60
    s1_low = df['s1_normalized'] < 40
    
    concordant_high = (viirs_high & s1_high).sum()
    concordant_low = (viirs_low & s1_low).sum()
    discordant = ((viirs_high & s1_low) | (viirs_low & s1_high)).sum()
    
    analysis['concordance_summary'] = {
        'concordant_high_activity': int(concordant_high),
        'concordant_low_activity': int(concordant_low),
        'discordant': int(discordant),
        'concordance_rate': float((concordant_high + concordant_low) / len(comparison_data))
    }
    
    # Sauvegarder l'analyse
    output_file = output_dir / f"concordance_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    return analysis, output_file


def print_analysis_summary(correlations, concordance):
    """Affiche un résumé de l'analyse"""
    print(f"\n🔬 ANALYSE DE CONCORDANCE")
    print("=" * 50)
    
    # Corrélations
    print(f"📊 CORRÉLATIONS:")
    for key, corr in correlations.items():
        pearson_r = corr['pearson'][0]
        pearson_p = corr['pearson'][1]
        print(f"   • {key}:")
        print(f"     Pearson: r={pearson_r:.3f}, p={pearson_p:.3f}")
        
        if pearson_p < 0.05:
            if abs(pearson_r) > 0.7:
                strength = "forte"
            elif abs(pearson_r) > 0.4:
                strength = "modérée"
            else:
                strength = "faible"
            print(f"     ✅ Corrélation {strength} et significative")
        else:
            print(f"     ❌ Pas de corrélation significative")
    
    # Concordance
    print(f"\n🎯 CONCORDANCE:")
    concordance_rate = concordance['concordance_rate']
    print(f"   • Taux de concordance: {concordance_rate:.1%}")
    print(f"   • Activité élevée concordante: {concordance['concordant_high_activity']} fincas")
    print(f"   • Activité faible concordante: {concordance['concordant_low_activity']} fincas")
    print(f"   • Résultats discordants: {concordance['discordant']} fincas")
    
    if concordance_rate > 0.7:
        print(f"   ✅ Excellente concordance entre les deux méthodes")
    elif concordance_rate > 0.5:
        print(f"   ⚠️  Concordance modérée")
    else:
        print(f"   ❌ Faible concordance")


def main():
    """Fonction principale"""
    print("🔬 COMPARAISON SENTINEL-1 vs VIIRS")
    print("=" * 60)
    print("Analyse de concordance entre radar et luminosité nocturne")
    
    try:
        # Charger les données
        print("\n📊 Chargement des données...")
        viirs_data = load_viirs_data()
        s1_data = load_sentinel1_data()
        
        # Normaliser et comparer
        print("🔄 Normalisation et comparaison...")
        comparison_data = normalize_activity_scores(viirs_data, s1_data)
        
        if not comparison_data:
            print("❌ Aucune donnée commune trouvée")
            return
        
        print(f"📈 {len(comparison_data)} fincas à comparer")
        
        # Calculer les corrélations
        correlations, df = calculate_correlations(comparison_data)
        
        # Créer le dossier de sortie
        output_dir = ROOT / 'data' / 'comparison_analysis'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Créer les graphiques
        print("📈 Création des graphiques...")
        plot_file = create_comparison_plots(df, output_dir)
        print(f"   ✅ Graphiques: {plot_file.name}")
        
        # Analyse de concordance
        print("🔬 Analyse de concordance...")
        analysis, analysis_file = create_concordance_analysis(comparison_data, correlations, output_dir)
        print(f"   ✅ Analyse: {analysis_file.name}")
        
        # Afficher le résumé
        print_analysis_summary(correlations, analysis['concordance_summary'])
        
        print(f"\n🎉 Analyse terminée!")
        print(f"📁 Résultats dans: {output_dir}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    main()
