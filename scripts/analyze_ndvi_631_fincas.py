#!/usr/bin/env python3
"""
Analyse la répartition NDVI avec les 631 fincas disponibles
Utilise les données d'analyse d'abandon complètes
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter
import sys
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from scoring.simple_scoring import score_vegetation_from_ndvi_summary


def load_ndvi_631_data():
    """Charge les données NDVI des 631 fincas depuis l'analyse d'abandon"""
    csv_file = Path("data/abandon_analysis_FULL/fincas_abandon_scores_REALISTIC_20250809_140234.csv")
    
    if not csv_file.exists():
        print(f"❌ Fichier non trouvé: {csv_file}")
        return None
    
    # Charger le CSV
    df = pd.read_csv(csv_file)
    
    print(f"📊 Données chargées: {len(df)} fincas")
    print(f"📋 Colonnes disponibles: {list(df.columns)}")
    
    # Vérifier les colonnes nécessaires
    required_cols = ['finca_id', 'median_ndvi', 'std_deviation', 'cv_percent']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"❌ Colonnes manquantes: {missing_cols}")
        return None
    
    # Convertir en liste de dictionnaires
    ndvi_data = []
    for _, row in df.iterrows():
        ndvi_data.append({
            'finca_id': row['finca_id'],
            'median': row['median_ndvi'],
            'std': row['std_deviation'],
            'cv': row['cv_percent'] / 100.0,  # Convertir de % à décimal
            'abandon_score': row['abandon_score'],
            'activity_status': row['activity_status']
        })
    
    return ndvi_data


def analyze_ndvi_distribution_631(ndvi_data):
    """Analyse la distribution NDVI avec les 631 fincas"""
    if not ndvi_data:
        return None
    
    print(f"🔍 ANALYSE NDVI - 631 FINCAS")
    print("=" * 60)
    
    # Statistiques de base
    medians = [item['median'] for item in ndvi_data]
    stds = [item['std'] for item in ndvi_data]
    cvs = [item['cv'] for item in ndvi_data]
    
    print(f"📈 Statistiques de base:")
    print(f"   • Total fincas: {len(ndvi_data)}")
    print(f"   • Médiane NDVI: {min(medians):.3f} - {max(medians):.3f} (moy: {np.mean(medians):.3f})")
    print(f"   • Écart-type: {min(stds):.3f} - {max(stds):.3f} (moy: {np.mean(stds):.3f})")
    print(f"   • CV: {min(cvs):.3f} - {max(cvs):.3f} (moy: {np.mean(cvs):.3f})")
    
    # Distribution par statut d'activité original
    status_counts = Counter([item['activity_status'] for item in ndvi_data])
    print(f"\n📋 Distribution par statut d'activité original:")
    for status, count in status_counts.items():
        percentage = (count / len(ndvi_data)) * 100
        print(f"   • {status}: {count} fincas ({percentage:.1f}%)")
    
    # Analyser avec la règle historique (CV)
    print(f"\n🎯 ANALYSE AVEC RÈGLE HISTORIQUE (CV)")
    print("-" * 50)
    
    scores = []
    levels = []
    
    for item in ndvi_data:
        points, level = score_vegetation_from_ndvi_summary(item['median'], item['std'])
        scores.append(points)
        levels.append(level)
    
    score_counts = Counter(scores)
    level_counts = Counter(levels)
    
    print(f"📊 Répartition par entretien végétation:")
    for points in [1, 3, 5]:
        count = score_counts.get(points, 0)
        percentage = (count / len(ndvi_data)) * 100
        label = "Faible" if points == 1 else "Moyen" if points == 3 else "Fort"
        print(f"   • {points}pt ({label}): {count} fincas ({percentage:.1f}%)")
    
    print(f"\n🏷️ Répartition par niveau:")
    for level in ['Faible', 'Moyen', 'Fort']:
        count = level_counts.get(level, 0)
        percentage = (count / len(ndvi_data)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    # Analyse détaillée par CV
    print(f"\n📈 Analyse détaillée par CV:")
    cv_ranges = [
        ("CV < 0.12", [item for item in ndvi_data if item['cv'] < 0.12]),
        ("CV 0.12-0.25", [item for item in ndvi_data if 0.12 <= item['cv'] < 0.25]),
        ("CV ≥ 0.25", [item for item in ndvi_data if item['cv'] >= 0.25])
    ]
    
    for range_name, items in cv_ranges:
        if items:
            avg_cv = np.mean([item['cv'] for item in items])
            avg_median = np.mean([item['median'] for item in items])
            print(f"   • {range_name}: {len(items)} fincas (CV moy: {avg_cv:.3f}, NDVI moy: {avg_median:.3f})")
    
    # Comparaison avec le statut d'activité original
    print(f"\n🔄 COMPARAISON AVEC STATUT ORIGINAL")
    print("-" * 50)
    
    # Créer une matrice de confusion
    confusion_matrix = {}
    for item in ndvi_data:
        original_status = item['activity_status']
        points, level = score_vegetation_from_ndvi_summary(item['median'], item['std'])
        
        if original_status not in confusion_matrix:
            confusion_matrix[original_status] = Counter()
        confusion_matrix[original_status][level] += 1
    
    print(f"📊 Matrice de confusion (Statut original → Entretien végétation):")
    for original_status in ['active', 'semi-active', 'inactive']:
        if original_status in confusion_matrix:
            print(f"   • {original_status}:")
            for level in ['Faible', 'Moyen', 'Fort']:
                count = confusion_matrix[original_status].get(level, 0)
                total = sum(confusion_matrix[original_status].values())
                percentage = (count / total) * 100 if total > 0 else 0
                print(f"     - {level}: {count} fincas ({percentage:.1f}%)")
    
    return {
        'total_fincas': len(ndvi_data),
        'cv_stats': {
            'min': min(cvs),
            'max': max(cvs),
            'mean': np.mean(cvs),
            'median': np.median(cvs)
        },
        'score_distribution': dict(score_counts),
        'level_distribution': dict(level_counts),
        'original_status_distribution': dict(status_counts),
        'confusion_matrix': {k: dict(v) for k, v in confusion_matrix.items()}
    }


def main():
    """Fonction principale"""
    print("🔍 ANALYSE NDVI - 631 FINCAS COMPLÈTES")
    print("=" * 60)
    
    # Charger les données
    ndvi_data = load_ndvi_631_data()
    
    if not ndvi_data:
        print("❌ Impossible de charger les données NDVI")
        return
    
    # Analyser la distribution
    results = analyze_ndvi_distribution_631(ndvi_data)
    
    if results:
        # Sauvegarder l'analyse
        output = {
            'analysis_type': 'ndvi_631_fincas_realistic',
            'total_fincas': results['total_fincas'],
            'cv_statistics': results['cv_stats'],
            'scoring_distribution': results['score_distribution'],
            'level_distribution': results['level_distribution'],
            'original_status_distribution': results['original_status_distribution'],
            'confusion_matrix': results['confusion_matrix']
        }
        
        output_file = Path("data/ndvi_631_analysis.json")
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Analyse sauvegardée: {output_file}")
        
        # Résumé final
        print(f"\n🎯 RÉSUMÉ FINAL - 631 FINCAS")
        print("=" * 60)
        print(f"📊 Entretien végétation (règle historique CV):")
        for level in ['Faible', 'Moyen', 'Fort']:
            count = results['level_distribution'].get(level, 0)
            percentage = (count / results['total_fincas']) * 100
            print(f"   • {level}: {count} fincas ({percentage:.1f}%)")


if __name__ == "__main__":
    main()
