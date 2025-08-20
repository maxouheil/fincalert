#!/usr/bin/env python3
"""
📊 Comparaison Complète des Analyses Sentinel-1 - Tous Niveaux de Précision
Compare les résultats avec différents rayons d'analyse (500m, 200m, 100m, 50m)
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    # Charger toutes les analyses disponibles
    analyses = {}
    
    # Chercher les fichiers de résumé
    data_dirs = [
        'sentinel1_analysis',
        'sentinel1_precise_analysis', 
        'sentinel1_ultra_precise_analysis'
    ]
    
    for data_dir in data_dirs:
        dir_path = ROOT / 'data' / data_dir
        if dir_path.exists():
            summary_files = list(dir_path.glob('*summary*.json'))
            for file in summary_files:
                with open(file, 'r') as f:
                    data = json.load(f)
                    radius = data.get('analysis_radius', 'unknown')
                    analyses[radius] = data
    
    if not analyses:
        print("❌ Aucune analyse trouvée")
        return
    
    print("📊 COMPARAISON COMPLÈTE SENTINEL-1 - TOUS NIVEAUX DE PRÉCISION")
    print("=" * 80)
    
    print(f"🔍 Rayons disponibles: {list(analyses.keys())}")
    
    # Trier par rayon (convertir en int pour le tri)
    sorted_radii = sorted(analyses.keys(), key=lambda x: int(x) if str(x).isdigit() else 999999)
    
    # Créer un dictionnaire pour faciliter la comparaison
    finca_data = {}
    
    # Collecter toutes les données par finca
    for radius in sorted_radii:
        analysis = analyses[radius]
        for finca in analysis['fincas']:
            finca_id = finca['finca_id']
            if finca_id not in finca_data:
                finca_data[finca_id] = {}
            finca_data[finca_id][radius] = {
                'vv': finca['avg_vv'],
                'activity': finca['overall_activity']
            }
    
    # Afficher le tableau comparatif
    print(f"\n📈 COMPARAISON DÉTAILLÉE PAR FINCA")
    print("-" * 120)
    
    # En-tête
    header = f"{'Finca':<12}"
    for radius in sorted_radii:
        header += f" {'VV '+str(radius)+'m':<12} {'Act '+str(radius)+'m':<12}"
    print(header)
    print("-" * 120)
    
    # Données par finca
    for finca_id in sorted(finca_data.keys()):
        row = f"{finca_id:<12}"
        for radius in sorted_radii:
            if radius in finca_data[finca_id]:
                data = finca_data[finca_id][radius]
                row += f" {data['vv']:<12.3f} {data['activity']:<12}"
            else:
                row += f" {'N/A':<12} {'N/A':<12}"
        print(row)
    
    print("-" * 120)
    
    # Statistiques globales par rayon
    print(f"\n📊 STATISTIQUES GLOBALES PAR RAYON")
    print("=" * 80)
    
    for radius in sorted_radii:
        analysis = analyses[radius]
        stats = analysis['vv_statistics']
        distribution = analysis['activity_distribution']
        
        print(f"\n🔍 RAYON {radius}m:")
        print(f"   📁 Fincas analysées: {analysis['total_fincas']}")
        print(f"   📊 VV moyen: {stats['mean']:.3f} dB")
        print(f"   📈 VV min/max: {stats['min']:.3f} / {stats['max']:.3f} dB")
        print(f"   📉 Écart-type: {stats['std']:.3f} dB")
        print(f"   🎯 Distribution d'activité:")
        for level, count in distribution.items():
            percentage = (count / analysis['total_fincas']) * 100
            print(f"      • {level}: {count} fincas ({percentage:.1f}%)")
    
    # Analyse des changements de catégorie
    print(f"\n🔄 ANALYSE DES CHANGEMENTS DE CATÉGORIE")
    print("=" * 50)
    
    if len(sorted_radii) >= 2:
        # Comparer les rayons consécutifs
        for i in range(len(sorted_radii) - 1):
            radius1 = sorted_radii[i]
            radius2 = sorted_radii[i + 1]
            
            changes = 0
            total_common = 0
            
            for finca_id in finca_data:
                if radius1 in finca_data[finca_id] and radius2 in finca_data[finca_id]:
                    total_common += 1
                    if finca_data[finca_id][radius1]['activity'] != finca_data[finca_id][radius2]['activity']:
                        changes += 1
                        print(f"🔄 {finca_id}: {radius1}m ({finca_data[finca_id][radius1]['activity']}) → {radius2}m ({finca_data[finca_id][radius2]['activity']})")
            
            if total_common > 0:
                change_rate = (changes / total_common) * 100
                print(f"📊 {radius1}m → {radius2}m: {changes}/{total_common} changements ({change_rate:.1f}%)")
    
    # Tendances générales
    print(f"\n📈 TENDANCES GÉNÉRALES")
    print("=" * 30)
    
    vv_means = [analyses[radius]['vv_statistics']['mean'] for radius in sorted_radii]
    
    print(f"📊 Évolution du VV moyen:")
    for i, radius in enumerate(sorted_radii):
        print(f"   • {radius}m: {vv_means[i]:.3f} dB")
    
    # Calculer la tendance
    if len(vv_means) > 1:
        trend = "↗️ Augmente" if vv_means[-1] > vv_means[0] else "↘️ Diminue" if vv_means[-1] < vv_means[0] else "➡️ Stable"
        print(f"📈 Tendance générale: {trend}")
    
    print(f"\n💡 OBSERVATIONS:")
    print(f"   • Plus le rayon est petit, plus l'analyse est précise")
    print(f"   • Les changements de catégorie indiquent la sensibilité au périmètre")
    print(f"   • Un rayon de 50m donne la vue la plus détaillée de l'activité")
    print(f"   • Un rayon de 500m donne une vue d'ensemble plus large")

if __name__ == "__main__":
    main()
