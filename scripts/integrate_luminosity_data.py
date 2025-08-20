#!/usr/bin/env python3
"""
🌙 Intégration des données de luminosité dans le système Fincalert
Met à jour le frontend et le backend avec les nouvelles données VIIRS
"""

import os
import sys
import json
import csv
from datetime import datetime
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_luminosity_data():
    """Charge les données de luminosité depuis le fichier CSV"""
    csv_file = ROOT / 'data' / 'luminosity_analysis' / 'luminosity_all631_real_20250820_150136.csv'
    
    if not csv_file.exists():
        raise FileNotFoundError(f"Fichier de données de luminosité non trouvé: {csv_file}")
    
    luminosity_data = {}
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['status'] == 'success':
                finca_id = row['finca_id']
                luminosity_data[finca_id] = {
                    'score': int(row['score']),
                    'mean_luminosity': float(row['mean_luminosity']),
                    'luminosity_level': row['luminosity_level'],
                    'active_months': int(row['active_months']),
                    'total_months': int(row['total_months']),
                    'trend': float(row['trend']),
                    'seasonal_pattern': row['seasonal_pattern'],
                    'reason': row['reason'],
                    'cached': row['cached'].lower() == 'true'
                }
    
    print(f"📊 Données de luminosité chargées: {len(luminosity_data)} fincas")
    return luminosity_data


def load_current_geojson():
    """Charge le GeoJSON actuel des fincas"""
    geojson_file = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    
    if not geojson_file.exists():
        raise FileNotFoundError(f"Fichier GeoJSON non trouvé: {geojson_file}")
    
    with open(geojson_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 GeoJSON chargé: {len(data['features'])} fincas")
    return data


def update_geojson_with_luminosity(geojson_data, luminosity_data):
    """Met à jour le GeoJSON avec les données de luminosité"""
    updated_count = 0
    missing_count = 0
    
    for feature in geojson_data['features']:
        props = feature.get('properties', {})
        finca_id = props.get('id')
        
        if finca_id and finca_id in luminosity_data:
            # Ajouter les données de luminosité
            lum_data = luminosity_data[finca_id]
            props['luminosity_score'] = lum_data['score']
            props['luminosity_mean'] = lum_data['mean_luminosity']
            props['luminosity_level'] = lum_data['luminosity_level']
            props['luminosity_reason'] = lum_data['reason']
            props['luminosity_trend'] = lum_data['trend']
            props['luminosity_seasonal'] = lum_data['seasonal_pattern']
            
            # Mettre à jour le score simple si nécessaire
            if 'simple_score' in props:
                # Le score simple est déjà calculé, on peut ajouter la luminosité comme info
                props['simple_score_luminosity'] = lum_data['score']
            else:
                # Créer un score simple basé sur la luminosité seulement
                props['simple_score'] = lum_data['score']
            
            updated_count += 1
        else:
            missing_count += 1
    
    print(f"✅ GeoJSON mis à jour: {updated_count} fincas avec données de luminosité")
    if missing_count > 0:
        print(f"⚠️  {missing_count} fincas sans données de luminosité")
    
    return geojson_data


def create_luminosity_summary(luminosity_data):
    """Crée un résumé des données de luminosité"""
    scores = [data['score'] for data in luminosity_data.values()]
    luminosities = [data['mean_luminosity'] for data in luminosity_data.values()]
    levels = [data['luminosity_level'] for data in luminosity_data.values()]
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_fincas": len(luminosity_data),
        "score_statistics": {
            "mean": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "distribution": {
                str(i): sum(1 for s in scores if s == i) 
                for i in range(6)
            }
        },
        "luminosity_statistics": {
            "mean": sum(luminosities) / len(luminosities),
            "min": min(luminosities),
            "max": max(luminosities),
            "level_distribution": {
                level: sum(1 for l in levels if l == level)
                for level in set(levels)
            }
        },
        "data_source": "VIIRS DNB (6 mois)",
        "analysis_date": "2025-08-20"
    }
    
    return summary


def save_updated_geojson(geojson_data, backup=True):
    """Sauvegarde le GeoJSON mis à jour"""
    geojson_file = ROOT / 'frontend' / 'public' / 'data' / 'fincas_with_abandon_scores.geojson'
    
    # Créer une sauvegarde si demandé
    if backup:
        backup_file = geojson_file.parent / f"fincas_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"
        with open(geojson_file, 'r', encoding='utf-8') as f:
            original_data = f.read()
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write(original_data)
        print(f"💾 Sauvegarde créée: {backup_file.name}")
    
    # Sauvegarder le fichier mis à jour
    with open(geojson_file, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ GeoJSON mis à jour: {geojson_file}")


def create_luminosity_api_data(luminosity_data):
    """Crée les données pour l'API backend"""
    api_data = {}
    
    for finca_id, data in luminosity_data.items():
        api_data[finca_id] = {
            "finca_id": finca_id,
            "luminosity_analysis": {
                "score": data['score'],
                "mean_luminosity": data['mean_luminosity'],
                "luminosity_level": data['luminosity_level'],
                "reason": data['reason'],
                "trend": data['trend'],
                "seasonal_pattern": data['seasonal_pattern'],
                "active_months": data['active_months'],
                "total_months": data['total_months'],
                "cached": data['cached']
            },
            "analysis_date": "2025-08-20",
            "data_source": "VIIRS DNB"
        }
    
    return api_data


def save_api_data(api_data):
    """Sauvegarde les données pour l'API"""
    api_file = ROOT / 'backend' / 'data' / 'luminosity_api_data.json'
    api_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(api_file, 'w', encoding='utf-8') as f:
        json.dump(api_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Données API sauvegardées: {api_file}")


def update_backend_api():
    """Met à jour l'API backend pour inclure les données de luminosité"""
    api_file = ROOT / 'backend' / 'api' / 'main.py'
    
    if not api_file.exists():
        print("⚠️  Fichier API backend non trouvé")
        return
    
    # Lire le fichier actuel
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier si l'endpoint de luminosité existe déjà
    if '/api/luminosity/{finca_id}' in content:
        print("ℹ️  Endpoint de luminosité déjà présent dans l'API")
        return
    
    # Ajouter l'endpoint de luminosité
    luminosity_endpoint = '''
@app.get("/api/luminosity/{finca_id}")
async def get_finca_luminosity(finca_id: str):
    """Récupère les données de luminosité d'une finca"""
    try:
        # Charger les données de luminosité
        api_file = Path(__file__).parent.parent / 'data' / 'luminosity_api_data.json'
        if not api_file.exists():
            raise HTTPException(status_code=404, detail="Données de luminosité non disponibles")
        
        with open(api_file, 'r', encoding='utf-8') as f:
            luminosity_data = json.load(f)
        
        if finca_id not in luminosity_data:
            raise HTTPException(status_code=404, detail=f"Finca {finca_id} non trouvée")
        
        return {
            "finca_id": finca_id,
            "luminosity_data": luminosity_data[finca_id],
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
'''
    
    # Trouver le bon endroit pour insérer (après les autres endpoints)
    if 'from pathlib import Path' not in content:
        # Ajouter l'import si nécessaire
        content = content.replace('import json', 'import json\nfrom pathlib import Path')
    
    # Insérer l'endpoint avant la fin du fichier
    if 'if __name__ == "__main__":' in content:
        content = content.replace('if __name__ == "__main__":', luminosity_endpoint + '\n\nif __name__ == "__main__":')
    else:
        content += luminosity_endpoint
    
    # Sauvegarder le fichier mis à jour
    with open(api_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ API backend mise à jour: {api_file}")


def update_frontend_components():
    """Met à jour les composants frontend pour afficher les données de luminosité"""
    popup_file = ROOT / 'frontend' / 'src' / 'components' / 'NewPopup.tsx'
    
    if not popup_file.exists():
        print("⚠️  Fichier popup frontend non trouvé")
        return
    
    # Lire le fichier actuel
    with open(popup_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Vérifier si les données de luminosité sont déjà affichées
    if 'luminosity_score' in content:
        print("ℹ️  Données de luminosité déjà présentes dans le popup")
        return
    
    # Ajouter l'affichage des données de luminosité
    luminosity_section = '''
            {/* Section Luminosité Nocturne */}
            {fincaData.luminosity_score && (
              <div className="popup-section">
                <h4>🌙 Luminosité Nocturne</h4>
                <div className="score-item">
                  <span className="score-label">Score:</span>
                  <span className={`score-value score-${fincaData.luminosity_score}`}>
                    {fincaData.luminosity_score}/5
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Niveau:</span>
                  <span className="detail-value">{fincaData.luminosity_level}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Luminosité moyenne:</span>
                  <span className="detail-value">{fincaData.luminosity_mean?.toFixed(3)}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Raison:</span>
                  <span className="detail-value">{fincaData.luminosity_reason}</span>
                </div>
              </div>
            )}
'''
    
    # Trouver le bon endroit pour insérer (après les autres sections)
    if 'popup-section' in content:
        # Insérer après la dernière section
        sections = content.split('</div>')
        for i, section in enumerate(sections):
            if 'popup-section' in section and 'h4>' in section:
                # Insérer après cette section
                sections[i] = section + luminosity_section
                break
        content = '</div>'.join(sections)
    else:
        # Ajouter à la fin du contenu du popup
        content = content.replace('</div>', luminosity_section + '\n          </div>', 1)
    
    # Sauvegarder le fichier mis à jour
    with open(popup_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Popup frontend mis à jour: {popup_file}")


def main():
    """Fonction principale d'intégration"""
    print("🌙 INTÉGRATION DES DONNÉES DE LUMINOSITÉ DANS FINCALTER")
    print("=" * 60)
    
    try:
        # 1. Charger les données de luminosité
        print("📊 Chargement des données de luminosité...")
        luminosity_data = load_luminosity_data()
        
        # 2. Créer le résumé
        print("📈 Création du résumé...")
        summary = create_luminosity_summary(luminosity_data)
        
        # 3. Charger et mettre à jour le GeoJSON
        print("🗺️  Mise à jour du GeoJSON...")
        geojson_data = load_current_geojson()
        updated_geojson = update_geojson_with_luminosity(geojson_data, luminosity_data)
        
        # 4. Sauvegarder le GeoJSON mis à jour
        print("💾 Sauvegarde du GeoJSON...")
        save_updated_geojson(updated_geojson)
        
        # 5. Créer les données API
        print("🔌 Création des données API...")
        api_data = create_luminosity_api_data(luminosity_data)
        save_api_data(api_data)
        
        # 6. Mettre à jour l'API backend
        print("⚙️  Mise à jour de l'API backend...")
        update_backend_api()
        
        # 7. Mettre à jour le frontend
        print("🎨 Mise à jour du frontend...")
        update_frontend_components()
        
        # 8. Afficher le résumé final
        print("\n📊 RÉSUMÉ DE L'INTÉGRATION:")
        print("=" * 40)
        print(f"   📈 Fincas avec données: {len(luminosity_data)}")
        print(f"   📊 Score moyen: {summary['score_statistics']['mean']:.1f}/5")
        print(f"   💡 Luminosité moyenne: {summary['luminosity_statistics']['mean']:.3f}")
        print(f"   📁 Fichiers mis à jour:")
        print(f"      - GeoJSON frontend")
        print(f"      - API backend")
        print(f"      - Composants frontend")
        print(f"      - Données API")
        
        print("\n🎉 INTÉGRATION TERMINÉE AVEC SUCCÈS!")
        print("💡 Les données de luminosité sont maintenant disponibles dans:")
        print("   - Frontend: Popup des fincas")
        print("   - Backend: /api/luminosity/{finca_id}")
        print("   - GeoJSON: Propriétés des fincas")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de l'intégration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
