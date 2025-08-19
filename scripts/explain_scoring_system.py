#!/usr/bin/env python3
"""
📊 Explication du Système de Scoring - Fincalert
Explique en détail comment les scores sont calculés et leur signification
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

def explain_scoring_system():
    """Explique le système de scoring"""
    print("📊 SYSTÈME DE SCORING FINCALERT - EXPLICATION DÉTAILLÉE")
    print("=" * 80)
    
    print("\n🎯 QU'EST-CE QUE 'MOINS À RISQUE' ?")
    print("-" * 50)
    print("Une finca 'moins à risque' = finca qui a PEU de risque d'être abandonnée")
    print("Score FAIBLE = Risque d'abandon FAIBLE = Finca ACTIVE")
    print("Score ÉLEVÉ = Risque d'abandon ÉLEVÉ = Finca INACTIVE/ABANDONNÉE")
    
    print("\n📈 CALCUL DU SCORE COMBINÉ:")
    print("-" * 50)
    print("Score Total = (Score NDVI × 60%) + (Score Sentinel-1 × 40%)")
    print("Score Total = (Score NDVI × 0.6) + (Score Sentinel-1 × 0.4)")
    
    print("\n🔍 COMPOSANTES DU SCORE:")
    print("-" * 50)
    
    print("\n1️⃣ SCORE NDVI (60% du total):")
    print("   • Mesure l'état de la végétation")
    print("   • NDVI élevé = Végétation saine = Finca active")
    print("   • NDVI faible = Végétation dégradée = Finca inactive")
    print("   • Score par défaut: 50/100 (modéré)")
    
    print("\n2️⃣ SCORE SENTINEL-1 (40% du total):")
    print("   • Mesure l'activité radar (mouvements/surfaces)")
    print("   • VV élevé = Activité détectée = Finca active")
    print("   • VV faible = Peu d'activité = Finca inactive")
    print("   • Seuils optimisés:")
    print("     - Très élevée (> -5 dB): 90/100")
    print("     - Élevée (> -10 dB): 75/100")
    print("     - Modérée (> -11.8 dB): 50/100")
    print("     - Faible (> -12.3 dB): 25/100")
    print("     - Très faible (≤ -12.3 dB): 10/100")
    
    print("\n📊 INTERPRÉTATION DES SCORES:")
    print("-" * 50)
    print("Score Total 0-20:   Très faible risque = Finca très active")
    print("Score Total 20-40:  Faible risque = Finca active")
    print("Score Total 40-60:  Risque modéré = Finca semi-active")
    print("Score Total 60-80:  Risque élevé = Finca inactive")
    print("Score Total 80-100: Très élevé risque = Finca abandonnée")

def show_examples():
    """Montre des exemples concrets"""
    data = load_optimized_data()
    if not data:
        return
    
    print("\n🔍 EXEMPLES CONCRETS:")
    print("-" * 50)
    
    # Exemple 1: Finca très active (score faible)
    finca_active = data['results'][0]  # finca_00001
    print(f"\n📈 EXEMPLE 1: FINCA TRÈS ACTIVE (finca_00001)")
    print(f"   • Score total: {finca_active['combined_scoring']['overall_score']}/100")
    print(f"   • Niveau: {finca_active['combined_scoring']['abandonment_level']}")
    print(f"   • NDVI: {finca_active['combined_scoring']['components']['ndvi']['score']}/100")
    print(f"   • Sentinel-1: {finca_active['combined_scoring']['components']['sentinel1']['score']}/100")
    print(f"   • VV radar: {finca_active['combined_scoring']['components']['sentinel1']['vv_mean']:.3f} dB")
    print(f"   • Signification: Finca avec peu d'activité radar = probablement inactive")
    
    # Exemple 2: Finca très inactive (score élevé)
    finca_inactive = None
    for result in data['results']:
        if result['combined_scoring']['overall_score'] > 60:
            finca_inactive = result
            break
    
    if finca_inactive:
        print(f"\n📉 EXEMPLE 2: FINCA TRÈS INACTIVE ({finca_inactive['finca_id']})")
        print(f"   • Score total: {finca_inactive['combined_scoring']['overall_score']}/100")
        print(f"   • Niveau: {finca_inactive['combined_scoring']['abandonment_level']}")
        print(f"   • NDVI: {finca_inactive['combined_scoring']['components']['ndvi']['score']}/100")
        print(f"   • Sentinel-1: {finca_inactive['combined_scoring']['components']['sentinel1']['score']}/100")
        print(f"   • VV radar: {finca_inactive['combined_scoring']['components']['sentinel1']['vv_mean']:.3f} dB")
        print(f"   • Signification: Finca avec forte activité radar = probablement active")

def explain_radar_activity():
    """Explique l'activité radar"""
    print("\n🛰️ ACTIVITÉ RADAR SENTINEL-1:")
    print("-" * 50)
    print("Le radar Sentinel-1 détecte les changements de surface:")
    print("   • VV élevé (> -10 dB) = Surface réfléchissante = Activité humaine")
    print("   • VV faible (< -12 dB) = Surface naturelle = Peu d'activité")
    print("   • Exemples d'activité détectée:")
    print("     - Véhicules stationnés")
    print("     - Constructions récentes")
    print("     - Surfaces métalliques")
    print("     - Routes asphaltées")
    print("     - Zones cultivées actives")
    
    print("\n📊 INTERPRÉTATION VV:")
    print("   • -1 à -5 dB: Très forte activité (zones urbaines)")
    print("   • -5 à -10 dB: Forte activité (zones cultivées actives)")
    print("   • -10 à -12 dB: Activité modérée (zones semi-actives)")
    print("   • -12 à -15 dB: Faible activité (zones naturelles)")
    print("   • < -15 dB: Très faible activité (zones abandonnées)")

def show_statistics():
    """Affiche les statistiques détaillées"""
    data = load_optimized_data()
    if not data:
        return
    
    print("\n📊 STATISTIQUES DÉTAILLÉES:")
    print("-" * 50)
    
    scores = [r['combined_scoring']['overall_score'] for r in data['results']]
    ndvi_scores = [r['combined_scoring']['components']['ndvi']['score'] for r in data['results']]
    s1_scores = [r['combined_scoring']['components']['sentinel1']['score'] for r in data['results']]
    
    print(f"Score total moyen: {sum(scores)/len(scores):.1f}/100")
    print(f"Score NDVI moyen: {sum(ndvi_scores)/len(ndvi_scores):.1f}/100")
    print(f"Score Sentinel-1 moyen: {sum(s1_scores)/len(s1_scores):.1f}/100")
    
    print(f"\nDistribution des scores totaux:")
    print(f"   • 0-20: {len([s for s in scores if s <= 20])} fincas")
    print(f"   • 20-40: {len([s for s in scores if 20 < s <= 40])} fincas")
    print(f"   • 40-60: {len([s for s in scores if 40 < s <= 60])} fincas")
    print(f"   • 60-80: {len([s for s in scores if 60 < s <= 80])} fincas")
    print(f"   • 80-100: {len([s for s in scores if s > 80])} fincas")

def main():
    explain_scoring_system()
    explain_radar_activity()
    show_examples()
    show_statistics()
    
    print("\n💡 RÉSUMÉ:")
    print("-" * 50)
    print("✅ Score FAIBLE = Risque d'abandon FAIBLE = Finca ACTIVE")
    print("❌ Score ÉLEVÉ = Risque d'abandon ÉLEVÉ = Finca INACTIVE")
    print("📡 Sentinel-1 détecte l'activité humaine via radar")
    print("🌱 NDVI mesure l'état de la végétation")
    print("⚖️ Score combiné = 60% NDVI + 40% Sentinel-1")

if __name__ == "__main__":
    main()
