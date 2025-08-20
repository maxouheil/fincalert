#!/usr/bin/env python3
"""
📊 Comparaison Activité Radar - Récente vs Moyenne 6 Mois
Compare les résultats d'une image récente vs une moyenne sur 6 mois
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_recent_data():
    """Charge les données Sentinel-1 récentes (image unique)"""
    s1_dir = ROOT / 'data' / 'sentinel1_ultra_precise_analysis'
    summary_files = [f for f in s1_dir.glob('*50m_summary*.json')]
    
    if not summary_files:
        return None
    
    latest_file = max(summary_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Données récentes: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def load_6months_data():
    """Charge les données Sentinel-1 moyenne 6 mois"""
    s1_dir = ROOT / 'data' / 'sentinel1_6months_analysis'
    summary_files = [f for f in s1_dir.glob('*6months_summary*.json')]
    
    if not summary_files:
        return None
    
    latest_file = max(summary_files, key=lambda x: x.stat().st_mtime)
    print(f"📄 Données 6 mois: {latest_file.name}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    return data

def main():
    print("📊 COMPARAISON ACTIVITÉ RADAR - RÉCENTE vs MOYENNE 6 MOIS")
    print("=" * 70)
    
    # Charger les données
    recent_data = load_recent_data()
    months6_data = load_6months_data()
    
    if not recent_data or not months6_data:
        print("❌ Données manquantes")
        return
    
    # Créer des dictionnaires pour faciliter la comparaison
    recent_dict = {finca['finca_id']: finca for finca in recent_data['fincas']}
    months6_dict = {finca['finca_id']: finca for finca in months6_data['fincas']}
    
    # Fincas communes
    common_fincas = [fid for fid in months6_dict.keys() if fid in recent_dict]
    print(f"📊 {len(common_fincas)} fincas avec données complètes")
    
    print(f"\n📈 COMPARAISON DÉTAILLÉE")
    print("-" * 100)
    print(f"{'Finca':<12} {'Récent VV':<12} {'Récent Niv':<12} {'6mois VV':<12} {'6mois Niv':<12} {'Diff VV':<10} {'Changement':<15}")
    print("-" * 100)
    
    differences = []
    level_changes = 0
    
    for finca_id in sorted(common_fincas):
        recent_finca = recent_dict[finca_id]
        months6_finca = months6_dict[finca_id]
        
        recent_vv = recent_finca['avg_vv']
        months6_vv = months6_finca['avg_vv_6months']
        diff_vv = months6_vv - recent_vv
        
        recent_level = recent_finca['overall_activity']
        months6_level = months6_finca['overall_activity']
        
        level_changed = recent_level != months6_level
        if level_changed:
            level_changes += 1
        
        differences.append(diff_vv)
        
        change_indicator = "🔄 Changé" if level_changed else "➡️ Stable"
        
        print(f"{finca_id:<12} "
              f"{recent_vv:<12.3f} "
              f"{recent_level:<12} "
              f"{months6_vv:<12.3f} "
              f"{months6_level:<12} "
              f"{diff_vv:<10.3f} "
              f"{change_indicator:<15}")
    
    print("-" * 100)
    
    # Statistiques des différences
    avg_diff = sum(differences) / len(differences)
    max_diff = max(differences)
    min_diff = min(differences)
    
    print(f"\n📊 STATISTIQUES DES DIFFÉRENCES")
    print("=" * 50)
    print(f"📁 Fincas comparées: {len(common_fincas)}")
    print(f"📈 Différence moyenne: {avg_diff:.3f} dB")
    print(f"📊 Différence max: {max_diff:.3f} dB")
    print(f"📉 Différence min: {min_diff:.3f} dB")
    print(f"🔄 Changements de niveau: {level_changes}/{len(common_fincas)} ({level_changes/len(common_fincas)*100:.1f}%)")
    
    # Analyse des changements de niveau
    if level_changes > 0:
        print(f"\n🔄 CHANGEMENTS DE NIVEAU DÉTAILLÉS:")
        for finca_id in sorted(common_fincas):
            recent_finca = recent_dict[finca_id]
            months6_finca = months6_dict[finca_id]
            
            if recent_finca['overall_activity'] != months6_finca['overall_activity']:
                print(f"   • {finca_id}: {recent_finca['overall_activity']} → {months6_finca['overall_activity']}")
    
    # Résumé des deux analyses
    print(f"\n📋 RÉSUMÉ DES DEUX ANALYSES")
    print("=" * 50)
    
    print(f"🔍 ANALYSE RÉCENTE (Image unique):")
    print(f"   • Fincas: {len(recent_data['fincas'])}")
    print(f"   • VV moyen: {recent_data['vv_statistics']['mean']:.3f} dB")
    print(f"   • Distribution: {recent_data['activity_distribution']}")
    
    print(f"\n🔍 ANALYSE 6 MOIS (Moyenne temporelle):")
    print(f"   • Fincas: {len(months6_data['fincas'])}")
    print(f"   • VV moyen: {months6_data['vv_statistics']['mean']:.3f} dB")
    print(f"   • Distribution: {months6_data['activity_distribution']}")
    
    print(f"\n💡 OBSERVATIONS:")
    if abs(avg_diff) < 1.0:
        print(f"   ✅ Différences faibles - activité stable")
    else:
        print(f"   ⚠️  Différences notables - activité variable")
    
    if level_changes > 0:
        print(f"   🔄 La moyenne 6 mois change la classification pour {level_changes} fincas")
    else:
        print(f"   ✅ Classification stable entre les deux analyses")
    
    print(f"\n🎯 RECOMMANDATIONS:")
    print(f"   • Image récente: Détecte l'activité actuelle (instantanée)")
    print(f"   • Moyenne 6 mois: Donne une vue plus stable et représentative")
    print(f"   • Pour l'abandon: La moyenne 6 mois est plus fiable")
    print(f"   • Pour l'activité: L'image récente est plus sensible")

if __name__ == "__main__":
    main()
