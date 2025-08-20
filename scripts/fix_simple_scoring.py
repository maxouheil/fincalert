#!/usr/bin/env python3
"""
🔧 Correction du Score Global Simplifié (/15)
Calcule le score global en combinant Radar + Luminosité + Végétation
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_geojson_data():
    """Charge les données GeoJSON actuelles"""
    geojson_file = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    
    if not geojson_file.exists():
        raise FileNotFoundError(f"Fichier GeoJSON non trouvé: {geojson_file}")
    
    with open(geojson_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 GeoJSON chargé: {len(data['features'])} fincas")
    return data


def calculate_simple_score(finca_props):
    """Calcule le score global simplifié (/15) basé sur les 3 critères"""
    
    # 1. Score Radar (basé sur l'activité Sentinel-1)
    radar_score = 1  # Par défaut faible
    if finca_props.get('activity_status') == 'active':
        radar_score = 5  # Fort
    elif finca_props.get('activity_status') == 'semi-active':
        radar_score = 3  # Moyen
    
    # 2. Score Luminosité (données VIIRS intégrées)
    luminosite_score = finca_props.get('luminosity_score', 1)  # Utilise les données intégrées
    
    # 3. Score Végétation (basé sur CV NDVI)
    vegetation_score = 1  # Par défaut faible
    cv_percent = finca_props.get('std_deviation', 0) * 100  # Convertir en pourcentage
    
    if cv_percent >= 25:
        vegetation_score = 5  # Fort (CV ≥ 25%)
    elif cv_percent >= 12:
        vegetation_score = 3  # Moyen (CV 12-25%)
    
    # Score total (/15)
    total_score = radar_score + luminosite_score + vegetation_score
    
    # Classification
    if total_score >= 10:
        classification = 'Active'
    elif total_score >= 5:
        classification = 'Moderate'
    else:
        classification = 'Inactive'
    
    return {
        'total_score': total_score,
        'radar_score': radar_score,
        'luminosite_score': luminosite_score,
        'vegetation_score': vegetation_score,
        'classification': classification,
        'cv_percent': cv_percent
    }


def update_geojson_with_simple_scores(geojson_data):
    """Met à jour le GeoJSON avec les scores globaux simplifiés"""
    updated_count = 0
    missing_luminosity = 0
    missing_activity = 0
    
    for feature in geojson_data['features']:
        props = feature.get('properties', {})
        finca_id = props.get('id')
        
        if finca_id:
            # Calculer le score global simplifié
            score_data = calculate_simple_score(props)
            
            # Mettre à jour les propriétés
            props['simple_score'] = score_data['total_score']
            props['simple_classification'] = score_data['classification']
            props['radar_score'] = score_data['radar_score']
            props['luminosite_score'] = score_data['luminosite_score']
            props['vegetation_score'] = score_data['vegetation_score']
            props['cv_percent'] = score_data['cv_percent']
            
            # Compter les données manquantes
            if not props.get('luminosity_score'):
                missing_luminosity += 1
            if not props.get('activity_status'):
                missing_activity += 1
            
            updated_count += 1
    
    print(f"✅ {updated_count} fincas mises à jour avec scores globaux")
    if missing_luminosity > 0:
        print(f"⚠️  {missing_luminosity} fincas sans données de luminosité")
    if missing_activity > 0:
        print(f"⚠️  {missing_activity} fincas sans données d'activité")
    
    return geojson_data


def create_score_summary(geojson_data):
    """Crée un résumé des scores globaux"""
    scores = []
    classifications = []
    
    for feature in geojson_data['features']:
        props = feature.get('properties', {})
        if props.get('simple_score'):
            scores.append(props['simple_score'])
            classifications.append(props.get('simple_classification', 'Unknown'))
    
    if not scores:
        return None
    
    # Statistiques des scores
    score_stats = {
        'total_fincas': len(scores),
        'mean_score': sum(scores) / len(scores),
        'min_score': min(scores),
        'max_score': max(scores),
        'score_distribution': {
            '1-4': sum(1 for s in scores if 1 <= s <= 4),
            '5-9': sum(1 for s in scores if 5 <= s <= 9),
            '10-15': sum(1 for s in scores if 10 <= s <= 15)
        }
    }
    
    # Statistiques des classifications
    class_counts = {}
    for cls in classifications:
        class_counts[cls] = class_counts.get(cls, 0) + 1
    
    classification_stats = {
        'total_fincas': len(classifications),
        'distribution': class_counts
    }
    
    return {
        'score_statistics': score_stats,
        'classification_statistics': classification_stats
    }


def save_updated_geojson(geojson_data, backup=True):
    """Sauvegarde le GeoJSON mis à jour"""
    geojson_file = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    
    # Créer une sauvegarde si demandé
    if backup:
        backup_file = geojson_file.parent / f"fincas_backup_simple_scoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"
        with open(geojson_file, 'r', encoding='utf-8') as f:
            original_data = f.read()
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(original_data)
        print(f"💾 Sauvegarde créée: {backup_file.name}")
    
    # Sauvegarder le fichier mis à jour
    with open(geojson_file, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ GeoJSON mis à jour: {geojson_file}")


def main():
    """Fonction principale"""
    print("🔧 CORRECTION DU SCORE GLOBAL SIMPLIFIÉ (/15)")
    print("=" * 50)
    print("📊 Calcul du score global : Radar + Luminosité + Végétation")
    print("🎯 Classification : Active (≥10), Moderate (5-9), Inactive (<5)")
    print("=" * 50)
    
    try:
        # 1. Charger les données GeoJSON
        print("📂 Chargement des données GeoJSON...")
        geojson_data = load_geojson_data()
        
        # 2. Calculer et mettre à jour les scores globaux
        print("🧮 Calcul des scores globaux simplifiés...")
        updated_geojson = update_geojson_with_simple_scores(geojson_data)
        
        # 3. Créer le résumé des scores
        print("📈 Création du résumé des scores...")
        summary = create_score_summary(updated_geojson)
        
        # 4. Sauvegarder le GeoJSON mis à jour
        print("💾 Sauvegarde du GeoJSON...")
        save_updated_geojson(updated_geojson)
        
        # 5. Afficher le résumé
        if summary:
            print("\n📊 RÉSUMÉ DES SCORES GLOBAUX:")
            print("=" * 40)
            
            score_stats = summary['score_statistics']
            print(f"   📈 Total fincas: {score_stats['total_fincas']}")
            print(f"   📊 Score moyen: {score_stats['mean_score']:.1f}/15")
            print(f"   📈 Score min/max: {score_stats['min_score']}/{score_stats['max_score']}")
            print("   📊 Distribution des scores:")
            for range_key, count in score_stats['score_distribution'].items():
                percentage = count / score_stats['total_fincas'] * 100
                print(f"      {range_key}: {count} fincas ({percentage:.1f}%)")
            
            class_stats = summary['classification_statistics']
            print("   🎯 Distribution des classifications:")
            for cls, count in class_stats['distribution'].items():
                percentage = count / class_stats['total_fincas'] * 100
                print(f"      {cls}: {count} fincas ({percentage:.1f}%)")
        
        print("\n🎉 CORRECTION TERMINÉE AVEC SUCCÈS!")
        print("💡 Les points sur la carte devraient maintenant afficher les bonnes couleurs:")
        print("   🟢 Vert: Score ≥ 10 (Active)")
        print("   🟠 Orange: Score 5-9 (Moderate)")
        print("   🔴 Rouge: Score < 5 (Inactive)")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la correction: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
