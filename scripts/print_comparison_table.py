#!/usr/bin/env python3
"""
📊 Tableau de Comparaison Sentinel-1 vs VIIRS
Affiche un tableau détaillé des résultats
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    # Charger l'analyse
    analysis_file = ROOT / 'data' / 'comparison_analysis' / 'concordance_analysis_20250819_230959.json'
    
    with open(analysis_file, 'r') as f:
        analysis = json.load(f)
    
    print("🔬 TABLEAU DE COMPARAISON SENTINEL-1 vs VIIRS")
    print("=" * 80)
    
    # En-tête du tableau
    print(f"{'Finca':<12} {'VIIRS Lum':<10} {'VIIRS Score':<12} {'VIIRS Norm':<11} {'S1 VV':<8} {'S1 Activity':<12} {'S1 Norm':<8}")
    print("-" * 80)
    
    # Données
    for finca in analysis['fincas_analysis']:
        print(f"{finca['finca_id']:<12} "
              f"{finca['viirs_luminosity']:<10.2f} "
              f"{finca['viirs_score']:<12} "
              f"{finca['viirs_normalized']:<11.1f} "
              f"{finca['s1_vv']:<8.1f} "
              f"{finca['s1_activity']:<12} "
              f"{finca['s1_normalized']:<8.1f}")
    
    print("\n📊 CORRÉLATIONS:")
    for key, corr in analysis['correlations'].items():
        if not str(corr['pearson_r']).lower() == 'nan':
            print(f"   • {key}: r={corr['pearson_r']:.3f} (p={corr['pearson_p']:.3f})")
    
    print(f"\n🎯 CONCORDANCE: {analysis['concordance_summary']['concordance_rate']:.1%}")
    
    print("\n💡 OBSERVATIONS:")
    print("   • Petit échantillon (5 fincas) → corrélations non significatives")
    print("   • Tendance positive visible (r=0.73-0.78)")
    print("   • Besoin de plus de données pour valider")

if __name__ == "__main__":
    main()
