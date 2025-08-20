#!/usr/bin/env python3
"""
🛰️ Analyse des Fincas avec Sentinel-1 SAR
Utilise Sentinel-1 pour détecter l'activité humaine avec une résolution de 10m
"""

import os
import sys
import json
import ee
import folium
import requests
import numpy as np
from datetime import datetime, timedelta
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


def get_sentinel1_collection(lat, lon, radius_m=500, months_back=6):
    """Récupère la collection Sentinel-1 pour une finca"""
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(radius_m)
    
    # Collection Sentinel-1
    s1 = ee.ImageCollection("COPERNICUS/S1_GRD")
    
    # Filtrer par région et date
    end_date = ee.Date(datetime.now())
    start_date = end_date.advance(-months_back, 'month')
    
    # Filtrer par région, date et paramètres
    filtered_s1 = s1.filterBounds(roi)\
                    .filterDate(start_date, end_date)\
                    .filter(ee.Filter.eq('instrumentMode', 'IW'))\
                    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    
    return filtered_s1, roi


def analyze_sentinel1_activity(finca_data, output_dir, radius_m=500):
    """Analyse l'activité d'une finca avec Sentinel-1"""
    finca_id = finca_data['finca_id']
    lat = finca_data['coordinates']['lat']
    lon = finca_data['coordinates']['lon']
    
    print(f"📍 {finca_id} - {lat:.6f}, {lon:.6f}")
    print(f"   🔍 Rayon: {radius_m}m")
    
    # Récupérer la collection Sentinel-1
    s1_collection, roi = get_sentinel1_collection(lat, lon, radius_m)
    
    # Compter les images
    count = s1_collection.size().getInfo()
    print(f"   📊 {count} images Sentinel-1 disponibles")
    
    if count == 0:
        print(f"   ❌ Aucune image disponible")
        return None
    
    # Prendre l'image la plus récente pour analyse
    latest_image = s1_collection.sort('system:time_start', False).first()
    latest_info = latest_image.getInfo()
    latest_date = datetime.fromtimestamp(latest_info['properties']['system:time_start']/1000).strftime('%Y-%m-%d')
    
    # Calculer la moyenne de backscatter VV
    stats = latest_image.select('VV').reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=10,  # Résolution Sentinel-1
        maxPixels=1e6
    ).getInfo()
    
    vv_mean = stats.get('VV', 0)
    activity_level = classify_activity_level(vv_mean)
    
    print(f"   📅 {latest_date}: VV={vv_mean:.3f} ({activity_level})")
    
    # Créer les statistiques
    activity_stats = [{
        'date': latest_date,
        'vv_mean': vv_mean,
        'activity_level': activity_level
    }]
    
    overall_activity = activity_level
    
    # Paramètres de visualisation pour Sentinel-1
    vis_params = {
        'bands': ['VV'],
        'min': -25,
        'max': 5,
        'gamma': 1.2
    }
    
    # Télécharger l'image
    url = latest_image.getThumbURL({
        'region': roi,
        'dimensions': '1024x1024',
        'format': 'png',
        **vis_params
    })
    
    response = requests.get(url)
    if response.status_code == 200:
        png_file = output_dir / f"{finca_id}_sentinel1.png"
        with open(png_file, 'wb') as f:
            f.write(response.content)
        print(f"   ✅ Image téléchargée: {png_file.name}")
    
    # Créer une carte interactive
    m = folium.Map(
        location=[lat, lon],
        zoom_start=16,
        tiles='OpenStreetMap'
    )
    
    # Ajouter un cercle pour la zone analysée
    folium.Circle(
        location=[lat, lon],
        radius=radius_m,
        popup=f"Zone d'analyse {radius_m}m",
        color='blue',
        fill=True,
        fillColor='blue',
        fillOpacity=0.2,
        weight=2
    ).add_to(m)
    
    # Ajouter un marqueur
    folium.Marker(
        [lat, lon],
        popup=f"""
        <b>{finca_id}</b><br>
        Sentinel-1 SAR Analysis<br>
        Date: {latest_date}<br>
        Activité: {overall_activity}<br>
        VV: {vv_mean:.3f} dB<br>
        Images analysées: {len(activity_stats)}
        """,
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    map_file = output_dir / f"{finca_id}_sentinel1_map.html"
    m.save(str(map_file))
    print(f"   🗺️  Carte créée: {map_file.name}")
    
    # Retourner les résultats
    return {
        'finca_id': finca_id,
        'coordinates': {'lat': lat, 'lon': lon},
        'sentinel1_stats': activity_stats,
        'avg_vv': vv_mean,
        'overall_activity': overall_activity,
        'images_analyzed': len(activity_stats),
        'latest_date': latest_date,
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


def create_activity_summary(all_results, output_dir):
    """Crée un résumé de l'analyse Sentinel-1"""
    successful_results = [r for r in all_results if r is not None]
    
    if not successful_results:
        print("❌ Aucun résultat à résumer")
        return
    
    # Statistiques globales
    activity_levels = [r['overall_activity'] for r in successful_results]
    vv_values = [r['avg_vv'] for r in successful_results]
    
    # Créer un fichier de résumé
    summary = {
        'analysis_date': datetime.now().isoformat(),
        'total_fincas': len(successful_results),
        'activity_distribution': {},
        'vv_statistics': {
            'mean': np.mean(vv_values),
            'std': np.std(vv_values),
            'min': np.min(vv_values),
            'max': np.max(vv_values)
        },
        'fincas': successful_results
    }
    
    # Compter les niveaux d'activité
    for level in activity_levels:
        summary['activity_distribution'][level] = summary['activity_distribution'].get(level, 0) + 1
    
    # Sauvegarder le résumé
    summary_file = output_dir / f"sentinel1_analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📊 RÉSUMÉ SENTINEL-1")
    print("=" * 40)
    print(f"📁 Fincas analysées: {len(successful_results)}")
    print(f"📊 VV moyen: {summary['vv_statistics']['mean']:.3f} dB")
    print(f"📈 VV min/max: {summary['vv_statistics']['min']:.3f} / {summary['vv_statistics']['max']:.3f} dB")
    print("\n🎯 Distribution d'activité:")
    for level, count in summary['activity_distribution'].items():
        percentage = (count / len(successful_results)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    return summary_file


def main():
    """Fonction principale"""
    print("🛰️ ANALYSE DES FINCAS AVEC SENTINEL-1 SAR")
    print("=" * 60)
    print("Résolution: 10m (vs 750m pour VIIRS)")
    print("Détection: Activité humaine via backscatter radar")
    
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
    output_dir = ROOT / 'data' / 'sentinel1_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    successful_data = [item for item in data if item['status'] == 'success']
    print(f"📊 {len(successful_data)} fincas à analyser")
    
    # Analyser toutes les 20 fincas
    test_data = successful_data[:20]
    print(f"📊 Analyse des {len(test_data)} premières fincas")
    
    # Analyser chaque finca
    results = []
    success_count = 0
    
    for i, finca_data in enumerate(test_data, 1):
        print(f"\n[{i}/{len(test_data)}] ", end="")
        
        try:
            result = analyze_sentinel1_activity(finca_data, output_dir, radius_m=500)
            results.append(result)
            if result:
                success_count += 1
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            results.append(None)
            continue
    
    # Créer le résumé
    if success_count > 0:
        summary_file = create_activity_summary(results, output_dir)
        print(f"\n📁 Résumé sauvegardé: {summary_file}")
    
    print(f"\n🎉 Analyse terminée!")
    print(f"✅ {success_count}/{len(test_data)} fincas analysées")
    print(f"📁 Résultats dans: {output_dir}")
    print("\n📋 Chaque finca a:")
    print("   • Image Sentinel-1 (1024x1024)")
    print("   • Carte HTML interactive")
    print("   • Statistiques d'activité")
    print("\n🌐 Ouvrez les fichiers .html dans votre navigateur")


if __name__ == "__main__":
    main()
