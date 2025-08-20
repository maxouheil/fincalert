#!/usr/bin/env python3
"""
🌙 Test d'une Image VIIRS DNB Unique
Teste le téléchargement d'une image satellite nocturne pour une finca
"""

import ee
import requests
from datetime import datetime
from pathlib import Path

# Initialize Google Earth Engine
try:
    ee.Initialize(project='fincalert')
    print("✅ Google Earth Engine initialisé")
except Exception as e:
    print(f"❌ Erreur GEE: {e}")
    exit(1)

def test_viirs_image():
    """Test avec une finca spécifique"""
    # Coordonnées de finca_00001
    lat = 38.989294
    lon = 1.289420
    
    print(f"📍 Test avec finca_00001")
    print(f"   Coordonnées: {lat:.6f}, {lon:.6f}")
    
    # Créer la région d'intérêt
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(1000)  # 1km de rayon
    
    # Collection VIIRS DNB
    viirs = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
    
    # Vérifier la collection
    print(f"📊 Collection VIIRS: {viirs.size().getInfo()} images totales")
    
    # Filtrer par date récente
    end_date = ee.Date(datetime.now())
    start_date = end_date.advance(-12, 'month')  # 12 mois en arrière
    
    filtered_viirs = viirs.filterDate(start_date, end_date)
    count = filtered_viirs.size().getInfo()
    print(f"📅 Images des 12 derniers mois: {count}")
    
    if count == 0:
        print("❌ Aucune image disponible")
        return
    
    # Prendre la plus récente
    latest_image = filtered_viirs.sort('system:time_start', False).first()
    
    # Informations sur l'image
    image_date = latest_image.date().format('YYYY-MM-dd').getInfo()
    print(f"📅 Image la plus récente: {image_date}")
    
    # Sélectionner la bande de luminosité (avg_rad)
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
    
    print(f"🌐 URL de l'image: {url}")
    
    # Télécharger l'image
    response = requests.get(url)
    if response.status_code == 200:
        output_file = Path('test_viirs_image.png')
        with open(output_file, 'wb') as f:
            f.write(response.content)
        print(f"✅ Image téléchargée: {output_file}")
        
        # Calculer les statistiques
        stats = latest_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=750,
            maxPixels=1e6
        ).getInfo()
        
        if 'avg_rad' in stats:
            luminosity = stats['avg_rad']
            print(f"💡 Luminosité moyenne: {luminosity:.3f}")
        
    else:
        print(f"❌ Erreur téléchargement: {response.status_code}")

if __name__ == "__main__":
    test_viirs_image()
