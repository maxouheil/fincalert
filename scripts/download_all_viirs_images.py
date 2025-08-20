#!/usr/bin/env python3
"""
🌙 Téléchargement de Toutes les Images VIIRS DNB
Télécharge les vraies images satellites nocturnes pour toutes les fincas
"""

import os
import sys
import json
import ee
import folium
import requests
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


def download_finca_image(finca_data, output_dir):
    """Télécharge l'image VIIRS pour une finca"""
    finca_id = finca_data['finca_id']
    lat = finca_data['coordinates']['lat']
    lon = finca_data['coordinates']['lon']
    
    print(f"📍 {finca_id} - {lat:.6f}, {lon:.6f}")
    
    # Créer la région d'intérêt
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(500)
    
    # Collection VIIRS DNB
    viirs = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    
    # Date de fin (maintenant)
    end_date = ee.Date(datetime.now())
    # Date de début (12 mois en arrière)
    start_date = end_date.advance(-12, 'month')
    
    # Récupérer les images
    filtered_viirs = viirs.filterDate(start_date, end_date)
    
    # Vérifier si on a des images
    count = filtered_viirs.size().getInfo()
    print(f"   📊 {count} images VIIRS disponibles")
    
    if count == 0:
        print(f"   ❌ Aucune image disponible")
        return False
    
    # Prendre la plus récente
    latest_image = filtered_viirs.sort('system:time_start', False).first()
    
    # Informations sur l'image
    image_date = latest_image.date().format('YYYY-MM-dd').getInfo()
    print(f"   📅 Image du: {image_date}")
    
    # Sélectionner la bande de luminosité
    luminosity_band = latest_image.select('avg_rad')
    
    # Paramètres de visualisation
    vis_params = {
        'min': 0,
        'max': 10,
        'palette': ['000000', 'FFFFFF']
    }
    
    # URL de l'image
    url = luminosity_band.getThumbURL({
        'region': roi,
        'dimensions': '512x512',
        'format': 'png',
        **vis_params
    })
    
    # Télécharger l'image
    response = requests.get(url)
    if response.status_code == 200:
        # Sauvegarder l'image PNG
        png_file = output_dir / f"{finca_id}_viirs_night.png"
        with open(png_file, 'wb') as f:
            f.write(response.content)
        print(f"   ✅ Image téléchargée: {png_file.name}")
        
        # Calculer les statistiques
        stats = latest_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=750,
            maxPixels=1e6
        ).getInfo()
        
        if 'avg_rad' in stats:
            luminosity = stats['avg_rad']
            print(f"   💡 Luminosité: {luminosity:.3f}")
        
        # Créer une carte interactive
        m = folium.Map(
            location=[lat, lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )
        
        # Ajouter un marqueur
        folium.Marker(
            [lat, lon],
            popup=f"<b>{finca_id}</b><br>Luminosité nocturne<br>Date: {image_date}<br>Luminosité: {luminosity:.3f}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        
        map_file = output_dir / f"{finca_id}_map.html"
        m.save(str(map_file))
        print(f"   🗺️  Carte créée: {map_file.name}")
        
        return True
    else:
        print(f"   ❌ Erreur téléchargement: {response.status_code}")
        return False


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
    success_count = 0
    for i, finca_data in enumerate(successful_data, 1):
        print(f"\n[{i}/{len(successful_data)}] ", end="")
        
        try:
            if download_finca_image(finca_data, output_dir):
                success_count += 1
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            continue
    
    print(f"\n🎉 Traitement terminé!")
    print(f"✅ {success_count}/{len(successful_data)} images téléchargées")
    print(f"📁 Images dans: {output_dir}")
    print("\n🌐 Ouvrez les fichiers .html dans votre navigateur pour voir les cartes")


if __name__ == "__main__":
    main()
