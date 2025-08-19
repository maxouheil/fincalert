#!/usr/bin/env python3
"""
🔄 Intégration des Données Sentinel-1 Optimisées - Scoring Combiné
Intègre les nouvelles données Sentinel-1 avec seuils optimisés dans le scoring combiné
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

def load_optimized_sentinel1_data():
    """Charge les données Sentinel-1 optimisées"""
    optimized_file = ROOT / 'data' / 'sentinel1_all_fincas_6months_optimized.json'
    
    if not optimized_file.exists():
        print("❌ Fichier de données Sentinel-1 optimisées non trouvé")
        return None
    
    print(f"📄 Chargement des données Sentinel-1 optimisées: {optimized_file.name}")
    
    with open(optimized_file, 'r') as f:
        data = json.load(f)
    
    return data

def load_ndvi_data():
    """Charge les données NDVI existantes"""
    ndvi_files = list(ROOT.glob('data/fincas_abandon_scores_*.csv'))
    
    if not ndvi_files:
        print("❌ Aucun fichier de données NDVI trouvé")
        return None
    
    latest_ndvi_file = max(ndvi_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Chargement des données NDVI: {latest_ndvi_file.name}")
    
    df = pd.read_csv(latest_ndvi_file)
    
    # Convertir en dictionnaire
    ndvi_data = {}
    for _, row in df.iterrows():
        ndvi_data[row['finca_id']] = {
            'abandon_score': row['abandon_score'],
            'activity_status': row['activity_status'],
            'median_ndvi': row['median_ndvi'],
            'risk_category': row['risk_category']
        }
    
    return ndvi_data

def combine_scores(sentinel1_data, ndvi_data, weights={'ndvi': 0.6, 'sentinel1': 0.4}):
    """Combine les scores NDVI et Sentinel-1"""
    combined_results = []
    
    for finca in sentinel1_data['fincas']:
        finca_id = finca['finca_id']
        
        # Données Sentinel-1
        s1_score = finca['sentinel1_6months']['activity_score']
        s1_level = finca['sentinel1_6months']['activity_level']
        s1_vv = finca['sentinel1_6months']['vv_mean']
        
        # Données NDVI (si disponibles)
        if finca_id in ndvi_data:
            ndvi_score = ndvi_data[finca_id]['abandon_score']
            ndvi_status = ndvi_data[finca_id]['activity_status']
            ndvi_median = ndvi_data[finca_id]['median_ndvi']
            ndvi_risk = ndvi_data[finca_id]['risk_category']
        else:
            # Valeurs par défaut si pas de données NDVI
            ndvi_score = 50
            ndvi_status = "Modérée"
            ndvi_median = 0.3
            ndvi_risk = "Moyen"
        
        # Score combiné pondéré
        combined_score = (ndvi_score * weights['ndvi']) + (s1_score * weights['sentinel1'])
        
        # Classification du niveau d'abandon
        if combined_score >= 80:
            abandonment_level = "Très élevé"
        elif combined_score >= 60:
            abandonment_level = "Élevé"
        elif combined_score >= 40:
            abandonment_level = "Modéré"
        elif combined_score >= 20:
            abandonment_level = "Faible"
        else:
            abandonment_level = "Très faible"
        
        # Résultat combiné
        combined_result = {
            'finca_id': finca_id,
            'coordinates': finca['coordinates'],
            'combined_scoring': {
                'overall_score': round(combined_score, 1),
                'abandonment_level': abandonment_level,
                'weights_used': weights,
                'components': {
                    'ndvi': {
                        'score': ndvi_score,
                        'status': ndvi_status,
                        'median_ndvi': ndvi_median,
                        'risk_category': ndvi_risk
                    },
                    'sentinel1': {
                        'score': s1_score,
                        'activity_level': s1_level,
                        'vv_mean': s1_vv,
                        'period': '6 months average'
                    }
                }
            }
        }
        
        combined_results.append(combined_result)
    
    return combined_results

def classify_abandonment(combined_score):
    """Classifie le niveau d'abandon basé sur le score combiné"""
    if combined_score >= 80:
        return "Très élevé"
    elif combined_score >= 60:
        return "Élevé"
    elif combined_score >= 40:
        return "Modéré"
    elif combined_score >= 20:
        return "Faible"
    else:
        return "Très faible"

def main():
    print("🔄 INTÉGRATION DES DONNÉES SENTINEL-1 OPTIMISÉES")
    print("=" * 70)
    
    # Charger les données Sentinel-1 optimisées
    sentinel1_data = load_optimized_sentinel1_data()
    if not sentinel1_data:
        return
    
    # Charger les données NDVI
    ndvi_data = load_ndvi_data()
    if not ndvi_data:
        print("⚠️ Aucune donnée NDVI trouvée, utilisation de valeurs par défaut")
        ndvi_data = {}
    
    print(f"\n📊 STATISTIQUES DES DONNÉES:")
    print(f"   📁 Fincas Sentinel-1: {len(sentinel1_data['fincas'])}")
    print(f"   📁 Fincas NDVI: {len(ndvi_data)}")
    
    # Combiner les scores
    print(f"\n🔄 Combinaison des scores...")
    combined_results = combine_scores(sentinel1_data, ndvi_data)
    
    # Calculer les statistiques
    scores = [r['combined_scoring']['overall_score'] for r in combined_results]
    abandonment_levels = [r['combined_scoring']['abandonment_level'] for r in combined_results]
    
    from collections import Counter
    level_distribution = Counter(abandonment_levels)
    
    # Statistiques
    score_stats = {
        'mean': round(sum(scores) / len(scores), 1),
        'min': min(scores),
        'max': max(scores),
        'std': round(sum((s - sum(scores)/len(scores))**2 for s in scores)**0.5 / len(scores), 1)
    }
    
    # Créer le fichier de résultats
    output_data = {
        'analysis_date': datetime.now().isoformat(),
        'total_fincas': len(combined_results),
        'weights_used': {'ndvi': 0.6, 'sentinel1': 0.4},
        'score_statistics': score_stats,
        'abandonment_distribution': dict(level_distribution),
        'sentinel1_thresholds': sentinel1_data['optimized_thresholds'],
        'results': combined_results
    }
    
    # Sauvegarder
    output_file = ROOT / 'data' / 'combined_scoring_optimized_sentinel1.json'
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    # Créer aussi un CSV
    csv_data = []
    for result in combined_results:
        csv_data.append({
            'finca_id': result['finca_id'],
            'lat': result['coordinates']['lat'],
            'lon': result['coordinates']['lon'],
            'overall_score': result['combined_scoring']['overall_score'],
            'abandonment_level': result['combined_scoring']['abandonment_level'],
            'ndvi_score': result['combined_scoring']['components']['ndvi']['score'],
            'ndvi_status': result['combined_scoring']['components']['ndvi']['status'],
            'sentinel1_score': result['combined_scoring']['components']['sentinel1']['score'],
            'sentinel1_level': result['combined_scoring']['components']['sentinel1']['activity_level'],
            'sentinel1_vv': result['combined_scoring']['components']['sentinel1']['vv_mean']
        })
    
    df = pd.DataFrame(csv_data)
    csv_file = ROOT / 'data' / 'combined_scoring_optimized_sentinel1.csv'
    df.to_csv(csv_file, index=False)
    
    # Afficher les résultats
    print(f"\n📊 RÉSULTATS DU SCORING COMBINÉ:")
    print(f"   📁 Total fincas: {len(combined_results)}")
    print(f"   🎯 Score moyen: {score_stats['mean']}/100")
    print(f"   📈 Score min/max: {score_stats['min']} / {score_stats['max']}")
    print(f"   📉 Écart-type: {score_stats['std']}")
    
    print(f"\n🎯 DISTRIBUTION DES NIVEAUX D'ABANDON:")
    for level in ['Très faible', 'Faible', 'Modéré', 'Élevé', 'Très élevé']:
        count = level_distribution.get(level, 0)
        percentage = (count / len(combined_results)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    print(f"\n📁 FICHIERS GÉNÉRÉS:")
    print(f"   • JSON combiné: {output_file}")
    print(f"   • CSV combiné: {csv_file}")
    
    # Top 10 des fincas les plus à risque
    print(f"\n🔥 TOP 10 DES FINCAS LES PLUS À RISQUE:")
    print("-" * 80)
    print(f"{'Rang':<4} {'Finca':<12} {'Score':<8} {'Niveau':<15} {'NDVI':<8} {'S1':<8}")
    print("-" * 80)
    
    sorted_results = sorted(combined_results, key=lambda x: x['combined_scoring']['overall_score'], reverse=True)
    
    for i, result in enumerate(sorted_results[:10], 1):
        finca_id = result['finca_id']
        overall_score = result['combined_scoring']['overall_score']
        abandonment_level = result['combined_scoring']['abandonment_level']
        ndvi_score = result['combined_scoring']['components']['ndvi']['score']
        s1_score = result['combined_scoring']['components']['sentinel1']['score']
        
        print(f"{i:<4} "
              f"{finca_id:<12} "
              f"{overall_score:<8.1f} "
              f"{abandonment_level:<15} "
              f"{ndvi_score:<8} "
              f"{s1_score:<8}")
    
    print("-" * 80)
    
    print(f"\n💡 INTÉGRATION TERMINÉE:")
    print(f"   ✅ Données Sentinel-1 optimisées intégrées")
    print(f"   📊 Scoring combiné calculé (60% NDVI + 40% S1)")
    print(f"   🎯 Niveaux d'abandon classifiés")
    print(f"   📁 Fichiers prêts pour le frontend")

if __name__ == "__main__":
    main()
