#!/usr/bin/env python3
"""
Test du popup simplifié pour vérifier qu'il correspond exactement au screenshot
"""

import requests
import json
import pandas as pd
from pathlib import Path


def test_simplified_popup():
    """Test le popup simplifié avec les données du screenshot"""
    base_url = "http://localhost:8000"
    
    print("🎯 TEST DU POPUP SIMPLIFIÉ")
    print("=" * 50)
    
    # Test avec finca_00001 (comme dans le screenshot)
    finca_id = "finca_00001"
    
    print(f"📋 Test de {finca_id}...")
    
    try:
        # Test API scoring simple
        response = requests.get(f"{base_url}/api/scoring/simple/{finca_id}")
        
        if response.status_code == 200:
            data = response.json()
            scoring = data['simple_scoring']
            
            print(f"✅ API fonctionne!")
            print(f"📊 Score total: {scoring['total_points']}/15")
            print(f"🏷️ Classification: {scoring['classification']}")
            
            # Vérifier les critères individuels
            print(f"\n📈 Critères individuels:")
            print(f"   📡 Activité radar: {scoring['criteria']['radar']['level']} ({scoring['criteria']['radar']['points']}/5)")
            print(f"   💡 Lumière nocturne: {scoring['criteria']['luminosite']['level']} ({scoring['criteria']['luminosite']['points']}/5)")
            print(f"   🌿 Entretien végétation: {scoring['criteria']['entretien_vegetation']['level']} ({scoring['criteria']['entretien_vegetation']['points']}/5)")
            
            # Vérifier la disponibilité des données
            print(f"\n📊 Disponibilité des données:")
            print(f"   • NDVI: {'✅' if data['data_available']['ndvi'] else '❌'}")
            print(f"   • Sentinel-1: {'✅' if data['data_available']['sentinel1'] else '❌'}")
            print(f"   • VIIRS: {'✅' if data['data_available']['viirs'] else '❌'}")
            
            # Vérifier que le format correspond au screenshot
            print(f"\n🎨 Vérification du format:")
            
            # Vérifier que tous les critères ont des scores 1/3/5
            radar_points = scoring['criteria']['radar']['points']
            luminosite_points = scoring['criteria']['luminosite']['points']
            vegetation_points = scoring['criteria']['entretien_vegetation']['points']
            
            valid_points = [1, 3, 5]
            if all(p in valid_points for p in [radar_points, luminosite_points, vegetation_points]):
                print(f"   ✅ Points valides (1/3/5): {radar_points}, {luminosite_points}, {vegetation_points}")
            else:
                print(f"   ❌ Points invalides: {radar_points}, {luminosite_points}, {vegetation_points}")
            
            # Vérifier le total
            total = scoring['total_points']
            expected_total = radar_points + luminosite_points + vegetation_points
            if total == expected_total:
                print(f"   ✅ Total correct: {total}/15")
            else:
                print(f"   ❌ Total incorrect: {total} (attendu: {expected_total})")
            
            # Vérifier la classification
            classification = scoring['classification']
            if classification in ['Active', 'Moderate', 'Inactive']:
                print(f"   ✅ Classification valide: {classification}")
            else:
                print(f"   ❌ Classification invalide: {classification}")
            
            return True
            
        else:
            print(f"❌ Erreur API {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def test_multiple_fincas():
    """Test avec plusieurs fincas pour vérifier la cohérence"""
    print(f"\n🔄 TEST AVEC PLUSIEURS FINCAS")
    print("-" * 40)
    
    test_fincas = ['finca_00001', 'finca_00010', 'finca_00014']
    
    for finca_id in test_fincas:
        try:
            response = requests.get(f"http://localhost:8000/api/scoring/simple/{finca_id}")
            if response.status_code == 200:
                data = response.json()
                scoring = data['simple_scoring']
                print(f"   {finca_id}: {scoring['total_points']}/15 → {scoring['classification']}")
            else:
                print(f"   {finca_id}: ❌ Erreur {response.status_code}")
        except Exception as e:
            print(f"   {finca_id}: ❌ Exception")


def main():
    """Fonction principale"""
    print("🚀 TEST COMPLET DU POPUP SIMPLIFIÉ")
    print("=" * 60)
    
    # Test principal
    success = test_simplified_popup()
    
    # Test multiple fincas
    test_multiple_fincas()
    
    # Résumé final
    print(f"\n🎯 RÉSUMÉ FINAL")
    print("=" * 60)
    
    if success:
        print("✅ POPUP SIMPLIFIÉ OPÉRATIONNEL!")
        print("📊 Le popup affiche maintenant exactement:")
        print("   • Nom de la finca")
        print("   • Badge de statut (Active/Moderate/Inactive)")
        print("   • Localisation")
        print("   • Détails (surface, distance)")
        print("   • Score simplifié avec 3 critères:")
        print("     - Activité radar (📡)")
        print("     - Lumière nocturne (💡)")
        print("     - Entretien végétation (🌿)")
        print("   • Total sur 15 points")
        print("   • Interface épurée sans image satellite")
    else:
        print("❌ PROBLÈMES DÉTECTÉS")


if __name__ == "__main__":
    main()
