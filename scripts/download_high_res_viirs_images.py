#!/usr/bin/env python3
"""
🌙 Téléchargement d'Images VIIRS Haute Résolution
Télécharge des images satellites nocturnes avec plus de détails
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


def download_high_res_finca_image(finca_data, output_dir, radius_m=500):
    """Télécharge une image VIIRS haute résolution pour une finca"""
    finca_id = finca_data['finca_id']
    lat = finca_data['coordinates']['lat']
    lon = finca_data['coordinates']['lon']
    
    print(f"📍 {finca_id} - {lat:.6f}, {lon:.6f}")
    print(f"   🔍 Rayon: {radius_m}m")
    
    # Créer une région d'intérêt précise
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(radius_m)  # Rayon en mètres
    
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
    
    # Paramètres de visualisation améliorés
    vis_params = {
        'min': 0,
        'max': 15,  # Ajusté pour mieux voir les variations
        'palette': [
            '000000',  # Noir (très sombre)
            '1a1a1a',  # Gris très foncé
            '333333',  # Gris foncé
            '4d4d4d',  # Gris moyen-foncé
            '666666',  # Gris moyen
            '808080',  # Gris
            '999999',  # Gris clair
            'b3b3b3',  # Gris très clair
            'cccccc',  # Gris presque blanc
            'ffffff'   # Blanc (très lumineux)
        ]
    }
    
    # Télécharger plusieurs résolutions pour maximiser les détails
    resolutions = [
        {'size': '512x512', 'name': 'standard'},
        {'size': '1024x1024', 'name': 'high_res'},
        {'size': '2048x2048', 'name': 'ultra_high_res'}
    ]
    
    success = False
    for res in resolutions:
        try:
            print(f"   📐 Téléchargement {res['size']}...")
            
            # URL de l'image
            url = luminosity_band.getThumbURL({
                'region': roi,
                'dimensions': res['size'],
                'format': 'png',
                **vis_params
            })
            
            # Télécharger l'image
            response = requests.get(url)
            if response.status_code == 200:
                # Sauvegarder l'image PNG
                png_file = output_dir / f"{finca_id}_viirs_{res['name']}.png"
                with open(png_file, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ Image {res['size']} téléchargée: {png_file.name}")
                success = True
            else:
                print(f"   ❌ Erreur {res['size']}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur {res['size']}: {e}")
    
    if success:
        # Calculer les statistiques
        stats = latest_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=750,
            maxPixels=1e6
        ).getInfo()
        
        if 'avg_rad' in stats:
            luminosity = stats['avg_rad']
            print(f"   💡 Luminosité moyenne: {luminosity:.3f}")
        
        # Créer une carte interactive avec zone précise
        m = folium.Map(
            location=[lat, lon],
            zoom_start=16,  # Zoom plus proche
            tiles='OpenStreetMap'
        )
        
        # Ajouter un cercle pour montrer la zone analysée
        folium.Circle(
            location=[lat, lon],
            radius=radius_m,  # Rayon en mètres
            popup=f"Zone d'analyse {radius_m}m",
            color='blue',
            fill=False,
            weight=2
        ).add_to(m)
        
        # Ajouter un marqueur central
        folium.Marker(
            [lat, lon],
            popup=f"""
            <b>{finca_id}</b><br>
            Luminosité nocturne<br>
            Date: {image_date}<br>
            Luminosité: {luminosity:.3f}<br>
            Rayon analysé: {radius_m}m
            """,
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        
        map_file = output_dir / f"{finca_id}_map_extended.html"
        m.save(str(map_file))
        print(f"   🗺️  Carte étendue créée: {map_file.name}")
        
        return True
    
    return False


def main():
    """Fonction principale"""
    print("🌙 TÉLÉCHARGEMENT D'IMAGES VIIRS HAUTE RÉSOLUTION")
    print("=" * 65)
    
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
    output_dir = ROOT / 'data' / 'luminosity_analysis' / 'high_res_images'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    successful_data = [item for item in data if item['status'] == 'success']
    print(f"📊 {len(successful_data)} fincas à traiter")
    print("🔍 Zone précise: 500m de rayon")
    print("📐 Résolutions: 512x512, 1024x1024 et 2048x2048 pixels")
    
    # Traiter les 5 premières fincas pour test
    test_data = successful_data[:5]
    print(f"🧪 Test avec les {len(test_data)} premières fincas")
    
    # Traiter chaque finca
    success_count = 0
    for i, finca_data in enumerate(test_data, 1):
        print(f"\n[{i}/{len(test_data)}] ", end="")
        
        try:
            if download_high_res_finca_image(finca_data, output_dir, radius_m=500):
                success_count += 1
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            continue
    
    print(f"\n🎉 Traitement terminé!")
    print(f"✅ {success_count}/{len(test_data)} fincas traitées")
    print(f"📁 Images dans: {output_dir}")
    print("\n📋 Chaque finca a:")
    print("   • Image 512x512 (standard)")
    print("   • Image 1024x1024 (haute résolution)")
    print("   • Image 2048x2048 (ultra haute résolution)")
    print("   • Carte HTML avec zone précise (500m)")
    print("\n🌐 Ouvrez les fichiers .html dans votre navigateur")


if __name__ == "__main__":
    main()
