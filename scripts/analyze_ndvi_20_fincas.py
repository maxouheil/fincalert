#!/usr/bin/env python3
"""
Analyse la répartition NDVI avec les 20 fincas disponibles
Combine données brutes (médiane + std) et scores calculés
"""

import json
import numpy as np
from pathlib import Path
from collections import Counter
import sys
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
from scoring.simple_scoring import score_vegetation_from_ndvi_summary, score_vegetation


def load_ndvi_raw_data():
    """Charge les données NDVI brutes (médiane + std)"""
    ndvi_dir = Path("data/ndvi")
    ndvi_data = {}
    
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
                            finca_id = finca_dir.name
                            ndvi_data[finca_id] = {
                                'median': summary['median'],
                                'std': summary['std'],
                                'cv': (summary['std'] / summary['median']) if summary['median'] > 0 else 0,
                                'source': 'raw_data'
                            }
                except Exception as e:
                    print(f"⚠️ Erreur lecture {summary_file}: {e}")
    
    return ndvi_data


def load_ndvi_calculated_data():
    """Charge les scores NDVI calculés depuis les analyses combinées"""
    combined_dir = Path("data/combined_analysis")
    combined_files = list(combined_dir.glob("combined_scoring_*.json"))
    
    ndvi_data = {}
    
    for file_path in combined_files:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        for finca in data.get('fincas', []):
            if 'ndvi_score' in finca:
                finca_id = finca['finca_id']
                if finca_id not in ndvi_data:
                    ndvi_data[finca_id] = []
                ndvi_data[finca_id].append(finca['ndvi_score'])
    
    # Calculer la moyenne pour chaque finca
    final_data = {}
    for finca_id, scores in ndvi_data.items():
        final_data[finca_id] = {
            'ndvi_score': np.mean(scores),
            'source': 'calculated_score'
        }
    
    return final_data


def analyze_ndvi_distribution():
    """Analyse la distribution NDVI avec les 20 fincas"""
    print("🔍 ANALYSE NDVI - 20 FINCAS DISPONIBLES")
    print("=" * 60)
    
    # Charger les deux sources de données
    raw_data = load_ndvi_raw_data()
    calculated_data = load_ndvi_calculated_data()
    
    print(f"📊 Sources de données:")
    print(f"   • Données brutes (médiane + std): {len(raw_data)} fincas")
    print(f"   • Scores calculés: {len(calculated_data)} fincas")
    
    # Identifier les fincas communes et uniques
    raw_ids = set(raw_data.keys())
    calculated_ids = set(calculated_data.keys())
    all_ids = raw_ids | calculated_ids
    
    print(f"\n📋 Répartition des fincas:")
    print(f"   • Total unique: {len(all_ids)} fincas")
    print(f"   • Brutes uniquement: {len(raw_ids - calculated_ids)} fincas")
    print(f"   • Calculées uniquement: {len(calculated_ids - raw_ids)} fincas")
    print(f"   • Communes: {len(raw_ids & calculated_ids)} fincas")
    
    # Analyser chaque source séparément
    print(f"\n📊 ANALYSE DONNÉES BRUTES (Règle Historique: Médiane + Variation)")
    print("-" * 60)
    
    if raw_data:
        raw_scores = []
        raw_levels = []
        raw_cvs = []
        
        for finca_id, data in raw_data.items():
            points, level = score_vegetation_from_ndvi_summary(data['median'], data['std'])
            raw_scores.append(points)
            raw_levels.append(level)
            raw_cvs.append(data['cv'])
        
        score_counts = Counter(raw_scores)
        level_counts = Counter(raw_levels)
        total = len(raw_scores)
        
        print(f"📈 Fincas analysées: {total}")
        print(f"📊 CV moyen: {np.mean(raw_cvs):.3f}")
        print(f"📊 CV range: {min(raw_cvs):.3f} - {max(raw_cvs):.3f}")
        
        print(f"\n🎯 Répartition par entretien végétation:")
        for points in [1, 3, 5]:
            count = score_counts.get(points, 0)
            percentage = (count / total) * 100
            label = "Faible" if points == 1 else "Moyen" if points == 3 else "Fort"
            print(f"   • {points}pt ({label}): {count} fincas ({percentage:.1f}%)")
        
        print(f"\n🏷️ Répartition par niveau:")
        for level in ['Faible', 'Moyen', 'Fort']:
            count = level_counts.get(level, 0)
            percentage = (count / total) * 100
            print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    print(f"\n📊 ANALYSE SCORES CALCULÉS")
    print("-" * 60)
    
    if calculated_data:
        calc_scores = []
        calc_levels = []
        calc_score_values = []
        
        for finca_id, data in calculated_data.items():
            points, level = score_vegetation(data['ndvi_score'])
            calc_scores.append(points)
            calc_levels.append(level)
            calc_score_values.append(data['ndvi_score'])
        
        score_counts = Counter(calc_scores)
        level_counts = Counter(calc_levels)
        total = len(calc_scores)
        
        print(f"📈 Fincas analysées: {total}")
        print(f"📊 Score moyen: {np.mean(calc_score_values):.1f}")
        print(f"📊 Score range: {min(calc_score_values):.1f} - {max(calc_score_values):.1f}")
        
        print(f"\n🎯 Répartition par entretien végétation:")
        for points in [1, 3, 5]:
            count = score_counts.get(points, 0)
            percentage = (count / total) * 100
            label = "Faible" if points == 1 else "Moyen" if points == 3 else "Fort"
            print(f"   • {points}pt ({label}): {count} fincas ({percentage:.1f}%)")
        
        print(f"\n🏷️ Répartition par niveau:")
        for level in ['Faible', 'Moyen', 'Fort']:
            count = level_counts.get(level, 0)
            percentage = (count / total) * 100
            print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    # Comparaison des deux approches
    print(f"\n🔄 COMPARAISON DES APPROCHES")
    print("-" * 60)
    
    common_ids = raw_ids & calculated_ids
    if common_ids:
        print(f"📊 Fincas communes ({len(common_ids)}):")
        
        for finca_id in sorted(common_ids):
            raw_points, raw_level = score_vegetation_from_ndvi_summary(
                raw_data[finca_id]['median'], 
                raw_data[finca_id]['std']
            )
            calc_points, calc_level = score_vegetation(calculated_data[finca_id]['ndvi_score'])
            
            print(f"   • {finca_id}:")
            print(f"     - Brute (CV={raw_data[finca_id]['cv']:.3f}): {raw_points}pt ({raw_level})")
            print(f"     - Calculé (score={calculated_data[finca_id]['ndvi_score']:.1f}): {calc_points}pt ({calc_level})")
    
    # Résumé final
    print(f"\n🎯 RÉSUMÉ FINAL - 20 FINCAS")
    print("=" * 60)
    
    print(f"📊 Données brutes (médiane + variation):")
    if raw_data:
        raw_dist = Counter([score_vegetation_from_ndvi_summary(d['median'], d['std'])[1] for d in raw_data.values()])
        for level in ['Faible', 'Moyen', 'Fort']:
            count = raw_dist.get(level, 0)
            percentage = (count / len(raw_data)) * 100
            print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    print(f"\n📊 Scores calculés:")
    if calculated_data:
        calc_dist = Counter([score_vegetation(d['ndvi_score'])[1] for d in calculated_data.values()])
        for level in ['Faible', 'Moyen', 'Fort']:
            count = calc_dist.get(level, 0)
            percentage = (count / len(calculated_data)) * 100
            print(f"   • {level}: {count} fincas ({percentage:.1f}%)")


def main():
    """Fonction principale"""
    analyze_ndvi_distribution()


if __name__ == "__main__":
    main()
