#!/usr/bin/env python3
"""
Analyse la répartition par critère du système de scoring simple
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import sys
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from scoring.simple_scoring import score_viirs, score_radar, score_vegetation_from_ndvi_summary
import numpy as np


def load_viirs_data():
    """Charge les données VIIRS"""
    viirs_file = Path("data/luminosity_analysis/luminosity_top20_20250819_223705.json")
    if not viirs_file.exists():
        return []
    
    with open(viirs_file, 'r') as f:
        data = json.load(f)
    
    # Le fichier VIIRS est une liste directe
    return data if isinstance(data, list) else []


def load_sentinel1_data():
    """Charge les données Sentinel-1"""
    s1_dir = Path("data/sentinel1_all_fincas_6months")
    s1_files = list(s1_dir.glob("sentinel1_all_fincas_6months_*.json"))
    
    if not s1_files:
        return []
    
    latest_file = sorted(s1_files)[-1]
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data.get('fincas', [])


def load_ndvi_data():
    """Charge les données NDVI brutes (médiane + std) depuis les fichiers individuels"""
    ndvi_dir = Path("data/ndvi")
    ndvi_data = []
    
    for finca_dir in ndvi_dir.iterdir():
        if finca_dir.is_dir():
            summary_file = finca_dir / "summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file, 'r') as f:
                        data = json.load(f)
                    
                    if 'summary' in data:
                        summary = data['summary']
                        if 'median' in summary and 'std' in summary:
                            ndvi_data.append({
                                'finca_id': finca_dir.name,
                                'median': summary['median'],
                                'std': summary['std'],
                                'cv': (summary['std'] / summary['median']) if summary['median'] > 0 else 0
                            })
                except Exception as e:
                    print(f"⚠️ Erreur lecture {summary_file}: {e}")
    
    return ndvi_data


def analyze_viirs_distribution(viirs_data):
    """Analyse la distribution VIIRS"""
    if not viirs_data:
        return None
    
    # Extraire les luminosités depuis la structure VIIRS
    luminosities = []
    for f in viirs_data:
        if f.get('status') == 'success' and 'metrics' in f:
            mean_luminosity = f['metrics'].get('mean_luminosity')
            if mean_luminosity is not None:
                luminosities.append(mean_luminosity)
    
    if not luminosities:
        print(f"📊 LUMINOSITÉ VIIRS")
        print(f"=" * 50)
        print(f"❌ Aucune donnée de luminosité trouvée")
        return None
    
    print(f"📊 LUMINOSITÉ VIIRS")
    print(f"=" * 50)
    print(f"📈 Données analysées: {len(luminosities)}")
    print(f"📊 Valeurs min/max: {min(luminosities):.3f} / {max(luminosities):.3f}")
    print(f"📊 Valeur moyenne: {np.mean(luminosities):.3f}")
    
    # Calculer les scores
    scores = []
    levels = []
    
    for finca in viirs_data:
        if finca.get('status') == 'success' and 'metrics' in finca:
            mean_luminosity = finca['metrics'].get('mean_luminosity')
            if mean_luminosity is not None:
                points, level = score_viirs(mean_luminosity)
                scores.append(points)
                levels.append(level)
    
    # Analyser la distribution
    score_counts = Counter(scores)
    level_counts = Counter(levels)
    total = len(scores)
    
    print(f"\n🎯 Répartition par points:")
    for points in [1, 3, 5]:
        count = score_counts.get(points, 0)
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"   • {points} point ({'Faible' if points == 1 else 'Moyen' if points == 3 else 'Fort'}): {count} fincas ({percentage:.1f}%)")
    
    print(f"\n🏷️ Répartition par niveau:")
    for level in ['Faible', 'Moyen', 'Fort']:
        count = level_counts.get(level, 0)
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    return {
        'total': total,
        'min_luminosity': min(luminosities),
        'max_luminosity': max(luminosities),
        'mean_luminosity': np.mean(luminosities),
        'score_distribution': dict(score_counts),
        'level_distribution': dict(level_counts)
    }


def analyze_sentinel1_distribution(sentinel1_data):
    """Analyse la distribution Sentinel-1"""
    if not sentinel1_data:
        return None
    
    vv_values = [f['sentinel1_6months']['vv_mean'] for f in sentinel1_data 
                if f.get('status') == 'success' and 'sentinel1_6months' in f]
    
    print(f"📊 ACTIVITÉ RADAR SENTINEL-1")
    print(f"=" * 50)
    print(f"📈 Données analysées: {len(vv_values)}")
    print(f"📊 Valeurs min/max: {min(vv_values):.3f} / {max(vv_values):.3f}")
    print(f"📊 Valeur moyenne: {np.mean(vv_values):.3f}")
    
    # Calculer les scores
    scores = []
    levels = []
    
    for finca in sentinel1_data:
        if finca.get('status') == 'success' and 'sentinel1_6months' in finca:
            points, level = score_radar(finca['sentinel1_6months']['vv_mean'])
            scores.append(points)
            levels.append(level)
    
    # Analyser la distribution
    score_counts = Counter(scores)
    level_counts = Counter(levels)
    total = len(scores)
    
    print(f"\n🎯 Répartition par points:")
    for points in [1, 3, 5]:
        count = score_counts.get(points, 0)
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"   • {points} point ({'Faible' if points == 1 else 'Moyen' if points == 3 else 'Fort'}): {count} fincas ({percentage:.1f}%)")
    
    print(f"\n🏷️ Répartition par niveau:")
    for level in ['Faible', 'Moyen', 'Fort']:
        count = level_counts.get(level, 0)
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    return {
        'total': total,
        'min_vv': min(vv_values),
        'max_vv': max(vv_values),
        'mean_vv': np.mean(vv_values),
        'score_distribution': dict(score_counts),
        'level_distribution': dict(level_counts)
    }


def analyze_ndvi_distribution(ndvi_data):
    """Analyse la distribution NDVI avec règle historique (médiane + variation)"""
    if not ndvi_data:
        return None
    
    medians = [f['median'] for f in ndvi_data if f.get('median') is not None]
    stds = [f['std'] for f in ndvi_data if f.get('std') is not None]
    cvs = [f['cv'] for f in ndvi_data if f.get('cv') is not None]
    
    print(f"📊 VÉGÉTATION NDVI (Règle Historique: Médiane + Variation)")
    print(f"=" * 60)
    print(f"📈 Données analysées: {len(ndvi_data)}")
    print(f"📊 Médiane NDVI: {min(medians):.3f} / {max(medians):.3f} (moy: {np.mean(medians):.3f})")
    print(f"📊 Écart-type: {min(stds):.3f} / {max(stds):.3f} (moy: {np.mean(stds):.3f})")
    print(f"📊 Coeff. Variation: {min(cvs):.3f} / {max(cvs):.3f} (moy: {np.mean(cvs):.3f})")
    
    # Calculer les scores avec la règle historique
    scores = []
    levels = []
    
    for finca in ndvi_data:
        if finca.get('median') is not None and finca.get('std') is not None:
            points, level = score_vegetation_from_ndvi_summary(finca['median'], finca['std'])
            scores.append(points)
            levels.append(level)
    
    # Analyser la distribution
    score_counts = Counter(scores)
    level_counts = Counter(levels)
    total = len(scores)
    
    print(f"\n🎯 Répartition par points:")
    for points in [1, 3, 5]:
        count = score_counts.get(points, 0)
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"   • {points} point ({'Faible' if points == 1 else 'Moyen' if points == 3 else 'Fort'}): {count} fincas ({percentage:.1f}%)")
    
    print(f"\n🏷️ Répartition par niveau:")
    for level in ['Faible', 'Moyen', 'Fort']:
        count = level_counts.get(level, 0)
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    return {
        'total': total,
        'median_stats': {
            'min': min(medians),
            'max': max(medians),
            'mean': np.mean(medians)
        },
        'std_stats': {
            'min': min(stds),
            'max': max(stds),
            'mean': np.mean(stds)
        },
        'cv_stats': {
            'min': min(cvs),
            'max': max(cvs),
            'mean': np.mean(cvs)
        },
        'score_distribution': dict(score_counts),
        'level_distribution': dict(level_counts)
    }


def main():
    """Fonction principale"""
    print("📊 ANALYSE DE LA RÉPARTITION PAR CRITÈRE")
    print("=" * 60)
    
    print("📂 Chargement des données...")
    
    # Charger les données
    viirs_data = load_viirs_data()
    sentinel1_data = load_sentinel1_data()
    ndvi_data = load_ndvi_data()
    
    print(f"   • VIIRS: {len(viirs_data)} fincas")
    print(f"   • Sentinel-1: {len(sentinel1_data)} fincas")
    print(f"   • NDVI: {len(ndvi_data)} fincas")
    
    # Analyser chaque critère
    viirs_results = analyze_viirs_distribution(viirs_data)
    sentinel1_results = analyze_sentinel1_distribution(sentinel1_data)
    ndvi_results = analyze_ndvi_distribution(ndvi_data)
    
    # Résumé global
    print(f"\n🎯 RÉSUMÉ GLOBAL")
    print(f"=" * 60)
    
    if viirs_results:
        print(f"\nVIIRS:")
        for points in [1, 3, 5]:
            count = viirs_results['score_distribution'].get(points, 0)
            total = viirs_results['total']
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"   • {points}pt ({'Faible' if points == 1 else 'Moyen' if points == 3 else 'Fort'}): {percentage:.1f}%")
    
    if sentinel1_results:
        print(f"\nSENTINEL1:")
        for points in [1, 3, 5]:
            count = sentinel1_results['score_distribution'].get(points, 0)
            total = sentinel1_results['total']
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"   • {points}pt ({'Faible' if points == 1 else 'Moyen' if points == 3 else 'Fort'}): {percentage:.1f}%")
    
    if ndvi_results:
        print(f"\nNDVI:")
        for points in [1, 3, 5]:
            count = ndvi_results['score_distribution'].get(points, 0)
            total = ndvi_results['total']
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"   • {points}pt ({'Faible' if points == 1 else 'Moyen' if points == 3 else 'Fort'}): {percentage:.1f}%")


if __name__ == "__main__":
    main()
