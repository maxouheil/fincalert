#!/usr/bin/env python3
"""
🛰️ Analyse Ultra-Précise des Fincas avec Sentinel-1 SAR
Analyse avec des périmètres ultra-réduits pour précision maximale
"""

import os
import sys
import json
import ee
import folium
import requests
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


def get_sentinel1_collection(lat, lon, radius_m=50, months_back=6):
    """Récupère la collection Sentinel-1 pour une finca avec périmètre ultra-réduit"""
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(radius_m)
    
    # Collection Sentinel-1
    s1 = ee.ImageCollection("COPERNICUS/S1_GRD")
    
    # Date de fin (maintenant)
    end_date = ee.Date(datetime.now())
    # Date de début (6 mois en arrière)
    start_date = end_date.advance(-months_back, 'month')
    
    # Filtrer par région, date et paramètres
    filtered_s1 = s1.filterBounds(roi)\
                    .filterDate(start_date, end_date)\
                    .filter(ee.Filter.eq('instrumentMode', 'IW'))\
                    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    
    return filtered_s1, roi


def analyze_sentinel1_ultra_precise(finca_data, output_dir, radius_m=50):
    """Analyse ultra-précise d'une finca avec Sentinel-1"""
    finca_id = finca_data['finca_id']
    lat = finca_data['coordinates']['lat']
    lon = finca_data['coordinates']['lon']
    
    print(f"📍 {finca_id} - {lat:.6f}, {lon:.6f}")
    print(f"   🔍 Rayon: {radius_m}m (zone ultra-précise)")
    
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
        png_file = output_dir / f"{finca_id}_sentinel1_ultra_{radius_m}m.png"
        with open(png_file, 'wb') as f:
            f.write(response.content)
        print(f"   ✅ Image téléchargée: {png_file.name}")
    
    # Créer une carte interactive ultra-précise
    m = folium.Map(
        location=[lat, lon],
        zoom_start=19,  # Zoom ultra-proche
        tiles='OpenStreetMap'
    )
    
    # Ajouter un cercle pour la zone analysée
    folium.Circle(
        location=[lat, lon],
        radius=radius_m,
        popup=f"Zone d'analyse {radius_m}m",
        color='purple',
        fill=True,
        fillColor='purple',
        fillOpacity=0.4,
        weight=4
    ).add_to(m)
    
    # Ajouter un marqueur central
    folium.Marker(
        [lat, lon],
        popup=f"""
        <b>{finca_id}</b><br>
        Sentinel-1 SAR (Ultra-Précis)<br>
        Date: {latest_date}<br>
        Activité: {overall_activity}<br>
        VV: {vv_mean:.3f} dB<br>
        Rayon: {radius_m}m<br>
        Résolution: 10m
        """,
        icon=folium.Icon(color='purple', icon='info-sign')
    ).add_to(m)
    
    map_file = output_dir / f"{finca_id}_sentinel1_ultra_{radius_m}m_map.html"
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


def create_ultra_precise_summary(all_results, output_dir, radius_m):
    """Crée un résumé de l'analyse ultra-précise"""
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
        'analysis_radius': radius_m,
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
    summary_file = output_dir / f"sentinel1_ultra_{radius_m}m_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📊 RÉSUMÉ SENTINEL-1 ULTRA-PRÉCIS ({radius_m}m)")
    print("=" * 60)
    print(f"📁 Fincas analysées: {len(successful_results)}")
    print(f"🔍 Rayon d'analyse: {radius_m}m")
    print(f"📊 VV moyen: {summary['vv_statistics']['mean']:.3f} dB")
    print(f"📈 VV min/max: {summary['vv_statistics']['min']:.3f} / {summary['vv_statistics']['max']:.3f} dB")
    print("\n🎯 Distribution d'activité:")
    for level, count in summary['activity_distribution'].items():
        percentage = (count / len(successful_results)) * 100
        print(f"   • {level}: {count} fincas ({percentage:.1f}%)")
    
    return summary_file


def main():
    """Fonction principale"""
    print("🛰️ ANALYSE ULTRA-PRÉCISE DES FINCAS AVEC SENTINEL-1 SAR")
    print("=" * 70)
    print("Résolution: 10m avec périmètres ultra-réduits")
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
    output_dir = ROOT / 'data' / 'sentinel1_ultra_precise_analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    successful_data = [item for item in data if item['status'] == 'success']
    print(f"📊 {len(successful_data)} fincas à analyser")
    
    # Analyser avec rayon optimal de 50m pour toutes les fincas
    radius_m = 50  # Rayon optimal déterminé
    
    print(f"\n🔍 ANALYSE ULTRA-PRÉCISE AVEC RAYON {radius_m}m - TOUTES LES FINCAS")
    print("=" * 70)
    
    # Analyser toutes les 20 fincas avec le rayon optimal
    test_data = successful_data  # Toutes les fincas
    print(f"🔍 Analyse des {len(test_data)} fincas avec rayon {radius_m}m (optimal)")
    
    # Analyser chaque finca
    results = []
    success_count = 0
    
    for i, finca_data in enumerate(test_data, 1):
        print(f"\n[{i}/{len(test_data)}] ", end="")
        
        try:
            result = analyze_sentinel1_ultra_precise(finca_data, output_dir, radius_m=radius_m)
            results.append(result)
            if result:
                success_count += 1
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            results.append(None)
            continue
    
    # Créer le résumé pour ce rayon
    if success_count > 0:
        summary_file = create_ultra_precise_summary(results, output_dir, radius_m)
        print(f"\n📁 Résumé sauvegardé: {summary_file}")
    
    print(f"\n✅ {success_count}/{len(test_data)} fincas analysées avec rayon {radius_m}m")
    
    print(f"\n🎉 Analyse ultra-précise terminée!")
    print(f"📁 Résultats dans: {output_dir}")
    print(f"🔍 Périmètre optimal: {radius_m}m (toutes les fincas)")
    print("\n📋 Chaque finca a:")
    print("   • Image Sentinel-1 ultra-précise (1024x1024)")
    print("   • Carte HTML interactive (zoom 19)")
    print("   • Statistiques d'activité détaillées")
    print("\n🌐 Ouvrez les fichiers .html dans votre navigateur")
    print("\n💡 Cette analyse à 50m est optimale pour détecter l'activité spécifique de chaque finca")


if __name__ == "__main__":
    main()
