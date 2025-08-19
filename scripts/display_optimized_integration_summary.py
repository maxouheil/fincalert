#!/usr/bin/env python3
"""
📊 Résumé de l'Intégration Frontend - Données Optimisées
Affiche un résumé de l'intégration des données Sentinel-1 optimisées
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_optimized_data():
    """Charge les données optimisées"""
    optimized_file = ROOT / 'data' / 'combined_scoring_optimized_sentinel1.json'
    
    if not optimized_file.exists():
        print("❌ Fichier de données optimisées non trouvé")
        return None
    
    print(f"📄 Chargement: {optimized_file.name}")
    
    with open(optimized_file, 'r') as f:
        data = json.load(f)
    
    return data

def main():
    print("📊 RÉSUMÉ DE L'INTÉGRATION FRONTEND - DONNÉES OPTIMISÉES")
    print("=" * 70)
    
    data = load_optimized_data()
    if not data:
        return
    
    print(f"📅 Date d'intégration: {data['analysis_date']}")
    print(f"📁 Total fincas: {data['total_fincas']}")
    print(f"⚖️ Poids utilisés: NDVI {data['weights_used']['ndvi']*100}% + S1 {data['weights_used']['sentinel1']*100}%")
    
    print(f"\n📈 STATISTIQUES DU SCORING COMBINÉ:")
    score_stats = data['score_statistics']
    print(f"   📊 Score moyen: {score_stats['mean']}/100")
    print(f"   📈 Score min/max: {score_stats['min']} / {score_stats['max']}")
    print(f"   📉 Écart-type: {score_stats['std']}")
    
    print(f"\n🎯 DISTRIBUTION DES NIVEAUX D'ABANDON:")
    for level, count in data['abandonment_distribution'].items():
        percentage = (count / data['total_fincas']) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    print(f"\n📏 SEUILS SENTINEL-1 OPTIMISÉS:")
    thresholds = data['sentinel1_thresholds']
    print(f"   • Très élevée: > {thresholds['very_high']:.3f} dB")
    print(f"   • Élevée: > {thresholds['high']:.3f} dB")
    print(f"   • Modérée: > {thresholds['moderate']:.3f} dB")
    print(f"   • Faible: > {thresholds['low']:.3f} dB")
    print(f"   • Très faible: ≤ {thresholds['low']:.3f} dB")
    
    # Top 10 des fincas les plus à risque
    print(f"\n🔥 TOP 10 DES FINCAS LES PLUS À RISQUE:")
    print("-" * 80)
    print(f"{'Rang':<4} {'Finca':<12} {'Score':<8} {'Niveau':<15} {'NDVI':<8} {'S1':<8}")
    print("-" * 80)
    
    sorted_results = sorted(data['results'], key=lambda x: x['combined_scoring']['overall_score'], reverse=True)
    
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
    
    # Top 10 des fincas les moins à risque
    print(f"\n📊 TOP 10 DES FINCAS LES MOINS À RISQUE:")
    print("-" * 80)
    print(f"{'Rang':<4} {'Finca':<12} {'Score':<8} {'Niveau':<15} {'NDVI':<8} {'S1':<8}")
    print("-" * 80)
    
    sorted_results_reverse = sorted(data['results'], key=lambda x: x['combined_scoring']['overall_score'])
    
    for i, result in enumerate(sorted_results_reverse[:10], 1):
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
    
    print(f"\n💡 INTÉGRATION FRONTEND:")
    print(f"   ✅ Types TypeScript mis à jour")
    print(f"   ✅ Composant NewPopup mis à jour")
    print(f"   ✅ Données optimisées chargées dynamiquement")
    print(f"   ✅ Affichage des scores Sentinel-1 optimisés")
    print(f"   ✅ Calcul du score total mis à jour")
    print(f"   ✅ Gestion des états de chargement")
    
    print(f"\n📁 FICHIERS FRONTEND MIS À JOUR:")
    print(f"   • frontend/src/utils/types.ts")
    print(f"   • frontend/src/utils/data.ts")
    print(f"   • frontend/src/components/NewPopup.tsx")
    print(f"   • frontend/public/data/combined_scoring_optimized_sentinel1.json")
    
    print(f"\n🚀 PROCHAINES ÉTAPES:")
    print(f"   • Tester l'interface utilisateur")
    print(f"   • Vérifier l'affichage des données optimisées")
    print(f"   • Optimiser les performances si nécessaire")
    print(f"   • Ajouter des filtres par niveau d'activité")

if __name__ == "__main__":
    main()
