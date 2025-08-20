#!/usr/bin/env python3
"""
📡 Activité Radar Sentinel-1 - Top 20 Fincas
Affiche l'activité radar détectée par Sentinel-1 pour les 20 premières fincas
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

def calculate_activity_score(vv_value):
    """Calcule un score d'activité basé sur la valeur VV Sentinel-1"""
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

def main():
    print("📡 ACTIVITÉ RADAR SENTINEL-1 - TOP 20 FINCAS")
    print("=" * 70)
    
    # Charger les données
    s1_data = load_sentinel1_data()
    
    if not s1_data:
        print("❌ Données manquantes")
        return
    
    # Extraire et trier les fincas par activité radar (VV décroissant = plus actif)
    fincas = []
    for finca in s1_data['fincas']:
        vv_value = finca['avg_vv']
        activity_level = finca['overall_activity']
        activity_score = calculate_activity_score(vv_value)
        
        fincas.append({
            'finca_id': finca['finca_id'],
            'coordinates': finca['coordinates'],
            'vv_value': vv_value,
            'activity_level': activity_level,
            'activity_score': activity_score,
            'latest_date': finca['latest_date']
        })
    
    # Trier par VV (décroissant = plus actif)
    fincas_sorted = sorted(fincas, key=lambda x: x['vv_value'], reverse=True)
    
    print(f"📊 {len(fincas_sorted)} fincas analysées")
    print(f"🔍 Rayon d'analyse: {s1_data['analysis_radius']}m")
    print(f"📅 Date d'analyse: {fincas_sorted[0]['latest_date']}")
    print(f"🛰️ Résolution: 10m (Sentinel-1 SAR)")
    
    print(f"\n📡 TOP 20 PAR ACTIVITÉ RADAR")
    print("-" * 90)
    print(f"{'Rang':<4} {'Finca':<12} {'VV (dB)':<10} {'Niveau':<15} {'Score':<8} {'Lat':<10} {'Lon':<10}")
    print("-" * 90)
    
    # Afficher le top 20
    for i, finca in enumerate(fincas_sorted[:20], 1):
        print(f"{i:<4} "
              f"{finca['finca_id']:<12} "
              f"{finca['vv_value']:<10.3f} "
              f"{finca['activity_level']:<15} "
              f"{finca['activity_score']:<8} "
              f"{finca['coordinates']['lat']:<10.6f} "
              f"{finca['coordinates']['lon']:<10.6f}")
    
    print("-" * 90)
    
    # Statistiques du top 20
    top20 = fincas_sorted[:20]
    vv_values = [f['vv_value'] for f in top20]
    activity_scores = [f['activity_score'] for f in top20]
    
    print(f"\n📊 STATISTIQUES DU TOP 20")
    print("=" * 50)
    print(f"📈 VV moyen: {sum(vv_values)/len(vv_values):.3f} dB")
    print(f"📊 VV min/max: {min(vv_values):.3f} / {max(vv_values):.3f} dB")
    print(f"🎯 Score d'activité moyen: {sum(activity_scores)/len(activity_scores):.1f}/100")
    
    # Distribution des niveaux d'activité
    activity_levels = [f['activity_level'] for f in top20]
    level_counts = {}
    for level in activity_levels:
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print(f"\n🎯 Distribution des niveaux d'activité:")
    for level, count in level_counts.items():
        percentage = (count / len(top20)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    # Analyse des plus actives
    most_active = fincas_sorted[:5]
    print(f"\n🔥 TOP 5 PLUS ACTIVES:")
    for i, finca in enumerate(most_active, 1):
        print(f"   {i}. {finca['finca_id']}: VV={finca['vv_value']:.3f} dB ({finca['activity_level']})")
    
    # Analyse des moins actives du top 20
    least_active_top20 = fincas_sorted[15:20]  # Les 5 moins actives du top 20
    print(f"\n❄️  MOINS ACTIVES DU TOP 20:")
    for i, finca in enumerate(least_active_top20, 16):
        print(f"   {i}. {finca['finca_id']}: VV={finca['vv_value']:.3f} dB ({finca['activity_level']})")
    
    # Analyse géographique
    print(f"\n🗺️ ANALYSE GÉOGRAPHIQUE")
    print("=" * 30)
    
    # Grouper par zones géographiques approximatives
    zones = {}
    for finca in top20:
        lat_zone = round(finca['coordinates']['lat'], 2)
        lon_zone = round(finca['coordinates']['lon'], 2)
        zone_key = f"{lat_zone:.2f}, {lon_zone:.2f}"
        
        if zone_key not in zones:
            zones[zone_key] = []
        zones[zone_key].append(finca)
    
    print(f"📍 Zones géographiques du top 20:")
    for zone, zone_fincas in zones.items():
        avg_vv = sum([f['vv_value'] for f in zone_fincas]) / len(zone_fincas)
        print(f"   • Zone {zone}: {len(zone_fincas)} fincas (VV moyen: {avg_vv:.3f} dB)")
        for finca in zone_fincas:
            print(f"     - {finca['finca_id']}: VV={finca['vv_value']:.3f} dB")
    
    # Sauvegarder les résultats
    output_dir = ROOT / 'data' / 'sentinel1_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = output_dir / f"top20_radar_activity_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    results_data = {
        'analysis_date': datetime.now().isoformat(),
        'total_fincas': len(fincas_sorted),
        'analysis_radius': s1_data['analysis_radius'],
        'top20_fincas': top20,
        'statistics': {
            'vv_mean': sum(vv_values)/len(vv_values),
            'vv_min': min(vv_values),
            'vv_max': max(vv_values),
            'activity_score_mean': sum(activity_scores)/len(activity_scores),
            'activity_distribution': level_counts
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\n📁 Résultats sauvegardés: {results_file}")
    
    print(f"\n💡 OBSERVATIONS:")
    print(f"   • Les fincas les plus actives ont un VV > -10 dB")
    print(f"   • L'activité radar détecte les mouvements et changements de surface")
    print(f"   • Un VV élevé indique une activité humaine récente")
    print(f"   • L'analyse à 50m évite les interférences des zones voisines")

if __name__ == "__main__":
    main()
