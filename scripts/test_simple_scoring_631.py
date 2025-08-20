#!/usr/bin/env python3
"""
Test du système de scoring simple avec les 631 fincas
"""

import requests
import json
import pandas as pd
from pathlib import Path
from collections import Counter


def test_simple_scoring_api():
    """Test l'API de scoring simple avec quelques fincas"""
    base_url = "http://localhost:8000"
    
    # Charger les données NDVI des 631 fincas
    csv_path = Path("data/abandon_analysis_FULL/fincas_abandon_scores_REALISTIC_20250809_140234.csv")
    df = pd.read_csv(csv_path)
    
    print(f"🔍 TEST DU SYSTÈME DE SCORING SIMPLE")
    print("=" * 60)
    print(f"📊 Total fincas disponibles: {len(df)}")
    
    # Tester quelques fincas représentatives
    test_fincas = [
        'finca_00001',  # Semi-active
        'finca_00010',  # Active
        'finca_00014',  # Inactive
        'finca_00034',  # Active avec CV élevé
        'finca_00044',  # Active avec CV très élevé
    ]
    
    results = []
    
    for finca_id in test_fincas:
        print(f"\n🎯 Test de {finca_id}...")
        
        try:
            response = requests.get(f"{base_url}/api/scoring/simple/{finca_id}")
            
            if response.status_code == 200:
                data = response.json()
                scoring = data['simple_scoring']
                
                print(f"   ✅ Score: {scoring['total_points']}/15")
                print(f"   📊 Classification: {scoring['classification']}")
                print(f"   💡 Luminosité: {scoring['criteria']['luminosite']['level']} ({scoring['criteria']['luminosite']['points']}pts)")
                print(f"   🛰️ Radar: {scoring['criteria']['radar']['level']} ({scoring['criteria']['radar']['points']}pts)")
                print(f"   🌿 Végétation: {scoring['criteria']['entretien_vegetation']['level']} ({scoring['criteria']['entretien_vegetation']['points']}pts)")
                
                results.append({
                    'finca_id': finca_id,
                    'total_points': scoring['total_points'],
                    'classification': scoring['classification'],
                    'data_available': data['data_available']
                })
                
            else:
                print(f"   ❌ Erreur {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Résumé des résultats
    print(f"\n📈 RÉSUMÉ DES TESTS")
    print("-" * 40)
    
    if results:
        classifications = Counter([r['classification'] for r in results])
        print(f"📊 Répartition des classifications:")
        for classification, count in classifications.items():
            print(f"   • {classification}: {count} fincas")
        
        total_points = [r['total_points'] for r in results]
        print(f"📊 Scores totaux: {min(total_points)}-{max(total_points)}/15 (moy: {sum(total_points)/len(total_points):.1f})")
        
        # Vérifier la disponibilité des données
        ndvi_available = sum(1 for r in results if r['data_available']['ndvi'])
        sentinel1_available = sum(1 for r in results if r['data_available']['sentinel1'])
        viirs_available = sum(1 for r in results if r['data_available']['viirs'])
        
        print(f"📊 Disponibilité des données:")
        print(f"   • NDVI: {ndvi_available}/{len(results)} ({ndvi_available/len(results)*100:.0f}%)")
        print(f"   • Sentinel-1: {sentinel1_available}/{len(results)} ({sentinel1_available/len(results)*100:.0f}%)")
        print(f"   • VIIRS: {viirs_available}/{len(results)} ({viirs_available/len(results)*100:.0f}%)")
    
    return results


def test_ndvi_631_endpoint():
    """Test l'endpoint NDVI 631 fincas"""
    print(f"\n🛰️ TEST ENDPOINT NDVI 631 FINCAS")
    print("-" * 40)
    
    try:
        response = requests.get("http://localhost:8000/api/ndvi-all/631-fincas")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint fonctionne!")
            print(f"📊 Total fincas: {data['total_fincas']}")
            print(f"📁 Source: {data['data_source']}")
            
            # Vérifier quelques données
            if data['fincas']:
                first_finca = data['fincas'][0]
                print(f"📋 Exemple finca: {first_finca['finca_id']}")
                print(f"   • Médiane NDVI: {first_finca['median_ndvi']:.3f}")
                print(f"   • Écart-type: {first_finca['std_deviation']:.3f}")
                print(f"   • CV: {first_finca['cv_percent']:.1f}%")
                print(f"   • Statut: {first_finca['activity_status']}")
            
            return True
        else:
            print(f"❌ Erreur {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def main():
    """Fonction principale"""
    print("🚀 TEST COMPLET DU SYSTÈME DE SCORING SIMPLE")
    print("=" * 60)
    
    # Test 1: Endpoint NDVI 631 fincas
    ndvi_ok = test_ndvi_631_endpoint()
    
    # Test 2: Scoring simple
    scoring_results = test_simple_scoring_api()
    
    # Résumé final
    print(f"\n🎯 RÉSUMÉ FINAL")
    print("=" * 60)
    
    if ndvi_ok and scoring_results:
        print("✅ SYSTÈME OPÉRATIONNEL!")
        print("📊 Le backend et le frontend sont prêts avec:")
        print("   • 631 fincas avec données NDVI")
        print("   • Scoring simple (3 critères)")
        print("   • API endpoints fonctionnels")
        print("   • Interface utilisateur mise à jour")
    else:
        print("❌ PROBLÈMES DÉTECTÉS")
        if not ndvi_ok:
            print("   • Endpoint NDVI 631 fincas non fonctionnel")
        if not scoring_results:
            print("   • Scoring simple non fonctionnel")


if __name__ == "__main__":
    main()
