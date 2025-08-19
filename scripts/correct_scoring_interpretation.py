#!/usr/bin/env python3
"""
🔧 Correction de l'Interprétation du Scoring - Fincalert
Corrige l'interprétation du système de scoring
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_optimized_data():
    """Charge les données optimisées"""
    optimized_file = ROOT / 'data' / 'combined_scoring_optimized_sentinel1.json'
    
    if not optimized_file.exists():
        print("❌ Fichier de données optimisées non trouvé")
        return None
    
    with open(optimized_file, 'r') as f:
        data = json.load(f)
    
    return data

def correct_interpretation():
    """Corrige l'interprétation du scoring"""
    print("🔧 CORRECTION DE L'INTERPRÉTATION DU SCORING")
    print("=" * 80)
    
    print("\n❌ INTERPRÉTATION INCORRECTE (précédente):")
    print("-" * 50)
    print("Score FAIBLE = Risque d'abandon FAIBLE = Finca ACTIVE")
    print("Score ÉLEVÉ = Risque d'abandon ÉLEVÉ = Finca INACTIVE")
    
    print("\n✅ INTERPRÉTATION CORRECTE:")
    print("-" * 50)
    print("Score FAIBLE = Risque d'abandon ÉLEVÉ = Finca INACTIVE")
    print("Score ÉLEVÉ = Risque d'abandon FAIBLE = Finca ACTIVE")
    
    print("\n🎯 LOGIQUE CORRECTE:")
    print("-" * 50)
    print("• Score NDVI FAIBLE = Végétation dégradée = Finca inactive")
    print("• Score Sentinel-1 FAIBLE = Peu d'activité = Finca inactive")
    print("• Score COMBINÉ FAIBLE = Risque d'abandon ÉLEVÉ")
    print("• Score COMBINÉ ÉLEVÉ = Risque d'abandon FAIBLE")

def explain_correct_scoring():
    """Explique le scoring correct"""
    print("\n📈 CALCUL DU SCORE COMBINÉ (CORRECT):")
    print("-" * 50)
    print("Score Total = (Score NDVI × 60%) + (Score Sentinel-1 × 40%)")
    print("Score Total = (Score NDVI × 0.6) + (Score Sentinel-1 × 0.4)")
    
    print("\n🔍 COMPOSANTES DU SCORE (CORRECT):")
    print("-" * 50)
    
    print("\n1️⃣ SCORE NDVI (60% du total):")
    print("   • Mesure l'état de la végétation")
    print("   • NDVI ÉLEVÉ = Végétation saine = Finca ACTIVE")
    print("   • NDVI FAIBLE = Végétation dégradée = Finca INACTIVE")
    print("   • Score par défaut: 50/100 (modéré)")
    
    print("\n2️⃣ SCORE SENTINEL-1 (40% du total):")
    print("   • Mesure l'activité radar (mouvements/surfaces)")
    print("   • VV ÉLEVÉ = Activité détectée = Finca ACTIVE")
    print("   • VV FAIBLE = Peu d'activité = Finca INACTIVE")
    print("   • Seuils optimisés:")
    print("     - Très élevée (> -5 dB): 90/100 (ACTIVE)")
    print("     - Élevée (> -10 dB): 75/100 (ACTIVE)")
    print("     - Modérée (> -11.8 dB): 50/100 (SEMI-ACTIVE)")
    print("     - Faible (> -12.3 dB): 25/100 (INACTIVE)")
    print("     - Très faible (≤ -12.3 dB): 10/100 (TRÈS INACTIVE)")
    
    print("\n📊 INTERPRÉTATION CORRECTE DES SCORES:")
    print("-" * 50)
    print("Score Total 0-20:   Très élevé risque = Finca très inactive")
    print("Score Total 20-40:  Élevé risque = Finca inactive")
    print("Score Total 40-60:  Risque modéré = Finca semi-active")
    print("Score Total 60-80:  Faible risque = Finca active")
    print("Score Total 80-100: Très faible risque = Finca très active")

def show_correct_examples():
    """Montre des exemples corrigés"""
    data = load_optimized_data()
    if not data:
        return
    
    print("\n🔍 EXEMPLES CORRIGÉS:")
    print("-" * 50)
    
    # Exemple 1: Finca inactive (score faible)
    finca_inactive = data['results'][0]  # finca_00001
    print(f"\n📉 EXEMPLE 1: FINCA INACTIVE (finca_00001)")
    print(f"   • Score total: {finca_inactive['combined_scoring']['overall_score']}/100")
    print(f"   • Niveau: {finca_inactive['combined_scoring']['abandonment_level']}")
    print(f"   • NDVI: {finca_inactive['combined_scoring']['components']['ndvi']['score']}/100")
    print(f"   • Sentinel-1: {finca_inactive['combined_scoring']['components']['sentinel1']['score']}/100")
    print(f"   • VV radar: {finca_inactive['combined_scoring']['components']['sentinel1']['vv_mean']:.3f} dB")
    print(f"   • Signification: Score FAIBLE = Finca INACTIVE (risque d'abandon ÉLEVÉ)")
    
    # Exemple 2: Finca active (score élevé)
    finca_active = None
    for result in data['results']:
        if result['combined_scoring']['overall_score'] > 60:
            finca_active = result
            break
    
    if finca_active:
        print(f"\n📈 EXEMPLE 2: FINCA ACTIVE ({finca_active['finca_id']})")
        print(f"   • Score total: {finca_active['combined_scoring']['overall_score']}/100")
        print(f"   • Niveau: {finca_active['combined_scoring']['abandonment_level']}")
        print(f"   • NDVI: {finca_active['combined_scoring']['components']['ndvi']['score']}/100")
        print(f"   • Sentinel-1: {finca_active['combined_scoring']['components']['sentinel1']['score']}/100")
        print(f"   • VV radar: {finca_active['combined_scoring']['components']['sentinel1']['vv_mean']:.3f} dB")
        print(f"   • Signification: Score ÉLEVÉ = Finca ACTIVE (risque d'abandon FAIBLE)")

def explain_radar_activity_correct():
    """Explique l'activité radar (version corrigée)"""
    print("\n🛰️ ACTIVITÉ RADAR SENTINEL-1 (CORRECT):")
    print("-" * 50)
    print("Le radar Sentinel-1 détecte les changements de surface:")
    print("   • VV ÉLEVÉ (> -10 dB) = Surface réfléchissante = Activité humaine = ACTIVE")
    print("   • VV FAIBLE (< -12 dB) = Surface naturelle = Peu d'activité = INACTIVE")
    print("   • Exemples d'activité détectée:")
    print("     - Véhicules stationnés")
    print("     - Constructions récentes")
    print("     - Surfaces métalliques")
    print("     - Routes asphaltées")
    print("     - Zones cultivées actives")
    
    print("\n📊 INTERPRÉTATION VV (CORRECT):")
    print("   • -1 à -5 dB: Très forte activité = Finca TRÈS ACTIVE")
    print("   • -5 à -10 dB: Forte activité = Finca ACTIVE")
    print("   • -10 à -12 dB: Activité modérée = Finca SEMI-ACTIVE")
    print("   • -12 à -15 dB: Faible activité = Finca INACTIVE")
    print("   • < -15 dB: Très faible activité = Finca TRÈS INACTIVE")

def show_correct_statistics():
    """Affiche les statistiques corrigées"""
    data = load_optimized_data()
    if not data:
        return
    
    print("\n📊 STATISTIQUES CORRIGÉES:")
    print("-" * 50)
    
    scores = [r['combined_scoring']['overall_score'] for r in data['results']]
    ndvi_scores = [r['combined_scoring']['components']['ndvi']['score'] for r in data['results']]
    s1_scores = [r['combined_scoring']['components']['sentinel1']['score'] for r in data['results']]
    
    print(f"Score total moyen: {sum(scores)/len(scores):.1f}/100")
    print(f"Score NDVI moyen: {sum(ndvi_scores)/len(ndvi_scores):.1f}/100")
    print(f"Score Sentinel-1 moyen: {sum(s1_scores)/len(s1_scores):.1f}/100")
    
    print(f"\nDistribution des scores totaux (CORRECT):")
    print(f"   • 0-20: {len([s for s in scores if s <= 20])} fincas (TRÈS INACTIVES)")
    print(f"   • 20-40: {len([s for s in scores if 20 < s <= 40])} fincas (INACTIVES)")
    print(f"   • 40-60: {len([s for s in scores if 40 < s <= 60])} fincas (SEMI-ACTIVES)")
    print(f"   • 60-80: {len([s for s in scores if 60 < s <= 80])} fincas (ACTIVES)")
    print(f"   • 80-100: {len([s for s in scores if s > 80])} fincas (TRÈS ACTIVES)")

def main():
    correct_interpretation()
    explain_correct_scoring()
    explain_radar_activity_correct()
    show_correct_examples()
    show_correct_statistics()
    
    print("\n💡 RÉSUMÉ CORRIGÉ:")
    print("-" * 50)
    print("❌ Score FAIBLE = Risque d'abandon ÉLEVÉ = Finca INACTIVE")
    print("✅ Score ÉLEVÉ = Risque d'abandon FAIBLE = Finca ACTIVE")
    print("📡 Sentinel-1: VV élevé = Activité = Finca active")
    print("🌱 NDVI: Score élevé = Végétation saine = Finca active")
    print("⚖️ Score combiné = 60% NDVI + 40% Sentinel-1")
    print("\n🎯 CONCLUSION: Une combinaison de scores FAIBLES = Finca INACTIVE")

if __name__ == "__main__":
    main()
