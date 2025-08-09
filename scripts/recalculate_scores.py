#!/usr/bin/env python3
"""
Recalcule les scores d'abandon avec l'algorithme corrigé
Utilise les données NDVI existantes, change seulement la formule POTENTIAL
"""

import json
import csv
import os
from datetime import datetime

def _calculate_abandon_score_corrected(status: str, std: float, dips: int, green_persistence: float) -> float:
    """Calculate numerical abandon score 0-100 (100 = most likely abandoned) - CORRECTED VERSION"""
    if status == "inactive":
        return 85.0 + min(15.0, green_persistence * 15.0)
    elif status == "potential":
        # CORRECTED: Lower std (more stable) should result in higher score
        return 80.0 - min(40.0, std * 500.0) + dips * 10.0
    elif status == "active":
        return max(5.0, 25.0 - std * 200.0 - dips * 5.0)
    else:
        return 50.0  # unknown

def coefficient_of_variation(std_dev: float, median: float) -> float:
    """Calculate coefficient of variation as percentage"""
    if median == 0:
        return 0.0
    return (std_dev / median) * 100.0

def recalculate_all_scores():
    """Recalcule tous les scores avec l'algorithme corrigé"""
    
    # Chemin du fichier d'analyse existant le plus récent
    input_file = "/Users/sou/Desktop/Fincalert/data/abandon_analysis_FULL/fincas_abandon_analysis_FULL_20250809_120932.json"
    
    if not os.path.exists(input_file):
        print(f"❌ Fichier d'entrée introuvable: {input_file}")
        return
    
    print(f"📖 Lecture des données existantes: {input_file}")
    
    # Charger les données existantes
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    print(f"📊 {len(data['fincas'])} fincas trouvées")
    
    # Statistiques
    recalculated_count = 0
    status_changes = {"potential": 0, "active": 0, "inactive": 0, "unknown": 0}
    score_changes = []
    
    # Recalculer seulement les scores
    for finca in data['fincas']:
        if finca['status'] == 'success':
            old_score = finca['abandon_score']
            
            # Récupérer les métriques NDVI existantes
            std_dev = finca['std_deviation']
            median_ndvi = finca['median_ndvi']
            
            # Compter les dips (périodes avec NDVI ≤ 0.30)
            dips_count = 0
            green_persistence = 0.0
            
            if 'ndvi_timeseries' in finca and finca['ndvi_timeseries']:
                valid_ndvi = [ts['ndvi_value'] for ts in finca['ndvi_timeseries'] if ts['ndvi_value'] is not None]
                if valid_ndvi:
                    dips_count = sum(1 for ndvi in valid_ndvi if ndvi <= 0.30)
                    green_count = sum(1 for ndvi in valid_ndvi if ndvi >= 0.55)
                    green_persistence = green_count / len(valid_ndvi) if valid_ndvi else 0.0
            
            # Déterminer le status (unchanged logic)
            if median_ndvi < 0.30:
                activity_status = "inactive"
            elif dips_count > 0:
                activity_status = "potential"
            elif median_ndvi >= 0.55:
                activity_status = "active"
            else:
                activity_status = "potential"
            
            # Calculer le nouveau score avec l'algorithme corrigé
            new_score = _calculate_abandon_score_corrected(
                activity_status, std_dev, dips_count, green_persistence
            )
            
            # Mettre à jour
            finca['abandon_score'] = round(new_score, 1)
            finca['activity_status'] = activity_status
            
            # Statistiques
            if abs(new_score - old_score) > 0.1:  # Changement significatif
                recalculated_count += 1
                score_changes.append({
                    'finca_id': finca['finca_id'],
                    'old_score': old_score,
                    'new_score': new_score,
                    'status': activity_status,
                    'std_dev': std_dev,
                    'cv_percent': coefficient_of_variation(std_dev, median_ndvi)
                })
            
            status_changes[activity_status] += 1
    
    # Timestamp pour les nouveaux fichiers
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Sauvegarder le JSON complet recalculé
    output_dir = "/Users/sou/Desktop/Fincalert/data/abandon_analysis_FULL"
    json_output = f"{output_dir}/fincas_abandon_analysis_CORRECTED_{timestamp}.json"
    
    with open(json_output, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Créer le CSV des scores
    csv_output = f"{output_dir}/fincas_abandon_scores_CORRECTED_{timestamp}.csv"
    
    with open(csv_output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['finca_id', 'abandon_score', 'activity_status', 'median_ndvi', 'std_deviation', 'cv_percent', 'valid_periods'])
        
        for finca in data['fincas']:
            if finca['status'] == 'success':
                cv_percent = coefficient_of_variation(finca['std_deviation'], finca['median_ndvi'])
                writer.writerow([
                    finca['finca_id'],
                    finca['abandon_score'],
                    finca['activity_status'],
                    finca['median_ndvi'],
                    finca['std_deviation'],
                    round(cv_percent, 1),
                    finca['valid_periods']
                ])
    
    # Créer le résumé
    summary_output = f"{output_dir}/analysis_summary_CORRECTED_{timestamp}.json"
    
    # Calculer nouvelles statistiques
    scores = [finca['abandon_score'] for finca in data['fincas'] if finca['status'] == 'success']
    risk_high = sum(1 for s in scores if s >= 70)
    risk_medium = sum(1 for s in scores if 40 <= s < 70)
    risk_low = sum(1 for s in scores if s < 40)
    
    summary = {
        "timestamp": timestamp,
        "algorithm_version": "corrected_potential_formula",
        "total_fincas": len([f for f in data['fincas'] if f['status'] == 'success']),
        "recalculated_count": recalculated_count,
        "status_distribution": status_changes,
        "risk_distribution": {
            "high_risk_ge_70": risk_high,
            "medium_risk_40_69": risk_medium,
            "low_risk_lt_40": risk_low
        },
        "score_statistics": {
            "mean": round(sum(scores) / len(scores), 1) if scores else 0,
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0
        },
        "files_generated": {
            "json_data": json_output,
            "csv_scores": csv_output,
            "summary": summary_output
        }
    }
    
    with open(summary_output, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Afficher les résultats
    print("\n🎉 RECALCUL TERMINÉ!")
    print("=" * 60)
    print(f"✅ Fincas avec changements: {recalculated_count}")
    print(f"📊 Distribution des status:")
    for status, count in status_changes.items():
        print(f"   {status}: {count}")
    
    print(f"\n🚨 NOUVELLE DISTRIBUTION DES RISQUES:")
    print(f"🔴 Risque élevé (≥70): {risk_high}")
    print(f"🟡 Risque moyen (40-69): {risk_medium}")
    print(f"🟢 Risque faible (<40): {risk_low}")
    
    print(f"\n💾 FICHIERS GÉNÉRÉS:")
    print(f"📄 JSON: {json_output}")
    print(f"📊 CSV: {csv_output}")
    print(f"📈 Résumé: {summary_output}")
    
    # Afficher quelques exemples de changements
    if score_changes:
        print(f"\n📈 EXEMPLES DE CHANGEMENTS (top 10):")
        score_changes.sort(key=lambda x: abs(x['new_score'] - x['old_score']), reverse=True)
        for i, change in enumerate(score_changes[:10]):
            diff = change['new_score'] - change['old_score']
            print(f"   {change['finca_id']}: {change['old_score']:.1f} → {change['new_score']:.1f} ({diff:+.1f}) | CV: {change['cv_percent']:.1f}%")
    
    return json_output

if __name__ == "__main__":
    json_file = recalculate_all_scores()
    
    # Proposer de mettre à jour le frontend
    print(f"\n🔄 MISE À JOUR DU FRONTEND:")
    print(f"Voulez-vous générer le GeoJSON pour le frontend avec les nouveaux scores?")
    
    response = input("Appuyez sur Entrée pour continuer ou 'n' pour annuler: ")
    if response.lower() != 'n':
        import subprocess
        print("🚀 Génération du GeoJSON frontend...")
        subprocess.run([
            "python", "scripts/generate_frontend_data.py",
            "--scores", json_file
        ])
        print("✅ Frontend mis à jour!")
