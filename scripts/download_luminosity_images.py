#!/usr/bin/env python3
"""
🌙 Téléchargement des Images Satellites Nocturnes VIIRS DNB
Télécharge et affiche les vraies images satellites nocturnes pour chaque finca
"""

import os
import sys
import json
import ee
import folium
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from PIL import Image
import requests
from io import BytesIO

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


def get_viirs_image(lat, lon, date_str, radius_meters=500):
    """
    Récupère une image VIIRS DNB pour une date spécifique
    """
    # Créer la région d'intérêt
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(radius_meters)
    
    # Collection VIIRS DNB
    viirs = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    
    # Filtrer par date
    start_date = ee.Date(date_str)
    end_date = start_date.advance(1, 'month')
    
    # Récupérer l'image
    image = viirs.filterDate(start_date, end_date).first()
    
    if image is None:
        return None
    
    return image, roi


def download_image_as_png(image, roi, output_path, width=512, height=512):
    """
    Télécharge une image GEE en PNG
    """
    # Sélectionner la bande de luminosité
    luminosity_band = image.select('avg_rad')
    
    # Paramètres de visualisation pour VIIRS DNB
    vis_params = {
        'min': 0,
        'max': 10,
        'palette': ['000000', 'FFFFFF']  # Noir à blanc
    }
    
    # URL de l'image
    url = luminosity_band.getThumbURL({
        'region': roi,
        'dimensions': f'{width}x{height}',
        'format': 'png',
        **vis_params
    })
    
    # Télécharger l'image
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    else:
        print(f"❌ Erreur téléchargement: {response.status_code}")
        return False


def create_luminosity_map(finca_data, output_dir):
    """
    Crée une carte interactive avec l'image de luminosité
    """
    finca_id = finca_data['finca_id']
    lat = finca_data['coordinates']['lat']
    lon = finca_data['coordinates']['lon']
    
    # Créer la carte centrée sur la finca
    m = folium.Map(
        location=[lat, lon],
        zoom_start=15,
        tiles='OpenStreetMap'
    )
    
    # Ajouter un marqueur pour la finca
    folium.Marker(
        [lat, lon],
        popup=f"<b>{finca_id}</b><br>Luminosité nocturne",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)
    
    # Sauvegarder la carte
    map_file = output_dir / f"{finca_id}_map.html"
    m.save(str(map_file))
    
    return map_file


def get_latest_viirs_data(lat, lon, months_back=12):
    """
    Récupère les données VIIRS les plus récentes disponibles
    """
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(500)
    
    # Collection VIIRS DNB
    viirs = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    
    # Date de fin (maintenant)
    end_date = ee.Date(datetime.now())
    # Date de début (12 mois en arrière)
    start_date = end_date.advance(-months_back, 'month')
    
    # Récupérer les images
    filtered_viirs = viirs.filterDate(start_date, end_date)
    
    # Vérifier si on a des images
    count = filtered_viirs.size().getInfo()
    print(f"   📊 {count} images VIIRS disponibles")
    
    if count == 0:
        return None, None
    
    # Prendre la plus récente
    latest_image = filtered_viirs.sort('system:time_start', False).first()
    
    return latest_image, roi


def main():
    """Fonction principale"""
    print("🌙 TÉLÉCHARGEMENT DES IMAGES SATELLITES NOCTURNES")
    print("=" * 60)
    
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
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'satellite_images'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    successful_data = [item for item in data if item['status'] == 'success']
    print(f"📊 {len(successful_data)} fincas à traiter")
    
    # Traiter chaque finca
    for i, finca_data in enumerate(successful_data, 1):
        finca_id = finca_data['finca_id']
        lat = finca_data['coordinates']['lat']
        lon = finca_data['coordinates']['lon']
        
        print(f"\n📍 [{i}/{len(successful_data)}] {finca_id}")
        print(f"   Coordonnées: {lat:.6f}, {lon:.6f}")
        
        try:
            # Récupérer l'image VIIRS la plus récente
            image, roi = get_latest_viirs_data(lat, lon, months_back=3)
            
            if image is None:
                print(f"   ❌ Aucune image VIIRS disponible")
                continue
            
            # Informations sur l'image
            image_date = image.date().format('YYYY-MM-dd').getInfo()
            print(f"   📅 Image du: {image_date}")
            
            # Télécharger l'image PNG
            png_file = output_dir / f"{finca_id}_viirs_night.png"
            if download_image_as_png(image, roi, png_file):
                print(f"   ✅ Image téléchargée: {png_file.name}")
            else:
                print(f"   ❌ Échec téléchargement")
                continue
            
            # Créer une carte interactive
            map_file = create_luminosity_map(finca_data, output_dir)
            print(f"   🗺️  Carte créée: {map_file.name}")
            
            # Calculer les statistiques de luminosité
            stats = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=roi,
                scale=750,  # Résolution VIIRS
                maxPixels=1e6
            ).getInfo()
            
            if 'avg_rad' in stats:
                luminosity = stats['avg_rad']
                print(f"   💡 Luminosité moyenne: {luminosity:.3f}")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            continue
    
    print(f"\n🎉 Images satellites créées dans: {output_dir}")
    print("📁 Chaque finca a:")
    print("   - Une image PNG de la luminosité nocturne")
    print("   - Une carte HTML interactive")
    print("\n🌐 Ouvrez les fichiers .html dans votre navigateur pour voir les cartes")


if __name__ == "__main__":
    main()
