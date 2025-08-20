#!/usr/bin/env python3
"""
🌙 Test VIIRS 6 mois vs 12 mois
Compare l'analyse VIIRS sur différentes périodes temporelles
"""

import os
import sys
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.satellite.nocturnal_luminosity import NocturnalLuminosityAnalyzer


def load_test_fincas():
    """Charge les 5 premières fincas pour le test"""
    geojson_path = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    
    if not geojson_path.exists():
        raise FileNotFoundError(f"Fichier GeoJSON non trouvé: {geojson_path}")
    
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"📊 Total fincas disponibles: {len(features)}")
    
    # Prendre les 5 premières fincas
    test_features = features[:5]
    print(f"🧪 Test sur {len(test_features)} fincas")
    
    return test_features


def analyze_finca_viirs_periods(finca_data, periods=[6, 12]):
    """Analyse une finca avec différentes périodes VIIRS"""
    props = finca_data.get('properties', {})
    finca_id = props.get('id')
    lat = props.get('lat')
    lon = props.get('lon')
    
    if not all([finca_id, lat, lon]):
        return None
    
    print(f"\n📍 {finca_id} - {lat:.6f}, {lon:.6f}")
    
    analyzer = NocturnalLuminosityAnalyzer()
    results = {}
    
    for months in periods:
        print(f"   🔍 Analyse {months} mois...")
        start_time = time.time()
        
        try:
            # Récupérer les données VIIRS
            monthly_data = analyzer.get_monthly_luminosity(lat, lon, months=months, demo=False)
            
            # Calculer les métriques
            metrics = analyzer.calculate_luminosity_metrics(monthly_data)
            
            # Calculer le score
            score, reason = analyzer.calculate_luminosity_score(metrics)
            
            processing_time = time.time() - start_time
            
            results[months] = {
                'monthly_data': monthly_data,
                'metrics': metrics,
                'score': score,
                'processing_time': processing_time,
                'data_points': len(monthly_data)
            }
            
            print(f"      ✅ {months} mois: Score {score}/5, {len(monthly_data)} points, {processing_time:.1f}s")
            
        except Exception as e:
            print(f"      ❌ Erreur {months} mois: {e}")
            results[months] = None
    
    return {
        'finca_id': finca_id,
        'coordinates': {'lat': lat, 'lon': lon},
        'results': results
    }


def compare_periods_analysis(test_results):
    """Compare les résultats entre 6 et 12 mois"""
    print(f"\n📊 COMPARAISON 6 MOIS vs 12 MOIS")
    print("=" * 60)
    
    comparison_data = []
    
    for finca_result in test_results:
        if not finca_result or not finca_result['results']:
            continue
            
        finca_id = finca_result['finca_id']
        results = finca_result['results']
        
        if 6 not in results or 12 not in results:
            continue
            
        result_6m = results[6]
        result_12m = results[12]
        
        if not result_6m or not result_12m:
            continue
        
        # Comparer les métriques
        metrics_6m = result_6m['metrics']
        metrics_12m = result_12m['metrics']
        
        comparison = {
            'finca_id': finca_id,
            'score_6m': result_6m['score'],
            'score_12m': result_12m['score'],
            'score_diff': result_12m['score'] - result_6m['score'],
            'mean_luminosity_6m': metrics_6m['mean_luminosity'],
            'mean_luminosity_12m': metrics_12m['mean_luminosity'],
            'trend_6m': metrics_6m['trend'],
            'trend_12m': metrics_12m['trend'],
            'active_months_6m': metrics_6m['active_months'],
            'active_months_12m': metrics_12m['active_months'],
            'seasonal_pattern_6m': metrics_6m['seasonal_pattern'],
            'seasonal_pattern_12m': metrics_12m['seasonal_pattern'],
            'processing_time_6m': result_6m['processing_time'],
            'processing_time_12m': result_12m['processing_time'],
            'data_points_6m': result_6m['data_points'],
            'data_points_12m': result_12m['data_points']
        }
        
        comparison_data.append(comparison)
        
        # Afficher les détails
        print(f"\n🔍 {finca_id}:")
        print(f"   Score: {result_6m['score']}/5 → {result_12m['score']}/5 (diff: {comparison['score_diff']:+d})")
        print(f"   Luminosité: {metrics_6m['mean_luminosity']:.3f} → {metrics_12m['mean_luminosity']:.3f}")
        print(f"   Tendance: {metrics_6m['trend']:.3f} → {metrics_12m['trend']:.3f}")
        print(f"   Pattern: {metrics_6m['seasonal_pattern']} → {metrics_12m['seasonal_pattern']}")
        print(f"   Temps: {result_6m['processing_time']:.1f}s → {result_12m['processing_time']:.1f}s")
    
    return comparison_data


def calculate_statistics(comparison_data):
    """Calcule les statistiques de comparaison"""
    if not comparison_data:
        return {}
    
    df = pd.DataFrame(comparison_data)
    
    stats = {
        'total_fincas': int(len(comparison_data)),
        'score_changes': {
            'mean_diff': float(df['score_diff'].mean()),
            'std_diff': float(df['score_diff'].std()),
            'improved': int((df['score_diff'] > 0).sum()),
            'worsened': int((df['score_diff'] < 0).sum()),
            'unchanged': int((df['score_diff'] == 0).sum())
        },
        'luminosity_changes': {
            'mean_diff': float((df['mean_luminosity_12m'] - df['mean_luminosity_6m']).mean()),
            'correlation': float(df['mean_luminosity_6m'].corr(df['mean_luminosity_12m']))
        },
        'trend_changes': {
            'mean_diff': float((df['trend_12m'] - df['trend_6m']).mean()),
            'correlation': float(df['trend_6m'].corr(df['trend_12m'])) if not pd.isna(df['trend_6m'].corr(df['trend_12m'])) else None
        },
        'processing_time': {
            'time_6m_mean': float(df['processing_time_6m'].mean()),
            'time_12m_mean': float(df['processing_time_12m'].mean()),
            'time_ratio': float(df['processing_time_12m'].mean() / df['processing_time_6m'].mean())
        },
        'data_points': {
            'points_6m_mean': float(df['data_points_6m'].mean()),
            'points_12m_mean': float(df['data_points_12m'].mean())
        }
    }
    
    return stats


def display_comparison_results(comparison_data, stats):
    """Affiche les résultats de comparaison"""
    print(f"\n📈 RÉSULTATS DE LA COMPARAISON")
    print("=" * 60)
    
    print(f"📊 {stats['total_fincas']} fincas analysées")
    
    print(f"\n🎯 CHANGEMENTS DE SCORE:")
    print(f"   • Amélioré: {stats['score_changes']['improved']} fincas")
    print(f"   • Détérioré: {stats['score_changes']['worsened']} fincas")
    print(f"   • Inchangé: {stats['score_changes']['unchanged']} fincas")
    print(f"   • Différence moyenne: {stats['score_changes']['mean_diff']:.2f} points")
    
    print(f"\n💡 LUMINOSITÉ:")
    print(f"   • Différence moyenne: {stats['luminosity_changes']['mean_diff']:.3f}")
    print(f"   • Corrélation 6m/12m: {stats['luminosity_changes']['correlation']:.3f}")
    
    print(f"\n📈 TENDANCES:")
    print(f"   • Différence moyenne: {stats['trend_changes']['mean_diff']:.3f}")
    correlation = stats['trend_changes']['correlation']
    if correlation is not None:
        print(f"   • Corrélation 6m/12m: {correlation:.3f}")
    else:
        print(f"   • Corrélation 6m/12m: Non calculable")
    
    print(f"\n⏱️ PERFORMANCE:")
    print(f"   • Temps 6 mois: {stats['processing_time']['time_6m_mean']:.1f}s")
    print(f"   • Temps 12 mois: {stats['processing_time']['time_12m_mean']:.1f}s")
    print(f"   • Ratio temps: {stats['processing_time']['time_ratio']:.2f}x")
    
    print(f"\n📊 DONNÉES:")
    print(f"   • Points 6 mois: {stats['data_points']['points_6m_mean']:.1f}")
    print(f"   • Points 12 mois: {stats['data_points']['points_12m_mean']:.1f}")


def save_comparison_results(comparison_data, stats):
    """Sauvegarde les résultats de comparaison"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Créer le dossier de sortie
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'comparison_6vs12'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder les données de comparaison
    comparison_file = output_dir / f"viirs_6vs12_comparison_{timestamp}.json"
    with open(comparison_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'comparison_data': comparison_data,
            'statistics': stats
        }, f, indent=2)
    
    # Sauvegarder en CSV
    csv_file = output_dir / f"viirs_6vs12_comparison_{timestamp}.csv"
    df = pd.DataFrame(comparison_data)
    df.to_csv(csv_file, index=False)
    
    print(f"\n💾 RÉSULTATS SAUVEGARDÉS:")
    print(f"   📄 JSON: {comparison_file}")
    print(f"   📊 CSV: {csv_file}")


def generate_recommendation(stats):
    """Génère une recommandation basée sur les résultats"""
    print(f"\n🎯 RECOMMANDATION")
    print("=" * 40)
    
    # Critères d'évaluation
    score_improvement = stats['score_changes']['improved'] / stats['total_fincas']
    time_penalty = stats['processing_time']['time_ratio']
    
    # Calculer la qualité de corrélation (gérer les valeurs None)
    luminosity_corr = stats['luminosity_changes']['correlation']
    trend_corr = stats['trend_changes']['correlation']
    
    if trend_corr is not None:
        correlation_quality = (luminosity_corr + trend_corr) / 2
    else:
        correlation_quality = luminosity_corr  # Utiliser seulement la corrélation luminosité
    
    print(f"📊 Critères d'évaluation:")
    print(f"   • Amélioration des scores: {score_improvement:.1%}")
    print(f"   • Pénalité temps: {time_penalty:.2f}x")
    print(f"   • Qualité corrélation: {correlation_quality:.3f}")
    
    # Recommandation
    if score_improvement > 0.6 and time_penalty < 2.0:
        print(f"\n✅ RECOMMANDATION: PASSER À 12 MOIS")
        print(f"   • Amélioration significative des scores")
        print(f"   • Coût de calcul acceptable")
        print(f"   • Meilleure détection des patterns saisonniers")
    elif score_improvement > 0.4 and time_penalty < 1.5:
        print(f"\n⚠️ RECOMMANDATION: TESTER SUR PLUS DE FINCAS")
        print(f"   • Amélioration modérée des scores")
        print(f"   • Nécessite plus de validation")
    else:
        print(f"\n❌ RECOMMANDATION: RESTER À 6 MOIS")
        print(f"   • Amélioration insuffisante")
        print(f"   • Coût de calcul trop élevé")
        print(f"   • 6 mois suffisent pour l'analyse")


def main():
    """Fonction principale"""
    print("🌙 TEST VIIRS 6 MOIS vs 12 MOIS")
    print("=" * 50)
    print("Comparaison des performances et qualité d'analyse")
    
    try:
        # Charger les fincas de test
        test_fincas = load_test_fincas()
        
        # Analyser chaque finca avec 6 et 12 mois
        test_results = []
        for finca_data in test_fincas:
            result = analyze_finca_viirs_periods(finca_data, periods=[6, 12])
            if result:
                test_results.append(result)
        
        if not test_results:
            print("❌ Aucun résultat obtenu")
            return
        
        # Comparer les résultats
        comparison_data = compare_periods_analysis(test_results)
        
        if not comparison_data:
            print("❌ Aucune comparaison possible")
            return
        
        # Calculer les statistiques
        stats = calculate_statistics(comparison_data)
        
        # Afficher les résultats
        display_comparison_results(comparison_data, stats)
        
        # Sauvegarder les résultats
        save_comparison_results(comparison_data, stats)
        
        # Générer la recommandation
        generate_recommendation(stats)
        
        print(f"\n🎉 Test terminé avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
