#!/usr/bin/env python3
"""
Script pour extraire les scores NDVI du fichier combined_scoring_optimized_sentinel1.json
et les convertir au format attendu par le système de scoring sur 20 points.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NDVIScoreExtractor:
    def __init__(self):
        self.source_file = "data/combined_scoring_optimized_sentinel1.json"
        self.output_file = "frontend/public/data/fincas_with_ndvi_scores.geojson"
        
    def load_ndvi_data(self) -> Dict[str, Dict]:
        """Charger les données NDVI du fichier source"""
        logger.info("📂 Chargement des données NDVI...")
        
        if not Path(self.source_file).exists():
            raise FileNotFoundError(f"Fichier source non trouvé: {self.source_file}")
        
        with open(self.source_file, 'r') as f:
            data = json.load(f)
        
        results = data.get('results', [])
        logger.info(f"✅ {len(results)} fincas trouvées")
        
        ndvi_data = {}
        for finca in results:
            finca_id = finca.get('finca_id')
            ndvi_component = finca.get('combined_scoring', {}).get('components', {}).get('ndvi', {})
            
            if ndvi_component:
                ndvi_data[finca_id] = {
                    'ndvi_score': ndvi_component.get('score'),
                    'ndvi_status': ndvi_component.get('status'),
                    'median_ndvi': ndvi_component.get('median_ndvi'),
                    'risk_category': ndvi_component.get('risk_category')
                }
        
        logger.info(f"✅ {len(ndvi_data)} données NDVI extraites")
        return ndvi_data
    
    def convert_ndvi_score_to_new_format(self, ndvi_score: int, ndvi_status: str) -> Dict[str, Any]:
        """Convertir l'ancien score NDVI au nouveau format (0-4 points)"""
        # Ancien système: score 0-100, status: "Faible", "Modérée", "Élevée"
        # Nouveau système: 0-4 points basé sur la variation
        
        if ndvi_score is None:
            return {"points": 0, "level": "Inconnu", "description": "Données non disponibles"}
        
        # Conversion basée sur le score et le status
        # Score 50 = "Modérée" = variation semi-active
        if ndvi_score == 50 and ndvi_status == "Modérée":
            return {"points": 2, "level": "Variation semi", "description": f"Végétation modérée (score: {ndvi_score})"}
        elif ndvi_score >= 70:  # Score élevé = faible variation = abandon
            return {"points": 0, "level": "Variation faible", "description": f"Végétation stable (score: {ndvi_score})"}
        elif ndvi_score >= 40:  # Score moyen = variation modérée
            return {"points": 2, "level": "Variation semi", "description": f"Végétation modérée (score: {ndvi_score})"}
        else:  # Score faible = forte variation = activité
            return {"points": 4, "level": "Variation forte", "description": f"Végétation variable (score: {ndvi_score})"}
    
    def integrate_ndvi_into_geojson(self, ndvi_data: Dict[str, Dict]) -> None:
        """Intégrer les scores NDVI dans le GeoJSON principal"""
        logger.info("🔗 Intégration des scores NDVI dans le GeoJSON...")
        
        # Charger le GeoJSON principal
        geojson_path = "frontend/public/data/fincas_with_all_data.geojson"
        if not Path(geojson_path).exists():
            logger.error(f"GeoJSON principal non trouvé: {geojson_path}")
            return
        
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        
        integrated_count = 0
        for feature in geojson_data.get('features', []):
            props = feature.get('properties', {})
            finca_id = props.get('id')
            
            if finca_id in ndvi_data:
                ndvi_info = ndvi_data[finca_id]
                
                # Convertir au nouveau format
                new_ndvi_score = self.convert_ndvi_score_to_new_format(
                    ndvi_info.get('ndvi_score'),
                    ndvi_info.get('ndvi_status')
                )
                
                # Mettre à jour les propriétés
                props['ndvi_median'] = ndvi_info.get('median_ndvi')
                props['ndvi_std_deviation'] = 0.1  # Valeur par défaut pour compatibilité
                props['ndvi_score_old'] = ndvi_info.get('ndvi_score')
                props['ndvi_status_old'] = ndvi_info.get('ndvi_status')
                
                # Mettre à jour le score total si il existe
                if 'total_score_criteria' in props:
                    props['total_score_criteria']['vegetation'] = new_ndvi_score
                    
                    # Recalculer le score total
                    total_points = sum([
                        props['total_score_criteria'].get('luminosite', {}).get('points', 0),
                        props['total_score_criteria'].get('radar', {}).get('points', 0),
                        new_ndvi_score.get('points', 0),
                        props['total_score_criteria'].get('creation_date', {}).get('points', 0),
                        props['total_score_criteria'].get('car_presence', {}).get('points', 0)
                    ])
                    
                    props['total_score_20'] = total_points
                    
                    # Mettre à jour la classification
                    if total_points > 10:
                        props['total_score_classification'] = "Active"
                    elif total_points >= 7:
                        props['total_score_classification'] = "Semi-active"
                    else:
                        props['total_score_classification'] = "Inactive"
                
                integrated_count += 1
        
        # Sauvegarder le GeoJSON mis à jour
        with open(self.output_file, 'w') as f:
            json.dump(geojson_data, f, indent=2)
        
        logger.info(f"✅ {integrated_count} scores NDVI intégrés")
        logger.info(f"💾 GeoJSON sauvegardé: {self.output_file}")
    
    def run_extraction(self):
        """Exécuter l'extraction complète"""
        logger.info("🚀 Démarrage de l'extraction des scores NDVI")
        
        try:
            # 1. Charger les données NDVI
            ndvi_data = self.load_ndvi_data()
            
            # 2. Intégrer dans le GeoJSON
            self.integrate_ndvi_into_geojson(ndvi_data)
            
            logger.info("✅ Extraction terminée avec succès!")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'extraction: {e}")
            raise

if __name__ == "__main__":
    extractor = NDVIScoreExtractor()
    extractor.run_extraction()
