#!/usr/bin/env python3
"""
🚗 Generate Vehicle History - Génère l'historique des véhicules pour le scoring
Simule 12 détections sur 6 mois pour tester le système de scoring d'abandon
"""

import os
import sys
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.scoring.abandonment_scorer import AbandonmentScorer  # noqa: E402

GEOJSON = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
OUT_DIR = ROOT / 'data' / 'test_results' / 'vehicle_history'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_vehicle_history_for_finca(finca_id: str, abandonment_level: str = "random") -> List[Dict]:
    """
    Génère un historique de véhicules pour une finca
    
    Args:
        finca_id: ID de la finca
        abandonment_level: "abandoned", "active", "random"
    
    Returns:
        Liste de 12 détections sur 6 mois
    """
    # Dates sur 6 mois (2 par mois)
    base_date = datetime(2024, 1, 1)
    dates = []
    for month in range(6):
        for day in [1, 15]:
            dates.append(base_date + timedelta(days=month*30 + day - 1))
    
    history = []
    
    if abandonment_level == "abandoned":
        # Aucun véhicule détecté
        for date in dates:
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "vehicle_detected": False,
                "total_count": 0,
                "counts_by_class": {},
                "finca_id": finca_id
            })
    
    elif abandonment_level == "active":
        # Beaucoup de véhicules (8-10/12 images)
        num_with_vehicles = random.randint(8, 10)
        vehicle_dates = random.sample(dates, num_with_vehicles)
        
        for date in dates:
            has_vehicles = date in vehicle_dates
            if has_vehicles:
                count = random.randint(1, 3)
                classes = {"car": count} if random.random() > 0.3 else {"car": count-1, "motorcycle": 1}
            else:
                count = 0
                classes = {}
            
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "vehicle_detected": has_vehicles,
                "total_count": count,
                "counts_by_class": classes,
                "finca_id": finca_id
            })
    
    else:  # random
        # Distribution aléatoire
        for date in dates:
            has_vehicles = random.random() > 0.6  # 40% chance d'avoir des véhicules
            if has_vehicles:
                count = random.randint(1, 2)
                classes = {"car": count}
            else:
                count = 0
                classes = {}
            
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "vehicle_detected": has_vehicles,
                "total_count": count,
                "counts_by_class": classes,
                "finca_id": finca_id
            })
    
    return history


def generate_ndvi_data_for_finca(abandonment_level: str = "random") -> Dict:
    """
    Génère des données NDVI pour une finca
    
    Args:
        abandonment_level: "abandoned", "active", "random"
    
    Returns:
        Données NDVI simulées
    """
    if abandonment_level == "abandoned":
        # Faible variation NDVI
        variation = random.uniform(3.0, 8.0)
        mean_ndvi = random.uniform(0.25, 0.40)
    elif abandonment_level == "active":
        # Forte variation NDVI
        variation = random.uniform(25.0, 40.0)
        mean_ndvi = random.uniform(0.45, 0.65)
    else:  # random
        variation = random.uniform(5.0, 35.0)
        mean_ndvi = random.uniform(0.30, 0.60)
    
    return {
        "variation_percent": variation,
        "mean_ndvi": mean_ndvi,
        "min_ndvi": mean_ndvi * 0.8,
        "max_ndvi": mean_ndvi * 1.2
    }


def main() -> int:
    """Génère l'historique des véhicules pour les top 30 fincas"""
    
    # Charger les fincas
    with open(GEOJSON, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    
    def id_num(fid: str) -> int:
        try:
            return int(fid.split('_')[-1])
        except Exception:
            return 10**9
    
    # Prendre les top 30
    top = [ft for ft in features if ft.get('properties', {}).get('id', '').startswith('finca_')]
    top.sort(key=lambda ft: id_num(ft['properties']['id']))
    top = top[:30]
    
    scorer = AbandonmentScorer()
    results = []
    
    print(f"🚗 Génération de l'historique des véhicules pour {len(top)} fincas...")
    
    for i, ft in enumerate(top, 1):
        props = ft['properties']
        fid = props['id']
        
        # Déterminer le niveau d'abandon basé sur le score existant
        existing_score = props.get('abandonment_score', 0)
        if existing_score > 70:
            abandonment_level = "abandoned"
        elif existing_score < 30:
            abandonment_level = "active"
        else:
            abandonment_level = "random"
        
        # Générer l'historique des véhicules
        vehicle_history = generate_vehicle_history_for_finca(fid, abandonment_level)
        
        # Générer les données NDVI
        ndvi_data = generate_ndvi_data_for_finca(abandonment_level)
        
        # Calculer le score combiné
        combined_score = scorer.calculate_combined_score(vehicle_history, ndvi_data)
        
        # Sauvegarder l'historique individuel
        history_file = OUT_DIR / f"{fid}_vehicle_history.json"
        with open(history_file, 'w') as f:
            json.dump({
                "finca_id": fid,
                "vehicle_history": vehicle_history,
                "ndvi_data": ndvi_data,
                "scoring_result": combined_score
            }, f, indent=2)
        
        results.append({
            "finca_id": fid,
            "abandonment_level": abandonment_level,
            "existing_score": existing_score,
            "vehicle_history": vehicle_history,
            "ndvi_data": ndvi_data,
            "scoring_result": combined_score
        })
        
        print(f"{i:2d}/30: {fid} - {abandonment_level} - Score: {combined_score['total_score']} ({combined_score['abandonment_level']})")
    
    # Sauvegarder le résumé
    summary_file = OUT_DIR / "vehicle_history_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "total_fincas": len(results),
            "results": results
        }, f, indent=2)
    
    # Statistiques
    levels = [r['scoring_result']['abandonment_level'] for r in results]
    scores = [r['scoring_result']['total_score'] for r in results]
    
    print(f"\n📊 Statistiques:")
    print(f"Fincas générées: {len(results)}")
    print(f"Scores moyens: {sum(scores)/len(scores):.1f}")
    print(f"Distribution des niveaux:")
    for level in ["high", "medium", "low", "none"]:
        count = levels.count(level)
        print(f"  {level}: {count} fincas ({count/len(levels)*100:.1f}%)")
    
    print(f"\n💾 Fichiers sauvegardés:")
    print(f"  Résumé: {summary_file}")
    print(f"  Historiques individuels: {OUT_DIR}/*_vehicle_history.json")
    
    return 0


if __name__ == "__main__":
    exit(main())
