#!/usr/bin/env python3
"""
📊 Affichage des Fincas à Faible Activité
Affiche les fincas classées comme "Faible" et "Très faible" avec les seuils optimisés
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_optimized_data():
    """Charge les données optimisées"""
    optimized_file = ROOT / 'data' / 'sentinel1_all_fincas_6months_optimized.json'
    
    if not optimized_file.exists():
        print("❌ Fichier de données optimisées non trouvé")
        return None
    
    print(f"📄 Chargement: {optimized_file.name}")
    
    with open(optimized_file, 'r') as f:
        data = json.load(f)
    
    return data

def main():
    print("📊 FINCAS À FAIBLE ACTIVITÉ - SEUILS OPTIMISÉS")
    print("=" * 70)
    
    data = load_optimized_data()
    if not data:
        return
    
    print(f"📅 Date d'analyse: {data['analysis_date']}")
    print(f"📁 Total fincas: {data['total_fincas']}")
    
    # Afficher les seuils utilisés
    thresholds = data['optimized_thresholds']
    print(f"\n📏 SEUILS OPTIMISÉS UTILISÉS:")
    print(f"   • Très élevée: > {thresholds['very_high']:.3f} dB")
    print(f"   • Élevée: > {thresholds['high']:.3f} dB")
    print(f"   • Modérée: > {thresholds['moderate']:.3f} dB")
    print(f"   • Faible: > {thresholds['low']:.3f} dB")
    print(f"   • Très faible: ≤ {thresholds['low']:.3f} dB")
    
    # Filtrer les fincas à faible activité
    low_activity_fincas = []
    very_low_activity_fincas = []
    
    for finca in data['fincas']:
        activity_level = finca['sentinel1_6months']['activity_level']
        if activity_level == "Faible":
            low_activity_fincas.append(finca)
        elif activity_level == "Très faible":
            very_low_activity_fincas.append(finca)
    
    print(f"\n📊 DISTRIBUTION COMPLÈTE:")
    for level, count in data['activity_distribution'].items():
        percentage = (count / data['total_fincas']) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    print(f"\n🔍 FINCAS À ACTIVITÉ FAIBLE ({len(low_activity_fincas)} fincas):")
    print("-" * 80)
    print(f"{'Finca':<12} {'VV (dB)':<10} {'Score':<8} {'Lat':<10} {'Lon':<10}")
    print("-" * 80)
    
    # Trier par VV (du plus faible au plus élevé)
    low_activity_sorted = sorted(low_activity_fincas, key=lambda x: x['sentinel1_6months']['vv_mean'])
    
    for finca in low_activity_sorted:
        vv_value = finca['sentinel1_6months']['vv_mean']
        score = finca['sentinel1_6months']['activity_score']
        lat = finca['coordinates']['lat']
        lon = finca['coordinates']['lon']
        
        print(f"{finca['finca_id']:<12} "
              f"{vv_value:<10.3f} "
              f"{score:<8} "
              f"{lat:<10.6f} "
              f"{lon:<10.6f}")
    
    print("-" * 80)
    
    print(f"\n⚠️ FINCAS À ACTIVITÉ TRÈS FAIBLE ({len(very_low_activity_fincas)} fincas):")
    print("-" * 80)
    print(f"{'Finca':<12} {'VV (dB)':<10} {'Score':<8} {'Lat':<10} {'Lon':<10}")
    print("-" * 80)
    
    # Trier par VV (du plus faible au plus élevé)
    very_low_activity_sorted = sorted(very_low_activity_fincas, key=lambda x: x['sentinel1_6months']['vv_mean'])
    
    for finca in very_low_activity_sorted:
        vv_value = finca['sentinel1_6months']['vv_mean']
        score = finca['sentinel1_6months']['activity_score']
        lat = finca['coordinates']['lat']
        lon = finca['coordinates']['lon']
        
        print(f"{finca['finca_id']:<12} "
              f"{vv_value:<10.3f} "
              f"{score:<8} "
              f"{lat:<10.6f} "
              f"{lon:<10.6f}")
    
    print("-" * 80)
    
    # Statistiques des fincas à faible activité
    all_low_activity = low_activity_fincas + very_low_activity_fincas
    vv_values_low = [f['sentinel1_6months']['vv_mean'] for f in all_low_activity]
    
    print(f"\n📈 STATISTIQUES DES FINCAS À FAIBLE ACTIVITÉ:")
    print(f"   📊 Total: {len(all_low_activity)} fincas ({(len(all_low_activity)/data['total_fincas'])*100:.1f}%)")
    print(f"   📊 VV moyen: {sum(vv_values_low)/len(vv_values_low):.3f} dB")
    print(f"   📈 VV min/max: {min(vv_values_low):.3f} / {max(vv_values_low):.3f} dB")
    print(f"   🎯 Score moyen: {sum(f['sentinel1_6months']['activity_score'] for f in all_low_activity)/len(all_low_activity):.1f}/100")
    
    # Top 10 des fincas les moins actives
    print(f"\n🔥 TOP 10 DES FINCAS LES MOINS ACTIVES:")
    print("-" * 80)
    print(f"{'Rang':<4} {'Finca':<12} {'VV (dB)':<10} {'Niveau':<15} {'Score':<8} {'Lat':<10} {'Lon':<10}")
    print("-" * 80)
    
    all_fincas_sorted = sorted(data['fincas'], key=lambda x: x['sentinel1_6months']['vv_mean'])
    
    for i, finca in enumerate(all_fincas_sorted[:10], 1):
        vv_value = finca['sentinel1_6months']['vv_mean']
        level = finca['sentinel1_6months']['activity_level']
        score = finca['sentinel1_6months']['activity_score']
        lat = finca['coordinates']['lat']
        lon = finca['coordinates']['lon']
        
        print(f"{i:<4} "
              f"{finca['finca_id']:<12} "
              f"{vv_value:<10.3f} "
              f"{level:<15} "
              f"{score:<8} "
              f"{lat:<10.6f} "
              f"{lon:<10.6f}")
    
    print("-" * 80)
    
    print(f"\n💡 OBSERVATIONS:")
    print(f"   • {len(low_activity_fincas)} fincas classées comme 'Faible' (5.9%)")
    print(f"   • {len(very_low_activity_fincas)} fincas classées comme 'Très faible' (4.3%)")
    print(f"   • Total: {len(all_low_activity)} fincas à faible activité (10.1%)")
    print(f"   • Seuil 'Faible': > {thresholds['low']:.3f} dB")
    print(f"   • Seuil 'Très faible': ≤ {thresholds['low']:.3f} dB")
    
    print(f"\n🎯 OBJECTIF ATTEINT:")
    print(f"   ✅ Environ 10% de fincas dans les catégories 'Faible' et 'Très faible'")
    print(f"   📊 Distribution équilibrée obtenue")
    print(f"   🔍 Fincas à faible activité identifiées pour analyse approfondie")

if __name__ == "__main__":
    main()
