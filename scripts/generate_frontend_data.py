#!/usr/bin/env python3
"""
Générer un fichier JSON enrichi pour le frontend
Combine les données GeoJSON existantes avec les scores d'abandon calculés
"""
import json
import csv
from pathlib import Path

def load_geojson(geojson_path):
    """Charger les données GeoJSON existantes"""
    with open(geojson_path, 'r') as f:
        return json.load(f)

def load_abandon_scores(json_path):
    """Charger les scores d'abandon depuis le JSON complet"""
    scores = {}
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Extraire les données de chaque finca
    for finca in data.get('fincas', []):
        if finca.get('status') == 'success':
            finca_id = finca['finca_id']
            scores[finca_id] = {
                'abandon_score': finca['abandon_score'],
                'activity_status': finca['activity_status'],
                'std_deviation': finca['std_deviation'],
                'median_ndvi': finca['median_ndvi'],
                'valid_periods': finca['valid_periods'],
                'processing_duration_s': finca['processing_duration_s'],
                'ndvi_timeseries': finca.get('ndvi_timeseries', [])
            }
    return scores

def merge_data(geojson_data, abandon_scores):
    """Fusionner les données GeoJSON avec les scores d'abandon"""
    for feature in geojson_data['features']:
        finca_id = feature['properties']['id']
        
        # Ajouter les scores d'abandon si disponibles
        if finca_id in abandon_scores:
            abandon_data = abandon_scores[finca_id]
            feature['properties'].update(abandon_data)
        else:
            # Valeurs par défaut si pas de données d'abandon
            feature['properties'].update({
                'abandon_score': 50.0,  # Score neutre
                'activity_status': 'unknown',
                'std_deviation': 0.0,
                'median_ndvi': 0.0,
                'valid_periods': 0,
                'processing_duration_s': 0.0,
                'ndvi_timeseries': []
            })
    
    return geojson_data

def main():
    # Chemins des fichiers
    base_dir = Path(__file__).parent.parent
    geojson_path = base_dir / "frontend" / "public" / "data" / "fincas_extreme_west.geojson"
    json_path = base_dir / "data" / "abandon_analysis_FULL" / "fincas_abandon_analysis_REALISTIC_20250809_140234.json"
    output_path = base_dir / "frontend" / "public" / "data" / "fincas_with_abandon_scores.geojson"
    
    print("🔄 Génération des données enrichies pour le frontend...")
    
    # Charger les données
    print(f"📂 Chargement GeoJSON: {geojson_path}")
    geojson_data = load_geojson(geojson_path)
    
    print(f"📊 Chargement scores d'abandon: {json_path}")
    abandon_scores = load_abandon_scores(json_path)
    
    print(f"✅ Scores chargés pour {len(abandon_scores)} fincas")
    print(f"✅ GeoJSON avec {len(geojson_data['features'])} fincas")
    
    # Fusionner
    enriched_data = merge_data(geojson_data, abandon_scores)
    
    # Sauvegarder
    with open(output_path, 'w') as f:
        json.dump(enriched_data, f, indent=2)
    
    print(f"💾 Données enrichies sauvegardées: {output_path}")
    
    # Statistiques
    matched = sum(1 for f in enriched_data['features'] if f['properties']['abandon_score'] != 50.0)
    print(f"📈 Statistiques: {matched}/{len(enriched_data['features'])} fincas avec scores d'abandon")
    
    # Distribution des scores
    scores = [f['properties']['abandon_score'] for f in enriched_data['features']]
    high_risk = sum(1 for s in scores if s >= 70)
    medium_risk = sum(1 for s in scores if 40 <= s < 70)
    low_risk = sum(1 for s in scores if s < 40)
    
    print(f"🚨 Distribution des risques:")
    print(f"   🔴 Risque élevé (≥70): {high_risk}")
    print(f"   🟡 Risque moyen (40-69): {medium_risk}")
    print(f"   🟢 Risque faible (<40): {low_risk}")
    
    print("🎯 Prêt pour le frontend !")

if __name__ == "__main__":
    main()
