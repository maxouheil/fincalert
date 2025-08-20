#!/usr/bin/env python3
"""
🔐 Setup Google Earth Engine Authentication
Configure l'authentification pour accéder aux données VIIRS DNB
"""

import os
import sys
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def setup_gee_auth():
    """Configure l'authentification Google Earth Engine"""
    print("🔐 Configuration Google Earth Engine")
    print("=" * 50)
    
    try:
        import ee
        
        # Vérifier si déjà authentifié
        try:
            ee.Initialize()
            print("✅ Google Earth Engine déjà initialisé")
            
            # Test simple
            test_point = ee.Geometry.Point([0, 0])
            test_point.getInfo()
            print("✅ Authentification valide")
            return True
            
        except Exception as e:
            print(f"⚠️ Authentification requise: {e}")
            
            # Authentification interactive
            print("\n🌐 Authentification Google Earth Engine...")
            print("📝 Suivez les instructions dans votre navigateur")
            
            ee.Authenticate()
            ee.Initialize()
            
            print("✅ Authentification réussie!")
            return True
            
    except ImportError:
        print("❌ Google Earth Engine non installé")
        print("💡 Installez avec: pip install earthengine-api")
        return False
    except Exception as e:
        print(f"❌ Erreur d'authentification: {e}")
        return False


def test_viirs_access():
    """Test l'accès aux données VIIRS DNB"""
    print("\n🌙 Test d'accès aux données VIIRS DNB")
    print("=" * 50)
    
    try:
        import ee
        
        # Test de la collection VIIRS
        collection = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
        size = collection.size().getInfo()
        
        print(f"✅ Collection VIIRS accessible")
        print(f"📊 Images disponibles: {size}")
        
        # Test d'une image récente
        recent_image = collection.first()
        date = recent_image.date().format('YYYY-MM-dd').getInfo()
        print(f"📅 Image la plus récente: {date}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur accès VIIRS: {e}")
        return False


def main():
    """Fonction principale"""
    print("🚀 SETUP GOOGLE EARTH ENGINE")
    print("=" * 50)
    
    # Setup authentification
    auth_ok = setup_gee_auth()
    
    if auth_ok:
        # Test accès données
        viirs_ok = test_viirs_access()
        
        if viirs_ok:
            print("\n🎉 Configuration terminée avec succès!")
            print("✅ Prêt pour l'analyse de luminosité nocturne")
        else:
            print("\n⚠️ Problème d'accès aux données VIIRS")
    else:
        print("\n❌ Échec de la configuration")


if __name__ == "__main__":
    main()
