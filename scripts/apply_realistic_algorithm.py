#!/usr/bin/env python3
"""
Applique l'algorithme réaliste ajusté sur les données existantes
Distribution cible: 46% Active, 38% Semi-active, 16% Inactive
"""

import json
import csv
import os
from datetime import datetime

def calculate_abandon_score_realistic(median_ndvi: float, std: float, dips: int, green_persistence: float) -> tuple:
    """
    Calculate activity status and abandon score using realistic algorithm
    Returns: (status, score)
    
    Distribution target: 46% Active, 38% Semi-active, 16% Inactive
    """
    # Calculate coefficient of variation (CV)
    cv_percent = (std / median_ndvi) * 100.0 if median_ndvi > 0 else 0.0
    
    # INACTIVE/ABANDONNÉE (Score 70-85) - Target ~15%
    if (cv_percent < 12 and dips == 0) or \
       (median_ndvi >= 0.4 and cv_percent < 8) or \
       (green_persistence >= 0.5) or \
       (median_ndvi >= 0.3 and cv_percent < 6):
        # Abandoned finca: stable vegetation, no activity
        base_score = 72.0
        # Bonus for extreme stability
        stability_bonus = max(0, (12 - cv_percent) * 0.8) if cv_percent < 12 else 0
        # Bonus for dense vegetation
        vegetation_bonus = (median_ndvi - 0.2) * 15 if median_ndvi > 0.2 else 0
        score = min(85.0, base_score + stability_bonus + vegetation_bonus)
        return "inactive", score
    
    # ACTIVE (Score 15-35) - Target ~45%
    elif (cv_percent >= 25) or \
         (cv_percent >= 18 and dips >= 1) or \
         (cv_percent >= 20 and median_ndvi < 0.25):
        # Active finca: high variation, detected activity
        base_score = 25.0
        activity_bonus = min(8.0, (cv_percent - 18) * 0.3) if cv_percent > 18 else 0
        dips_bonus = min(5.0, dips * 2.5)
        score = max(15.0, base_score - activity_bonus - dips_bonus)
        return "active", score
    
    # SEMI-ACTIVE (Score 40-65) - Target ~40%
    else:
        # Semi-active finca: moderate usage, transition
        base_score = 52.0
        
        # CV adjustment
        if cv_percent < 15:
            cv_adjustment = (15 - cv_percent) * 0.6
        else:
            cv_adjustment = -(cv_percent - 15) * 0.3
        
        # Dips adjustment
        dips_adjustment = -dips * 2 if dips > 0 else 3
        
        score = base_score + cv_adjustment + dips_adjustment
        score = max(40.0, min(65.0, score))
        return "semi-active", score

def coefficient_of_variation(std_dev: float, median: float) -> float:
    """Calculate coefficient of variation as percentage"""
    if median == 0:
        return 0.0
    return (std_dev / median) * 100.0

def apply_realistic_algorithm():
    """Applique l'algorithme réaliste sur les données existantes"""
    
    # Chemin du fichier d'analyse existant
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
    status_changes = {"active": 0, "semi-active": 0, "inactive": 0, "unknown": 0}
    score_changes = []
    old_vs_new = []
    
    # Appliquer le nouvel algorithme
    for finca in data['fincas']:
        if finca['status'] == 'success':
            old_score = finca['abandon_score']
            old_status = finca['activity_status']
            
            # Récupérer les métriques NDVI existantes
            std_dev = finca['std_deviation']
            median_ndvi = finca['median_ndvi']
            
            # Compter les dips et green persistence
            dips_count = 0
            green_persistence = 0.0
            
            if 'ndvi_timeseries' in finca and finca['ndvi_timeseries']:
                valid_ndvi = [ts['ndvi_value'] for ts in finca['ndvi_timeseries'] if ts['ndvi_value'] is not None]
                if valid_ndvi:
                    # Dips: NDVI <= median - 0.15 (selon breakdown)
                    dips_threshold = median_ndvi - 0.15
                    dips_count = sum(1 for ndvi in valid_ndvi if ndvi <= dips_threshold)
                    
                    # Green persistence: % with NDVI >= 0.55
                    green_count = sum(1 for ndvi in valid_ndvi if ndvi >= 0.55)
                    green_persistence = green_count / len(valid_ndvi) if valid_ndvi else 0.0
            
            # Calculer avec l'algorithme réaliste
            new_status, new_score = calculate_abandon_score_realistic(
                median_ndvi, std_dev, dips_count, green_persistence
            )
            
            # Mettre à jour
            finca['abandon_score'] = round(new_score, 1)
            finca['activity_status'] = new_status
            
            # Statistiques
            status_changes[new_status] += 1
            recalculated_count += 1
            
            cv_percent = coefficient_of_variation(std_dev, median_ndvi)
            
            change_record = {
                'finca_id': finca['finca_id'],
                'old_score': old_score,
                'new_score': new_score,
                'old_status': old_status,
                'new_status': new_status,
                'median_ndvi': median_ndvi,
                'cv_percent': cv_percent,
                'dips': dips_count,
                'green_pct': green_persistence * 100
            }
            old_vs_new.append(change_record)
            
            if abs(new_score - old_score) > 5.0:  # Changement significatif
                score_changes.append(change_record)
    
    # Timestamp pour les nouveaux fichiers
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Sauvegarder le JSON complet avec algorithme réaliste
    output_dir = "/Users/sou/Desktop/Fincalert/data/abandon_analysis_FULL"
    json_output = f"{output_dir}/fincas_abandon_analysis_REALISTIC_{timestamp}.json"
    
    with open(json_output, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Créer le CSV des scores
    csv_output = f"{output_dir}/fincas_abandon_scores_REALISTIC_{timestamp}.csv"
    
    with open(csv_output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['finca_id', 'abandon_score', 'activity_status', 'median_ndvi', 'std_deviation', 'cv_percent', 'dips', 'green_persistence', 'valid_periods'])
        
        for finca in data['fincas']:
            if finca['status'] == 'success':
                cv_percent = coefficient_of_variation(finca['std_deviation'], finca['median_ndvi'])
                # Recalculer dips et green_persistence pour le CSV
                dips_count = 0
                green_persistence = 0.0
                if 'ndvi_timeseries' in finca and finca['ndvi_timeseries']:
                    valid_ndvi = [ts['ndvi_value'] for ts in finca['ndvi_timeseries'] if ts['ndvi_value'] is not None]
                    if valid_ndvi:
                        dips_threshold = finca['median_ndvi'] - 0.15
                        dips_count = sum(1 for ndvi in valid_ndvi if ndvi <= dips_threshold)
                        green_count = sum(1 for ndvi in valid_ndvi if ndvi >= 0.55)
                        green_persistence = green_count / len(valid_ndvi)
                
                writer.writerow([
                    finca['finca_id'],
                    finca['abandon_score'],
                    finca['activity_status'],
                    finca['median_ndvi'],
                    finca['std_deviation'],
                    round(cv_percent, 1),
                    dips_count,
                    round(green_persistence, 3),
                    finca['valid_periods']
                ])
    
    # Créer le résumé
    summary_output = f"{output_dir}/analysis_summary_REALISTIC_{timestamp}.json"
    
    # Calculer nouvelles statistiques
    scores = [finca['abandon_score'] for finca in data['fincas'] if finca['status'] == 'success']
    risk_high = sum(1 for s in scores if s >= 70)
    risk_medium = sum(1 for s in scores if 40 <= s < 70)
    risk_low = sum(1 for s in scores if s < 40)
    
    # Analyse par status
    cv_by_status = {"active": [], "semi-active": [], "inactive": []}
    for record in old_vs_new:
        cv_by_status[record['new_status']].append(record['cv_percent'])
    
    cv_averages = {}
    for status, cvs in cv_by_status.items():
        cv_averages[status] = round(sum(cvs) / len(cvs), 1) if cvs else 0
    
    summary = {
        "timestamp": timestamp,
        "algorithm_version": "realistic_adjusted",
        "total_fincas": len([f for f in data['fincas'] if f['status'] == 'success']),
        "recalculated_count": recalculated_count,
        "status_distribution": status_changes,
        "status_percentages": {
            status: round((count / recalculated_count) * 100, 1) 
            for status, count in status_changes.items()
        },
        "risk_distribution": {
            "high_risk_ge_70": risk_high,
            "medium_risk_40_69": risk_medium,
            "low_risk_lt_40": risk_low
        },
        "risk_percentages": {
            "high": round((risk_high / recalculated_count) * 100, 1),
            "medium": round((risk_medium / recalculated_count) * 100, 1),
            "low": round((risk_low / recalculated_count) * 100, 1)
        },
        "cv_by_status": cv_averages,
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
    print("\n🎉 ALGORITHME RÉALISTE APPLIQUÉ!")
    print("=" * 60)
    print(f"✅ Fincas recalculées: {recalculated_count}")
    
    print(f"\n📈 NOUVELLE DISTRIBUTION:")
    total_success = sum(status_changes.values())
    for status, count in status_changes.items():
        pct = (count / total_success) * 100 if total_success > 0 else 0
        status_label = {
            "active": "🟢 ACTIVE", 
            "semi-active": "🟡 SEMI-ACTIVE", 
            "inactive": "🔴 ABANDONNÉE",
            "unknown": "⚪ UNKNOWN"
        }.get(status, f"❓ {status.upper()}")
        print(f"   {status_label}: {count} ({pct:.1f}%)")
    
    print(f"\n🚨 DISTRIBUTION DES RISQUES:")
    print(f"🔴 Risque élevé (≥70): {risk_high} ({summary['risk_percentages']['high']:.1f}%)")
    print(f"🟡 Risque moyen (40-69): {risk_medium} ({summary['risk_percentages']['medium']:.1f}%)")
    print(f"🟢 Risque faible (<40): {risk_low} ({summary['risk_percentages']['low']:.1f}%)")
    
    print(f"\n📊 CV MOYEN PAR STATUS:")
    for status, avg_cv in cv_averages.items():
        status_label = {
            "active": "🟢 Active", 
            "semi-active": "🟡 Semi-active", 
            "inactive": "🔴 Abandonnée",
            "unknown": "⚪ Unknown"
        }.get(status, f"❓ {status}")
        print(f"   {status_label}: {avg_cv}%")
    
    print(f"\n💾 FICHIERS GÉNÉRÉS:")
    print(f"📄 JSON: {json_output}")
    print(f"📊 CSV: {csv_output}")
    print(f"📈 Résumé: {summary_output}")
    
    # Afficher quelques exemples de changements significatifs
    if score_changes:
        print(f"\n📈 CHANGEMENTS SIGNIFICATIFS (échantillon):")
        score_changes.sort(key=lambda x: abs(x['new_score'] - x['old_score']), reverse=True)
        for i, change in enumerate(score_changes[:10]):
            diff = change['new_score'] - change['old_score']
            print(f"   {change['finca_id']}: {change['old_status']}→{change['new_status']} | {change['old_score']:.1f}→{change['new_score']:.1f} ({diff:+.1f}) | CV:{change['cv_percent']:.1f}%")
    
    return json_output

if __name__ == "__main__":
    json_file = apply_realistic_algorithm()
    print(f"\n🔄 Prêt pour mettre à jour le frontend avec: {json_file}")
