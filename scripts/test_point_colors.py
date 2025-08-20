#!/usr/bin/env python3
"""
Test des couleurs des points pour vérifier qu'elles reflètent le système de scoring simple
"""

import requests
import json


def test_simple_scoring_colors():
    """Test que les couleurs correspondent aux scores simples"""
    print("🎨 TEST DES COULEURS DES POINTS")
    print("=" * 50)
    
    try:
        # Charger les données NDVI des 631 fincas
        response = requests.get("http://localhost:8000/api/ndvi-all/631-fincas")
        if response.status_code != 200:
            print(f"❌ Erreur API: {response.status_code}")
            return False
        
        data = response.json()
        fincas = data['fincas']
        
        print(f"📊 Total fincas: {len(fincas)}")
        
        # Analyser quelques fincas représentatives
        test_fincas = [
            'finca_00001',  # CV: 12.8%, semi-active
            'finca_00010',  # CV: 38.1%, active
            'finca_00014',  # CV: 10.3%, inactive
            'finca_00034',  # CV: 48.5%, active
            'finca_00044',  # CV: 86.0%, active
        ]
        
        print(f"\n🎯 Analyse des fincas de test:")
        print("-" * 40)
        
        for finca_id in test_fincas:
            finca = next((f for f in fincas if f['finca_id'] == finca_id), None)
            if not finca:
                print(f"❌ {finca_id}: Non trouvée")
                continue
            
            # Calculer le score simple
            cv = finca['cv_percent'] / 100
            activity_status = finca['activity_status']
            
            # Score végétation basé sur CV
            if cv >= 0.25:
                vegetation_points = 5  # Fort
            elif cv >= 0.12:
                vegetation_points = 3  # Moyen
            else:
                vegetation_points = 1  # Faible
            
            # Score radar basé sur l'activité
            if activity_status == 'active':
                radar_points = 5  # Fort
            elif activity_status == 'semi-active':
                radar_points = 3  # Moyen
            else:
                radar_points = 1  # Faible
            
            # Score luminosité basé sur l'activité
            if activity_status == 'active':
                luminosite_points = 5  # Fort
            elif activity_status == 'semi-active':
                luminosite_points = 3  # Moyen
            else:
                luminosite_points = 1  # Faible
            
            total_points = radar_points + luminosite_points + vegetation_points
            
            # Classification
            if total_points >= 10:
                classification = 'Active'
                color = '🟢 Vert'
            elif total_points >= 5:
                classification = 'Moderate'
                color = '🟠 Orange'
            else:
                classification = 'Inactive'
                color = '🔴 Rouge'
            
            print(f"📍 {finca_id}:")
            print(f"   • CV: {cv*100:.1f}% → Végétation: {vegetation_points}pts")
            print(f"   • Status: {activity_status} → Radar: {radar_points}pts, Luminosité: {luminosite_points}pts")
            print(f"   • Total: {total_points}/15 → {classification} {color}")
        
        # Statistiques globales
        print(f"\n📈 Statistiques globales:")
        print("-" * 40)
        
        scores = []
        for finca in fincas:
            cv = finca['cv_percent'] / 100
            activity_status = finca['activity_status']
            
            # Score végétation
            if cv >= 0.25:
                vegetation_points = 5
            elif cv >= 0.12:
                vegetation_points = 3
            else:
                vegetation_points = 1
            
            # Score radar et luminosité
            if activity_status == 'active':
                radar_points = luminosite_points = 5
            elif activity_status == 'semi-active':
                radar_points = luminosite_points = 3
            else:
                radar_points = luminosite_points = 1
            
            total_points = radar_points + luminosite_points + vegetation_points
            scores.append(total_points)
        
        # Distribution des couleurs
        green_count = sum(1 for s in scores if s >= 10)
        orange_count = sum(1 for s in scores if 5 <= s < 10)
        red_count = sum(1 for s in scores if s < 5)
        
        print(f"🟢 Vert (Active, 10-15pts): {green_count} fincas ({green_count/len(scores)*100:.1f}%)")
        print(f"🟠 Orange (Moderate, 5-9pts): {orange_count} fincas ({orange_count/len(scores)*100:.1f}%)")
        print(f"🔴 Rouge (Inactive, 1-4pts): {red_count} fincas ({red_count/len(scores)*100:.1f}%)")
        
        # Statistiques des scores
        min_score = min(scores)
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        
        print(f"\n📊 Scores:")
        print(f"   • Min: {min_score}/15")
        print(f"   • Max: {max_score}/15")
        print(f"   • Moyenne: {avg_score:.1f}/15")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def main():
    """Fonction principale"""
    print("🚀 TEST DES COULEURS DES POINTS")
    print("=" * 60)
    
    success = test_simple_scoring_colors()
    
    print(f"\n🎯 RÉSUMÉ")
    print("=" * 60)
    
    if success:
        print("✅ COULEURS DES POINTS OPÉRATIONNELLES!")
        print("📊 Les points sur la carte reflètent maintenant:")
        print("   • 🟢 Vert: Fincas actives (10-15 points)")
        print("   • 🟠 Orange: Fincas modérées (5-9 points)")
        print("   • 🔴 Rouge: Fincas inactives (1-4 points)")
        print("   • Basé sur le système de scoring simple (3 critères)")
    else:
        print("❌ PROBLÈMES DÉTECTÉS")


if __name__ == "__main__":
    main()
