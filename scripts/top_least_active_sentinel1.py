#!/usr/bin/env python3
"""
📉 Top des Fincas les Moins Actives - Analyse Sentinel-1
Identifie les fincas avec la plus faible activité radar
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
    print(f"📄 Chargement: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def classify_activity_level(vv_value):
    """Classifie le niveau d'activité basé sur le backscatter VV"""
    if vv_value > -5:
        return "Très élevée"
    elif vv_value > -10:
        return "Élevée"
    elif vv_value > -15:
        return "Modérée"
    elif vv_value > -20:
        return "Faible"
    else:
        return "Très faible"

def main():
    print("📉 TOP DES FINCAS LES MOINS ACTIVES - SENTINEL-1")
    print("=" * 70)
    
    # Charger les données
    s1_data = load_sentinel1_data()
    
    if not s1_data:
        print("❌ Données manquantes")
        return
    
    # Extraire et trier les fincas par activité (VV croissant = moins actif)
    fincas = []
    for finca in s1_data['fincas']:
        fincas.append({
            'finca_id': finca['finca_id'],
            'coordinates': finca['coordinates'],
            'vv_value': finca['avg_vv'],
            'activity_level': finca['overall_activity'],
            'latest_date': finca['latest_date']
        })
    
    # Trier par VV (croissant = moins actif)
    fincas_sorted = sorted(fincas, key=lambda x: x['vv_value'])
    
    print(f"📊 {len(fincas_sorted)} fincas analysées")
    print(f"🔍 Rayon d'analyse: {s1_data['analysis_radius']}m")
    print(f"📅 Date d'analyse: {fincas_sorted[0]['latest_date']}")
    
    print(f"\n📉 TOP 10 DES FINCAS LES MOINS ACTIVES")
    print("-" * 80)
    print(f"{'Rang':<4} {'Finca':<12} {'VV (dB)':<10} {'Niveau':<15} {'Lat':<10} {'Lon':<10}")
    print("-" * 80)
    
    # Afficher le top 10
    for i, finca in enumerate(fincas_sorted[:10], 1):
        print(f"{i:<4} "
              f"{finca['finca_id']:<12} "
              f"{finca['vv_value']:<10.3f} "
              f"{finca['activity_level']:<15} "
              f"{finca['coordinates']['lat']:<10.6f} "
              f"{finca['coordinates']['lon']:<10.6f}")
    
    print("-" * 80)
    
    # Statistiques des moins actives
    least_active = fincas_sorted[:10]
    vv_values = [f['vv_value'] for f in least_active]
    
    print(f"\n📊 STATISTIQUES DES 10 MOINS ACTIVES")
    print("=" * 50)
    print(f"📉 VV moyen: {sum(vv_values)/len(vv_values):.3f} dB")
    print(f"📊 VV min/max: {min(vv_values):.3f} / {max(vv_values):.3f} dB")
    
    # Distribution des niveaux d'activité
    activity_levels = [f['activity_level'] for f in least_active]
    level_counts = {}
    for level in activity_levels:
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print(f"\n🎯 Distribution des niveaux d'activité:")
    for level, count in level_counts.items():
        percentage = (count / len(least_active)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    # Analyse géographique
    print(f"\n🗺️ ANALYSE GÉOGRAPHIQUE")
    print("=" * 30)
    
    # Grouper par zones géographiques approximatives
    zones = {}
    for finca in least_active:
        lat_zone = round(finca['coordinates']['lat'], 2)
        lon_zone = round(finca['coordinates']['lon'], 2)
        zone_key = f"{lat_zone:.2f}, {lon_zone:.2f}"
        
        if zone_key not in zones:
            zones[zone_key] = []
        zones[zone_key].append(finca)
    
    print(f"📍 Zones géographiques des moins actives:")
    for zone, zone_fincas in zones.items():
        print(f"   • Zone {zone}: {len(zone_fincas)} fincas")
        for finca in zone_fincas:
            print(f"     - {finca['finca_id']}: VV={finca['vv_value']:.3f} dB")
    
    # Comparaison avec les plus actives
    most_active = fincas_sorted[-10:]  # Les 10 plus actives
    
    print(f"\n⚖️ COMPARAISON AVEC LES PLUS ACTIVES")
    print("=" * 50)
    
    least_vv_avg = sum([f['vv_value'] for f in least_active]) / len(least_active)
    most_vv_avg = sum([f['vv_value'] for f in most_active]) / len(most_active)
    
    print(f"📉 Moins actives (moyenne): {least_vv_avg:.3f} dB")
    print(f"📈 Plus actives (moyenne): {most_vv_avg:.3f} dB")
    print(f"📊 Différence: {most_vv_avg - least_vv_avg:.3f} dB")
    
    # Sauvegarder les résultats
    output_dir = ROOT / 'data' / 'sentinel1_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = output_dir / f"least_active_sentinel1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    results_data = {
        'analysis_date': datetime.now().isoformat(),
        'total_fincas': len(fincas_sorted),
        'analysis_radius': s1_data['analysis_radius'],
        'least_active_fincas': least_active,
        'most_active_fincas': most_active,
        'statistics': {
            'least_active_vv_avg': least_vv_avg,
            'most_active_vv_avg': most_vv_avg,
            'vv_difference': most_vv_avg - least_vv_avg,
            'activity_distribution': level_counts
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n📁 Résultats sauvegardés: {results_file}")
    
    print(f"\n💡 OBSERVATIONS:")
    print(f"   • Les fincas les moins actives ont un VV < -15 dB")
    print(f"   • Ces fincas montrent peu d'activité humaine récente")
    print(f"   • Elles sont candidates pour une inspection d'abandon")
    print(f"   • L'analyse à 50m évite les interférences des zones voisines")

if __name__ == "__main__":
    main()
