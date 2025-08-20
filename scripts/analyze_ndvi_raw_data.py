#!/usr/bin/env python3
"""
Analyse les données NDVI brutes (médiane + std) pour le système de scoring simple
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import sys
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from scoring.simple_scoring import score_vegetation_from_ndvi_summary


def load_ndvi_raw_data():
    """Charge les données NDVI brutes depuis les fichiers individuels"""
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
                                'cv': (summary['std'] / summary['median']) if summary['median'] > 0 else 0,
                                'status': summary.get('status', 'unknown'),
                                'valid_periods': summary.get('valid', 0)
                            })
                except Exception as e:
                    print(f"⚠️ Erreur lecture {summary_file}: {e}")
    
    return ndvi_data


def analyze_cv_distribution(ndvi_data):
    """Analyse la distribution des coefficients de variation"""
    if not ndvi_data:
        return None
    
    cvs = [item['cv'] for item in ndvi_data]
    medians = [item['median'] for item in ndvi_data]
    stds = [item['std'] for item in ndvi_data]
    
    print(f"📊 ANALYSE DES DONNÉES NDVI BRUTES")
    print(f"=" * 50)
    print(f"📈 Fincas analysées: {len(ndvi_data)}")
    print(f"📊 Médiane NDVI: {min(medians):.3f} - {max(medians):.3f} (moy: {np.mean(medians):.3f})")
    print(f"📊 Écart-type: {min(stds):.3f} - {max(stds):.3f} (moy: {np.mean(stds):.3f})")
    print(f"📊 Coefficient de Variation: {min(cvs):.3f} - {max(cvs):.3f} (moy: {np.mean(cvs):.3f})")
    
    # Distribution par statut original
    status_counts = Counter([item['status'] for item in ndvi_data])
    print(f"\n📋 Distribution par statut original:")
    for status, count in status_counts.items():
        percentage = (count / len(ndvi_data)) * 100
        print(f"   • {status}: {count} fincas ({percentage:.1f}%)")
    
    # Test des seuils de scoring simple
    scores = []
    levels = []
    
    for item in ndvi_data:
        points, level = score_vegetation_from_ndvi_summary(item['median'], item['std'])
        scores.append(points)
        levels.append(level)
    
    score_counts = Counter(scores)
    level_counts = Counter(levels)
    
    print(f"\n🎯 Distribution avec règle CV (médiane + variation):")
    for points in [1, 3, 5]:
        count = score_counts.get(points, 0)
        percentage = (count / len(ndvi_data)) * 100
        label = "Faible" if points == 1 else "Moyen" if points == 3 else "Fort"
        print(f"   • {points}pt ({label}): {count} fincas ({percentage:.1f}%)")
    
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
            
            # Lister quelques exemples
            for item in items[:3]:
                print(f"     - {item['finca_id']}: CV={item['cv']:.3f}, median={item['median']:.3f}, std={item['std']:.3f}")
    
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
        'status_distribution': dict(status_counts)
    }


def main():
    """Fonction principale"""
    print("🔍 ANALYSE DES DONNÉES NDVI BRUTES (MÉDIANE + VARIATION)")
    print("=" * 60)
    
    # Charger les données brutes
    ndvi_data = load_ndvi_raw_data()
    
    if not ndvi_data:
        print("❌ Aucune donnée NDVI brute trouvée")
        return
    
    # Analyser la distribution
    results = analyze_cv_distribution(ndvi_data)
    
    # Comparer avec les données combinées (scores calculés)
    print(f"\n🔄 COMPARAISON AVEC SCORES CALCULÉS")
    print(f"=" * 50)
    
    # Charger les scores calculés depuis les analyses combinées
    combined_dir = Path("data/combined_analysis")
    combined_files = list(combined_dir.glob("combined_scoring_*.json"))
    
    if combined_files:
        with open(combined_files[0], 'r') as f:
            combined_data = json.load(f)
        
        print(f"📊 Données brutes (médiane+std): {len(ndvi_data)} fincas")
        print(f"📊 Scores calculés: {len(combined_data.get('fincas', []))} fincas")
        
        # Identifier les fincas communes
        raw_ids = set([item['finca_id'] for item in ndvi_data])
        combined_ids = set([item['finca_id'] for item in combined_data.get('fincas', [])])
        common_ids = raw_ids & combined_ids
        
        print(f"📊 Fincas communes: {len(common_ids)}")
        print(f"📊 Fincas uniquement en brut: {len(raw_ids - combined_ids)}")
        print(f"📊 Fincas uniquement en calculé: {len(combined_ids - raw_ids)}")
        
        if len(raw_ids - combined_ids) > 0:
            print(f"\n💡 Fincas supplémentaires disponibles en données brutes:")
            for finca_id in sorted(raw_ids - combined_ids):
                item = next(item for item in ndvi_data if item['finca_id'] == finca_id)
                print(f"   • {finca_id}: CV={item['cv']:.3f}, median={item['median']:.3f}")
    
    # Sauvegarder l'analyse
    output = {
        'analysis_type': 'ndvi_raw_median_std',
        'total_fincas': results['total_fincas'],
        'cv_statistics': results['cv_stats'],
        'scoring_distribution': results['score_distribution'],
        'level_distribution': results['level_distribution'],
        'original_status_distribution': results['status_distribution'],
        'fincas': ndvi_data
    }
    
    output_file = Path("data/ndvi_raw_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Analyse sauvegardée: {output_file}")


if __name__ == "__main__":
    main()
