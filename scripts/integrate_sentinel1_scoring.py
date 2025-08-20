#!/usr/bin/env python3
"""
🎯 Intégration Sentinel-1 dans le Scoring d'Abandon
Combine les données d'activité radar avec les scores NDVI existants
"""

import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def load_sentinel1_data():
    """Charge les données Sentinel-1 ultra-précises"""
    s1_dir = ROOT / 'data' / 'sentinel1_ultra_precise_analysis'
    summary_files = [f for f in s1_dir.glob('*50m_summary*.json')]
    
    if not summary_files:
        print("❌ Aucune donnée Sentinel-1 trouvée")
        return None
    
    latest_file = max(summary_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Chargement Sentinel-1: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def load_ndvi_data():
    """Charge les données NDVI existantes depuis les CSVs"""
    abandon_dir = ROOT / 'data' / 'abandon_analysis_FULL'
    csv_files = [f for f in abandon_dir.glob('fincas_abandon_scores_*.csv')]
    
    if not csv_files:
        print("❌ Aucune donnée NDVI CSV trouvée")
        return None
    
    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Chargement NDVI: {latest_file.name}")
    
    import pandas as pd
    df = pd.read_csv(latest_file)
    
    # Convertir en dictionnaire par finca_id
    ndvi_dict = {}
    for _, row in df.iterrows():
        ndvi_dict[row['finca_id']] = {
            'finca_id': row['finca_id'],
            'overall_score': row['abandon_score'],
            'status': row['activity_status'],
            'median_ndvi': row['median_ndvi']
        }
    
    return ndvi_dict

def calculate_activity_score(vv_value):
    """Calcule un score d'activité basé sur la valeur VV Sentinel-1"""
    # Normaliser VV entre 0 et 100
    # VV élevé = plus d'activité = score plus élevé
    # VV typique : -25 à 0 dB
    
    if vv_value > -5:
        return 90  # Très élevée
    elif vv_value > -10:
        return 75  # Élevée
    elif vv_value > -15:
        return 50  # Modérée
    elif vv_value > -20:
        return 25  # Faible
    else:
        return 10  # Très faible

def combine_scores(ndvi_score, activity_score, weights={'ndvi': 0.6, 'activity': 0.4}):
    """Combine les scores NDVI et Sentinel-1 avec pondération"""
    combined = (ndvi_score * weights['ndvi']) + (activity_score * weights['activity'])
    return round(combined, 2)

def classify_abandonment(combined_score):
    """Classifie le niveau d'abandon basé sur le score combiné"""
    if combined_score >= 70:
        return "Non abandonné"
    elif combined_score >= 50:
        return "Activité modérée"
    elif combined_score >= 30:
        return "Probablement abandonné"
    else:
        return "Fortement abandonné"

def main():
    print("🎯 INTÉGRATION SENTINEL-1 DANS LE SCORING D'ABANDON")
    print("=" * 70)
    
    # Charger les données
    s1_data = load_sentinel1_data()
    ndvi_data = load_ndvi_data()
    
    if not s1_data or not ndvi_data:
        print("❌ Données manquantes")
        return
    
    # Créer des dictionnaires pour faciliter la correspondance
    s1_dict = {finca['finca_id']: finca for finca in s1_data['fincas']}
    # ndvi_data est déjà un dictionnaire
    
    # Fincas communes
    common_fincas = [fid for fid in s1_dict.keys() if fid in ndvi_data]
    print(f"📊 {len(common_fincas)} fincas avec données complètes")
    
    # Combiner les scores
    combined_results = []
    
    print(f"\n📈 SCORING COMBINÉ NDVI + SENTINEL-1")
    print("-" * 90)
    print(f"{'Finca':<12} {'NDVI':<8} {'S1-VV':<8} {'Act':<8} {'Combiné':<10} {'Classification':<20}")
    print("-" * 90)
    
    for finca_id in sorted(common_fincas):
        s1_finca = s1_dict[finca_id]
        ndvi_finca = ndvi_data[finca_id]
        
        # Extraire les scores
        ndvi_score = ndvi_finca.get('overall_score', 0)
        vv_value = s1_finca['avg_vv']
        activity_score = calculate_activity_score(vv_value)
        
        # Score combiné
        combined_score = combine_scores(ndvi_score, activity_score)
        classification = classify_abandonment(combined_score)
        
        print(f"{finca_id:<12} "
              f"{ndvi_score:<8.1f} "
              f"{vv_value:<8.3f} "
              f"{activity_score:<8} "
              f"{combined_score:<10.1f} "
              f"{classification:<20}")
        
        # Sauvegarder le résultat
        combined_results.append({
            'finca_id': finca_id,
            'coordinates': s1_finca['coordinates'],
            'ndvi_score': ndvi_score,
            'sentinel1_vv': vv_value,
            'activity_score': activity_score,
            'combined_score': combined_score,
            'classification': classification,
            'sentinel1_activity_level': s1_finca['overall_activity'],
            'analysis_date': datetime.now().isoformat()
        })
    
    print("-" * 90)
    
    # Statistiques
    classifications = [r['classification'] for r in combined_results]
    combined_scores = [r['combined_score'] for r in combined_results]
    
    print(f"\n📊 STATISTIQUES DU SCORING COMBINÉ")
    print("=" * 50)
    print(f"📁 Fincas analysées: {len(combined_results)}")
    print(f"📈 Score moyen: {sum(combined_scores)/len(combined_scores):.1f}")
    print(f"📊 Score min/max: {min(combined_scores):.1f} / {max(combined_scores):.1f}")
    
    print(f"\n🎯 Distribution des classifications:")
    class_counts = {}
    for cls in classifications:
        class_counts[cls] = class_counts.get(cls, 0) + 1
    
    for cls, count in class_counts.items():
        percentage = (count / len(combined_results)) * 100
        print(f"   • {cls}: {count} fincas ({percentage:.1f}%)")
    
    # Sauvegarder les résultats
    output_dir = ROOT / 'data' / 'combined_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = output_dir / f"combined_scoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    final_data = {
        'analysis_date': datetime.now().isoformat(),
        'total_fincas': len(combined_results),
        'weighting': {'ndvi': 0.6, 'activity': 0.4},
        'statistics': {
            'mean_score': sum(combined_scores)/len(combined_scores),
            'min_score': min(combined_scores),
            'max_score': max(combined_scores),
            'classification_distribution': class_counts
        },
        'fincas': combined_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(final_data, f, indent=2)
    
    print(f"\n📁 Résultats sauvegardés: {results_file}")
    
    print(f"\n💡 OBSERVATIONS:")
    print(f"   • Le scoring combiné utilise 60% NDVI + 40% Sentinel-1")
    print(f"   • Sentinel-1 détecte l'activité humaine récente")
    print(f"   • NDVI mesure la végétation et l'entretien")
    print(f"   • La combinaison donne une vue plus complète de l'abandon")
    
    # Identifier les fincas avec divergence
    print(f"\n🔍 FINCAS AVEC DIVERGENCE NDVI/SENTINEL-1:")
    for result in combined_results:
        ndvi_high = result['ndvi_score'] >= 60
        activity_high = result['activity_score'] >= 60
        
        if ndvi_high != activity_high:
            print(f"   • {result['finca_id']}: NDVI={result['ndvi_score']:.1f}, "
                  f"Activité={result['activity_score']:.1f} "
                  f"({result['classification']})")

if __name__ == "__main__":
    main()
