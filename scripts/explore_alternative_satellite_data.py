#!/usr/bin/env python3
"""
🌙 Exploration de Données Satellitaires Alternatives
Recherche des sources avec une meilleure résolution que VIIRS DNB
"""

import os
import sys
import ee
import json
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


def explore_viirs_alternatives():
    """Explore les alternatives VIIRS avec meilleure résolution"""
    print("\n🔍 ALTERNATIVES VIIRS")
    print("=" * 40)
    
    # VIIRS DNB alternatives
    alternatives = {
        "VIIRS_DNB_DAILY": {
            "collection": "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG",
            "description": "VIIRS DNB quotidien (meilleure résolution temporelle)",
            "resolution": "750m",
            "availability": "Quotidien"
        },
        "VIIRS_DNB_RAW": {
            "collection": "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG",
            "description": "VIIRS DNB brut (données non filtrées)",
            "resolution": "750m",
            "availability": "Mensuel"
        }
    }
    
    for name, info in alternatives.items():
        print(f"📡 {name}")
        print(f"   📊 Collection: {info['collection']}")
        print(f"   📏 Résolution: {info['resolution']}")
        print(f"   📅 Disponibilité: {info['availability']}")
        print(f"   📝 {info['description']}")
        print()


def explore_landsat_night():
    """Explore les données Landsat nocturnes"""
    print("\n🌃 LANDSAT NOCTURNE")
    print("=" * 40)
    
    # Landsat 8/9 TIRS (Thermal Infrared)
    landsat_collections = {
        "LANDSAT_8_TIRS": {
            "collection": "LANDSAT/LC08/C02/T1_L2",
            "description": "Landsat 8 TIRS - Bande thermique (résolution 100m)",
            "resolution": "100m",
            "availability": "16 jours",
            "bands": ["ST_B10", "ST_B11"]  # Bandes thermiques
        },
        "LANDSAT_9_TIRS": {
            "collection": "LANDSAT/LC09/C02/T1_L2", 
            "description": "Landsat 9 TIRS - Bande thermique (résolution 100m)",
            "resolution": "100m",
            "availability": "16 jours",
            "bands": ["ST_B10", "ST_B11"]
        }
    }
    
    for name, info in landsat_collections.items():
        print(f"📡 {name}")
        print(f"   📊 Collection: {info['collection']}")
        print(f"   📏 Résolution: {info['resolution']}")
        print(f"   📅 Disponibilité: {info['availability']}")
        print(f"   📝 {info['description']}")
        print(f"   🎨 Bandes: {', '.join(info['bands'])}")
        print()


def explore_sentinel_data():
    """Explore les données Sentinel"""
    print("\n🛰️ SENTINEL")
    print("=" * 40)
    
    sentinel_collections = {
        "SENTINEL_2": {
            "collection": "COPERNICUS/S2_SR",
            "description": "Sentinel-2 (résolution 10-20m, mais pas nocturne)",
            "resolution": "10-20m",
            "availability": "5 jours",
            "note": "⚠️ Pas de données nocturnes"
        },
        "SENTINEL_1": {
            "collection": "COPERNICUS/S1_GRD",
            "description": "Sentinel-1 SAR (résolution 10m, jour/nuit)",
            "resolution": "10m",
            "availability": "6-12 jours",
            "note": "✅ Fonctionne jour et nuit"
        }
    }
    
    for name, info in sentinel_collections.items():
        print(f"📡 {name}")
        print(f"   📊 Collection: {info['collection']}")
        print(f"   📏 Résolution: {info['resolution']}")
        print(f"   📅 Disponibilité: {info['availability']}")
        print(f"   📝 {info['description']}")
        print(f"   ⚠️  {info['note']}")
        print()


def explore_high_res_alternatives():
    """Explore les alternatives haute résolution"""
    print("\n🔬 ALTERNATIVES HAUTE RÉSOLUTION")
    print("=" * 50)
    
    high_res_options = {
        "PLANET_SCOPE": {
            "description": "PlanetScope (résolution 3-5m)",
            "resolution": "3-5m",
            "availability": "Quotidien",
            "note": "⚠️ Payant, pas dans GEE"
        },
        "WORLDVIEW": {
            "description": "WorldView (résolution 0.3-1.2m)",
            "resolution": "0.3-1.2m", 
            "availability": "Sur demande",
            "note": "⚠️ Payant, pas dans GEE"
        },
        "SPOT": {
            "description": "SPOT (résolution 1.5-6m)",
            "resolution": "1.5-6m",
            "availability": "Sur demande",
            "note": "⚠️ Payant, pas dans GEE"
        }
    }
    
    for name, info in high_res_options.items():
        print(f"📡 {name}")
        print(f"   📏 Résolution: {info['resolution']}")
        print(f"   📅 Disponibilité: {info['availability']}")
        print(f"   📝 {info['description']}")
        print(f"   ⚠️  {info['note']}")
        print()


def test_sentinel1_availability(lat, lon):
    """Teste la disponibilité des données Sentinel-1"""
    print(f"\n🧪 TEST SENTINEL-1")
    print("=" * 30)
    
    point = ee.Geometry.Point([lon, lat])
    
    # Collection Sentinel-1
    s1 = ee.ImageCollection("COPERNICUS/S1_GRD")
    
    # Filtrer par région et date
    end_date = ee.Date(datetime.now())
    start_date = end_date.advance(-3, 'month')
    
    filtered_s1 = s1.filterBounds(point).filterDate(start_date, end_date)
    
    # Compter les images
    count = filtered_s1.size().getInfo()
    print(f"📊 Images Sentinel-1 disponibles: {count}")
    
    if count > 0:
        # Prendre la plus récente
        latest = filtered_s1.sort('system:time_start', False).first()
        date = latest.date().format('YYYY-MM-dd').getInfo()
        print(f"📅 Image la plus récente: {date}")
        
        # Informations sur l'image
        properties = latest.getInfo()['properties']
        print(f"🎨 Polarisation: {properties.get('transmitterReceiverPolarisation', 'N/A')}")
        print(f"📐 Mode: {properties.get('instrumentMode', 'N/A')}")
        
        return True
    else:
        print("❌ Aucune image Sentinel-1 disponible")
        return False


def test_landsat_availability(lat, lon):
    """Teste la disponibilité des données Landsat"""
    print(f"\n🧪 TEST LANDSAT")
    print("=" * 25)
    
    point = ee.Geometry.Point([lon, lat])
    
    # Collection Landsat 8
    landsat = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    
    # Filtrer par région et date
    end_date = ee.Date(datetime.now())
    start_date = end_date.advance(-3, 'month')
    
    filtered_landsat = landsat.filterBounds(point).filterDate(start_date, end_date)
    
    # Compter les images
    count = filtered_landsat.size().getInfo()
    print(f"📊 Images Landsat disponibles: {count}")
    
    if count > 0:
        # Prendre la plus récente
        latest = filtered_landsat.sort('system:time_start', False).first()
        date = latest.date().format('YYYY-MM-dd').getInfo()
        print(f"📅 Image la plus récente: {date}")
        
        # Informations sur l'image
        properties = latest.getInfo()['properties']
        print(f"☁️ Couverture nuageuse: {properties.get('CLOUD_COVER', 'N/A')}%")
        
        return True
    else:
        print("❌ Aucune image Landsat disponible")
        return False


def main():
    """Fonction principale"""
    print("🌙 EXPLORATION DE DONNÉES SATELLITAIRES ALTERNATIVES")
    print("=" * 70)
    print("Recherche de sources avec une meilleure résolution que VIIRS DNB (~750m)")
    
    # Explorer toutes les alternatives
    explore_viirs_alternatives()
    explore_landsat_night()
    explore_sentinel_data()
    explore_high_res_alternatives()
    
    # Test avec une finca
    print("\n🧪 TESTS DE DISPONIBILITÉ")
    print("=" * 40)
    
    # Coordonnées de test (finca_00001)
    test_lat = 38.989294
    test_lon = 1.289420
    
    print(f"📍 Test avec finca_00001: {test_lat:.6f}, {test_lon:.6f}")
    
    # Tester Sentinel-1
    s1_available = test_sentinel1_availability(test_lat, test_lon)
    
    # Tester Landsat
    landsat_available = test_landsat_availability(test_lat, test_lon)
    
    # Recommandations
    print(f"\n💡 RECOMMANDATIONS")
    print("=" * 30)
    
    if s1_available:
        print("✅ Sentinel-1: Bonne option pour détecter l'activité humaine")
        print("   • Résolution: 10m")
        print("   • Fonctionne jour et nuit")
        print("   • Détecte les changements de surface")
    
    if landsat_available:
        print("✅ Landsat: Bonne option pour l'analyse thermique")
        print("   • Résolution: 100m")
        print("   • Bande thermique (activité humaine)")
        print("   • Données gratuites")
    
    print("\n❌ VIIRS DNB: Résolution trop faible (750m)")
    print("   • Limite: ~1-2 pixels par finca")
    print("   • Pas assez de détails pour l'analyse individuelle")


if __name__ == "__main__":
    main()
