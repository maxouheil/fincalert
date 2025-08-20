#!/usr/bin/env python3
"""
🌙 Test d'analyse de luminosité nocturne
Teste le module NocturnalLuminosityAnalyzer sur quelques fincas d'exemple
"""

import os
import sys
import json
import time
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.satellite.nocturnal_luminosity import NocturnalLuminosityAnalyzer


def test_single_finca():
    """Test sur une seule finca"""
    print("🌙 Test d'analyse de luminosité - Finca unique")
    print("=" * 60)
    
    analyzer = NocturnalLuminosityAnalyzer()
    
    # Coordonnées d'une finca d'Ibiza (exemple)
    test_fincas = [
        {
            'id': 'test_finca_001',
            'lat': 38.9231,
            'lon': 1.3132,
            'description': 'Finca ouest Ibiza'
        },
        {
            'id': 'test_finca_002', 
            'lat': 38.9609,
            'lon': 1.2217,
            'description': 'Cala Comte'
        },
        {
            'id': 'test_finca_003',
            'lat': 38.9620,
            'lon': 1.2460,
            'description': 'Cala Bassa'
        }
    ]
    
    for finca in test_fincas:
        print(f"\n📍 Test: {finca['description']}")
        print(f"   Coordonnées: {finca['lat']}, {finca['lon']}")
        
        start_time = time.time()
        
        try:
            result = analyzer.analyze_finca_luminosity(
                finca['id'], 
                finca['lat'], 
                finca['lon'], 
                months=6,  # Test sur 6 mois pour aller plus vite
                demo=True  # Mode démo pour les tests
            )
            
            elapsed = time.time() - start_time
            
            print(f"   ⏱️  Temps: {elapsed:.1f}s")
            print(f"   📊 Status: {result['status']}")
            
            if result['status'] == 'success':
                print(f"   🌟 Score: {result['score']}/5")
                print(f"   💡 Raison: {result['reason']}")
                print(f"   📅 Données: {len(result['monthly_data'])} mois")
                
                metrics = result['metrics']
                print(f"   📈 Métriques:")
                print(f"      - Luminosité moyenne: {metrics['mean_luminosity']:.3f}")
                print(f"      - Écart-type: {metrics['std_luminosity']:.3f}")
                print(f"      - Tendance: {metrics['trend']:.3f}")
                print(f"      - Mois actifs: {metrics['active_months']}/{metrics['total_months']}")
                print(f"      - Niveau: {metrics['luminosity_level']}")
                print(f"      - Pattern saisonnier: {metrics['seasonal_pattern']}")
                
                # Afficher quelques données mensuelles
                if result['monthly_data']:
                    print(f"   📅 Données mensuelles (échantillon):")
                    for i, month_data in enumerate(result['monthly_data'][:3]):
                        print(f"      {month_data['month']}: {month_data['luminosity']:.3f} "
                              f"({'✅' if month_data['active'] else '❌'})")
                    if len(result['monthly_data']) > 3:
                        print(f"      ... et {len(result['monthly_data']) - 3} autres mois")
                
            else:
                print(f"   ❌ Erreur: {result['error_message']}")
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ⏱️  Temps: {elapsed:.1f}s")
            print(f"   💥 Exception: {str(e)}")
        
        print("-" * 40)


def test_batch_fincas():
    """Test sur un petit batch de fincas"""
    print("\n🌙 Test d'analyse de luminosité - Batch de fincas")
    print("=" * 60)
    
    # Charger quelques fincas depuis le GeoJSON
    geojson_path = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    
    if not geojson_path.exists():
        print(f"❌ Fichier GeoJSON non trouvé: {geojson_path}")
        return
    
    with open(geojson_path, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"📊 Total fincas disponibles: {len(features)}")
    
    # Prendre les 5 premières fincas pour le test
    test_features = features[:5]
    print(f"🧪 Test sur {len(test_features)} fincas")
    
    analyzer = NocturnalLuminosityAnalyzer()
    results = []
    
    start_time = time.time()
    
    for i, feature in enumerate(test_features, 1):
        props = feature.get('properties', {})
        finca_id = props.get('id')
        lat = props.get('lat')
        lon = props.get('lon')
        
        if not all([finca_id, lat, lon]):
            continue
        
        print(f"\n📍 [{i}/{len(test_features)}] {finca_id}")
        print(f"   Coordonnées: {lat}, {lon}")
        
        try:
            result = analyzer.analyze_finca_luminosity(
                finca_id, lat, lon, months=6, demo=True
            )
            
            results.append(result)
            
            if result['status'] == 'success':
                print(f"   ✅ Score: {result['score']}/5 - {result['reason'][:50]}...")
            else:
                print(f"   ❌ Erreur: {result['error_message']}")
                
        except Exception as e:
            print(f"   💥 Exception: {str(e)}")
            results.append({
                'finca_id': finca_id,
                'status': 'error',
                'error_message': str(e)
            })
    
    total_time = time.time() - start_time
    
    # Statistiques
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    print(f"\n📊 RÉSULTATS DU BATCH:")
    print(f"   ✅ Succès: {successful}/{len(results)}")
    print(f"   ❌ Échecs: {failed}/{len(results)}")
    print(f"   ⏱️  Temps total: {total_time:.1f}s")
    print(f"   ⚡ Temps moyen: {total_time/len(results):.1f}s par finca")
    
    if successful > 0:
        scores = [r['score'] for r in results if r['status'] == 'success']
        print(f"   📈 Scores moyens: {sum(scores)/len(scores):.1f}/5")
        print(f"   📊 Distribution scores:")
        for score in range(6):
            count = sum(1 for s in scores if s == score)
            if count > 0:
                print(f"      {score}/5: {count} fincas")


def test_gee_connection():
    """Test de la connexion Google Earth Engine"""
    print("🌙 Test de connexion Google Earth Engine")
    print("=" * 60)
    
    analyzer = NocturnalLuminosityAnalyzer()
    
    if analyzer._ensure_gee_initialized():
        print("✅ Google Earth Engine connecté avec succès")
        
        # Test simple d'accès aux données VIIRS
        try:
            import ee
            collection = ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")
            size = collection.size().getInfo()
            print(f"✅ Collection VIIRS accessible ({size} images disponibles)")
        except Exception as e:
            print(f"❌ Erreur accès collection VIIRS: {e}")
    else:
        print("❌ Google Earth Engine non disponible")
        print("💡 Pour installer:")
        print("   pip install earthengine-api")
        print("   earthengine authenticate")


def main():
    """Fonction principale de test"""
    print("🌙 TESTS D'ANALYSE DE LUMINOSITÉ NOCTURNE")
    print("=" * 60)
    
    # Test 1: Connexion GEE
    test_gee_connection()
    
    # Test 2: Finca unique
    test_single_finca()
    
    # Test 3: Batch de fincas
    test_batch_fincas()
    
    print("\n🎉 Tests terminés!")


if __name__ == "__main__":
    main()
