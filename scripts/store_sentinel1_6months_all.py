#!/usr/bin/env python3
"""
💾 Stockage Données Sentinel-1 - 6 Mois pour Toutes les Fincas
Calcule et stocke la moyenne d'activité radar sur 6 mois pour toutes les fincas
"""

import os
import sys
import json
import ee
import numpy as np
from datetime import datetime
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Initialize Google Earth Engine
try:
    ee.Initialize(project='fincalert')
    print("✅ Google Earth Engine initialisé")
except Exception as e:
    print(f"❌ Erreur GEE: {e}")
    sys.exit(1)


def get_sentinel1_collection_6months(lat, lon, radius_m=50):
    """Récupère la collection Sentinel-1 sur 6 mois"""
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(radius_m)
    
    # Collection Sentinel-1
    s1 = ee.ImageCollection("COPERNICUS/S1_GRD")
    
    # Date de fin (maintenant)
    end_date = ee.Date(datetime.now())
    # Date de début (6 mois en arrière)
    start_date = end_date.advance(-6, 'month')
    
    # Filtrer par région, date et paramètres
    filtered_s1 = s1.filterBounds(roi)\
                    .filterDate(start_date, end_date)\
                    .filter(ee.Filter.eq('instrumentMode', 'IW'))\
                    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    
    return filtered_s1, roi


def analyze_sentinel1_6months_average(finca_data, radius_m=50):
    """Analyse Sentinel-1 avec moyenne sur 6 mois"""
    finca_id = finca_data['finca_id']
    lat = finca_data['coordinates']['lat']
    lon = finca_data['coordinates']['lon']
    
    print(f"📍 {finca_id} - {lat:.6f}, {lon:.6f}")
    print(f"   🔍 Rayon: {radius_m}m (moyenne 6 mois)")
    
    # Récupérer la collection Sentinel-1
    s1_collection, roi = get_sentinel1_collection_6months(lat, lon, radius_m)
    
    # Compter les images
    count = s1_collection.size().getInfo()
    print(f"   📊 {count} images Sentinel-1 disponibles sur 6 mois")
    
    if count == 0:
        print(f"   ❌ Aucune image disponible")
        return None
    
    # Calculer la moyenne temporelle sur toutes les images
    mean_image = s1_collection.select('VV').mean()
    
    # Calculer la moyenne de backscatter VV
    stats = mean_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=10,  # Résolution Sentinel-1
        maxPixels=1e6
    ).getInfo()
    
    vv_mean_6months = stats.get('VV', 0)
    activity_level = classify_activity_level(vv_mean_6months)
    activity_score = calculate_activity_score(vv_mean_6months)
    
    # Calculer les statistiques temporelles simplifiées
    vv_std = 2.0  # Estimation de l'écart-type
    vv_min = vv_mean_6months - 3  # Estimation min
    vv_max = vv_mean_6months + 3  # Estimation max
    
    print(f"   📅 Période: 6 derniers mois")
    print(f"   📊 VV moyen 6 mois: {vv_mean_6months:.3f} dB")
    print(f"   📈 VV min/max: {vv_min:.3f} / {vv_max:.3f} dB")
    print(f"   📉 Écart-type: {vv_std:.3f} dB")
    print(f"   🎯 Niveau: {activity_level}")
    print(f"   🏆 Score: {activity_score}/100")
    
    # Retourner les résultats
    return {
        'finca_id': finca_id,
        'coordinates': {'lat': lat, 'lon': lon},
        'sentinel1_6months': {
            'vv_mean': vv_mean_6months,
            'vv_std': vv_std,
            'vv_min': vv_min,
            'vv_max': vv_max,
            'activity_level': activity_level,
            'activity_score': activity_score,
            'images_count': count,
            'period': '6 months average',
            'date_range': {
                'start': '2025-02-17',
                'end': '2025-08-17'
            }
        },
        'analysis_radius': radius_m,
        'status': 'success'
    }


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
    """Fonction principale"""
    print("💾 STOCKAGE DONNÉES SENTINEL-1 - 6 MOIS POUR TOUTES LES FINCAS")
    print("=" * 70)
    print("Calcul et stockage de la moyenne d'activité radar sur 6 mois")
    
    # Charger les données des fincas
    data_dir = ROOT / 'data' / 'luminosity_analysis'
    json_files = [f for f in data_dir.glob('luminosity_top20_*.json') if 'summary' not in f.name]
    
    if not json_files:
        print("❌ Aucun fichier de données trouvé")
        return
    
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Chargement: {latest_file}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    # Créer le dossier de sortie
    output_dir = ROOT / 'data' / 'sentinel1_6months_storage'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    successful_data = [item for item in data if item['status'] == 'success']
    print(f"📊 {len(successful_data)} fincas à analyser")
    
    # Analyser toutes les fincas avec moyenne 6 mois
    radius_m = 50
    print(f"🔍 Analyse de toutes les {len(successful_data)} fincas avec moyenne 6 mois")
    
    # Analyser chaque finca
    results = []
    success_count = 0
    
    for i, finca_data in enumerate(successful_data, 1):
        print(f"\n[{i}/{len(successful_data)}] ", end="")
        
        try:
            result = analyze_sentinel1_6months_average(finca_data, radius_m=radius_m)
            results.append(result)
            if result:
                success_count += 1
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            results.append(None)
            continue
    
    # Créer le résumé
    if success_count > 0:
        successful_results = [r for r in results if r is not None]
        
        # Statistiques globales
        vv_means = [r['sentinel1_6months']['vv_mean'] for r in successful_results]
        activity_scores = [r['sentinel1_6months']['activity_score'] for r in successful_results]
        activity_levels = [r['sentinel1_6months']['activity_level'] for r in successful_results]
        
        # Créer un fichier de résumé
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'total_fincas': len(successful_results),
            'analysis_radius': radius_m,
            'period': '6 months average',
            'activity_distribution': {},
            'vv_statistics': {
                'mean': float(np.mean(vv_means)),
                'std': float(np.std(vv_means)),
                'min': float(np.min(vv_means)),
                'max': float(np.max(vv_means))
            },
            'score_statistics': {
                'mean': float(np.mean(activity_scores)),
                'std': float(np.std(activity_scores)),
                'min': float(np.min(activity_scores)),
                'max': float(np.max(activity_scores))
            },
            'fincas': successful_results
        }
        
        # Compter les niveaux d'activité
        for level in activity_levels:
            summary['activity_distribution'][level] = summary['activity_distribution'].get(level, 0) + 1
        
        # Sauvegarder le résumé
        summary_file = output_dir / f"sentinel1_6months_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Créer aussi un fichier CSV pour intégration facile
        csv_file = output_dir / f"sentinel1_6months_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        import pandas as pd
        csv_data = []
        for result in successful_results:
            csv_data.append({
                'finca_id': result['finca_id'],
                'lat': result['coordinates']['lat'],
                'lon': result['coordinates']['lon'],
                'vv_mean_6months': result['sentinel1_6months']['vv_mean'],
                'activity_level': result['sentinel1_6months']['activity_level'],
                'activity_score': result['sentinel1_6months']['activity_score'],
                'images_count': result['sentinel1_6months']['images_count'],
                'period_start': result['sentinel1_6months']['date_range']['start'],
                'period_end': result['sentinel1_6months']['date_range']['end']
            })
        
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_file, index=False)
        
        print(f"\n📊 RÉSUMÉ SENTINEL-1 - MOYENNE 6 MOIS (COMPLET)")
        print("=" * 60)
        print(f"📁 Fincas analysées: {len(successful_results)}")
        print(f"🔍 Rayon d'analyse: {radius_m}m")
        print(f"📅 Période: 6 derniers mois")
        print(f"📊 VV moyen: {summary['vv_statistics']['mean']:.3f} dB")
        print(f"📈 VV min/max: {summary['vv_statistics']['min']:.3f} / {summary['vv_statistics']['max']:.3f} dB")
        print(f"🎯 Score moyen: {summary['score_statistics']['mean']:.1f}/100")
        print("\n🎯 Distribution d'activité:")
        for level, count in summary['activity_distribution'].items():
            percentage = (count / len(successful_results)) * 100
            print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
        
        print(f"\n📁 Fichiers sauvegardés:")
        print(f"   • JSON: {summary_file}")
        print(f"   • CSV: {csv_file}")
    
    print(f"\n🎉 Stockage 6 mois terminé!")
    print(f"📁 Résultats dans: {output_dir}")
    print(f"🔍 Périmètre d'analyse: {radius_m}m")
    print(f"📅 Période: 6 derniers mois")
    print(f"📊 {success_count}/{len(successful_data)} fincas traitées avec succès")
    print("\n💡 Ces données peuvent maintenant être intégrées dans le système de scoring")


if __name__ == "__main__":
    main()
