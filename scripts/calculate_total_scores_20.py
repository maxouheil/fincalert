#!/usr/bin/env python3
"""
Calculateur de scores totaux sur 20 points avec intégration des données NDVI
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TotalScoreCalculator20:
    def __init__(self):
        self.geojson_path = "frontend/public/data/fincas_with_ndvi_scores.geojson"
        self.output_path = "frontend/public/data/fincas_total_scores_20.geojson"
        
        # Critères de scoring (20 points max)
        self.criteria = {
            "car_presence": {
                "name": "Présence de Voitures",
                "max_points": 5,
                "description": "Activité humaine récente"
            },
            "creation_date": {
                "name": "Date de Création Cadastrale",
                "max_points": 5,
                "description": "Ancienneté de la finca"
            },
            "vegetation": {
                "name": "Entretien Végétation (NDVI)",
                "max_points": 4,
                "description": "Variabilité de la végétation"
            },
            "radar": {
                "name": "Activité Radar (Sentinel-1)",
                "max_points": 3,
                "description": "Activité radar détectée"
            },
            "luminosite": {
                "name": "Luminosité Nocturne (VIIRS)",
                "max_points": 3,
                "description": "Activité nocturne"
            }
        }
        
        logger.info("🎯 Initialisation du calculateur de scores totaux sur 20")
        logger.info(f"📂 GeoJSON source: {self.geojson_path}")
        logger.info(f"💾 Fichier de sortie: {self.output_path}")
        logger.info(f"📊 Total critères: 5 (20 points max)")
    
    def load_fincas_data(self) -> Dict:
        """Charger les données des fincas"""
        logger.info("📂 Chargement des données fincas...")
        
        if not Path(self.geojson_path).exists():
            raise FileNotFoundError(f"Fichier GeoJSON non trouvé: {self.geojson_path}")
        
        with open(self.geojson_path, 'r') as f:
            data = json.load(f)
        
        logger.info(f"✅ {len(data.get('features', []))} fincas chargées")
        return data
    
    def calculate_luminosite_score(self, viirs_mean_luminosity: Optional[float]) -> Dict:
        """Calculer le score de luminosité nocturne (0-3 points)"""
        if viirs_mean_luminosity is None:
            return {"points": 0, "level": "Inconnu", "description": "Données non disponibles"}
        
        # Nouveaux seuils pour 3 points avec progression équilibrée
        if viirs_mean_luminosity <= 0.700:
            return {"points": 1, "level": "Faible", "description": f"Luminosité faible ({viirs_mean_luminosity:.3f})"}
        elif viirs_mean_luminosity <= 1.209:
            return {"points": 2, "level": "Moyen", "description": f"Luminosité modérée ({viirs_mean_luminosity:.3f})"}
        else:
            return {"points": 3, "level": "Fort", "description": f"Luminosité élevée ({viirs_mean_luminosity:.3f})"}
    
    def calculate_radar_score(self, sentinel1_vv_db: Optional[float]) -> Dict:
        """Calculer le score d'activité radar (0-3 points)"""
        if sentinel1_vv_db is None:
            return {"points": 0, "level": "Inconnu", "description": "Données non disponibles"}
        
        # Nouveaux seuils pour 3 points avec progression équilibrée
        if sentinel1_vv_db <= -11.404:
            return {"points": 1, "level": "Faible", "description": f"Activité radar faible ({sentinel1_vv_db:.2f} dB)"}
        elif sentinel1_vv_db <= -10.066:
            return {"points": 2, "level": "Moyen", "description": f"Activité radar modérée ({sentinel1_vv_db:.2f} dB)"}
        else:
            return {"points": 3, "level": "Fort", "description": f"Activité radar élevée ({sentinel1_vv_db:.2f} dB)"}
    
    def calculate_vegetation_score_from_ndvi_data(self, ndvi_score_old: Optional[int], ndvi_status_old: Optional[str]) -> Dict:
        """Calculer le score d'entretien végétation à partir des données NDVI existantes (0-4 points)"""
        if ndvi_score_old is None or ndvi_status_old is None:
            return {"points": 0, "level": "Inconnu", "description": "Données non disponibles"}
        
        # Conversion basée sur les données NDVI existantes
        if ndvi_score_old == 50 and ndvi_status_old == "Modérée":
            return {"points": 2, "level": "Variation semi", "description": f"Végétation modérée (score: {ndvi_score_old})"}
        elif ndvi_score_old >= 70:  # Score élevé = faible variation = abandon
            return {"points": 0, "level": "Variation faible", "description": f"Végétation stable (score: {ndvi_score_old})"}
        elif ndvi_score_old >= 40:  # Score moyen = variation modérée
            return {"points": 2, "level": "Variation semi", "description": f"Végétation modérée (score: {ndvi_score_old})"}
        else:  # Score faible = forte variation = activité
            return {"points": 4, "level": "Variation forte", "description": f"Végétation variable (score: {ndvi_score_old})"}
    
    def calculate_creation_date_score(self, creation_date: Optional[str]) -> Dict:
        """Calculer le score de date de création (0-5 points) - NOUVEAU BARÈME"""
        if creation_date is None:
            return {"points": 0, "level": "Inconnu", "description": "Date de création non disponible"}
        
        try:
            date_obj = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
            current_date = datetime.now()
            age_years = (current_date - date_obj).days / 365.25
            
            # NOUVEAU BARÈME sur 5 points
            if age_years > 20:
                return {"points": 0, "level": "Très ancien", "description": f"Finca très ancienne ({age_years:.0f} ans)"}
            elif age_years > 15:
                return {"points": 1, "level": "Ancien", "description": f"Finca ancienne ({age_years:.0f} ans)"}
            elif age_years > 10:
                return {"points": 2, "level": "Moyen", "description": f"Finca d'âge moyen ({age_years:.0f} ans)"}
            elif age_years > 5:
                return {"points": 3, "level": "Récent", "description": f"Finca récente ({age_years:.0f} ans)"}
            else:
                return {"points": 5, "level": "Très récent", "description": f"Finca très récente ({age_years:.0f} ans)"}
        except Exception as e:
            return {"points": 0, "level": "Erreur", "description": f"Erreur de calcul: {str(e)}"}
    
    def calculate_car_presence_score(self, total_vehicles: int) -> Dict:
        """Calculer le score de présence de voitures (0-5 points) - inchangé"""
        if total_vehicles == 0:
            return {"points": 0, "level": "Aucune", "description": "Aucun véhicule détecté"}
        elif total_vehicles <= 2:
            return {"points": 3, "level": "Modérée", "description": f"Activité modérée ({total_vehicles} véhicules)"}
        else:
            return {"points": 5, "level": "Élevée", "description": f"Activité élevée ({total_vehicles} véhicules)"}
    
    def calculate_total_score(self, finca_props: Dict) -> Dict:
        """Calculer le score total sur 20 points"""
        # Récupérer les données brutes
        viirs_luminosity = finca_props.get('viirs_mean_luminosity')
        sentinel1_vv = finca_props.get('sentinel1_vv_db')
        ndvi_score_old = finca_props.get('ndvi_score_old')
        ndvi_status_old = finca_props.get('ndvi_status_old')
        creation_date = finca_props.get('creation_date')
        total_vehicles = finca_props.get('total_vehicles_detected', 0)
        
        # Calculer chaque critère
        luminosite = self.calculate_luminosite_score(viirs_luminosity)
        radar = self.calculate_radar_score(sentinel1_vv)
        vegetation = self.calculate_vegetation_score_from_ndvi_data(ndvi_score_old, ndvi_status_old)
        creation = self.calculate_creation_date_score(creation_date)
        car_presence = self.calculate_car_presence_score(total_vehicles)
        
        # Calculer le total
        total_points = (
            luminosite["points"] + 
            radar["points"] + 
            vegetation["points"] + 
            creation["points"] + 
            car_presence["points"]
        )
        
        # Classification finale avec nouveaux barèmes sur 20 points
        if total_points > 10:
            classification = "Active"
            level_description = "Finca très active"
        elif total_points >= 7:
            classification = "Semi-active"
            level_description = "Finca moyennement active"
        else:
            classification = "Inactive"
            level_description = "Finca inactive/abandonnée"
        
        return {
            "total_score_20": total_points,
            "max_possible": 20,
            "classification": classification,
            "level_description": level_description,
            "total_score_criteria": {
                "luminosite": luminosite,
                "radar": radar,
                "vegetation": vegetation,
                "creation_date": creation,
                "car_presence": car_presence
            }
        }
    
    def process_all_fincas(self, fincas_data: Dict) -> Dict:
        """Traiter toutes les fincas et calculer les scores"""
        logger.info("🔄 Calcul des scores totaux pour toutes les fincas...")
        
        features = fincas_data.get('features', [])
        processed_count = 0
        
        for feature in features:
            props = feature.get('properties', {})
            
            # Calculer le score total
            total_score_data = self.calculate_total_score(props)
            
            # Mettre à jour les propriétés
            props.update({
                'total_score_20': total_score_data['total_score_20'],
                'total_score_classification': total_score_data['classification'],
                'total_score_criteria': total_score_data['total_score_criteria']
            })
            
            processed_count += 1
        
        logger.info(f"✅ {processed_count} fincas traitées")
        return fincas_data
    
    def generate_summary_report(self, fincas_data: Dict) -> Dict:
        """Générer un rapport de synthèse"""
        logger.info("📊 Génération du rapport de synthèse...")
        
        features = fincas_data.get('features', [])
        
        # Statistiques de base
        scores = [f.get('properties', {}).get('total_score_20', 0) for f in features]
        classifications = [f.get('properties', {}).get('total_score_classification', 'Inactive') for f in features]
        
        # Distribution des classifications
        active_count = classifications.count('Active')
        semi_active_count = classifications.count('Semi-active')
        inactive_count = classifications.count('Inactive')
        
        # Distribution des scores avec nouveaux barèmes
        score_ranges = {
            '0-6': sum(1 for s in scores if s < 7),
            '7-10': sum(1 for s in scores if 7 <= s <= 10),
            '11-20': sum(1 for s in scores if s > 10)
        }
        
        # Statistiques par critère
        criteria_stats = {}
        for criteria_name in ['luminosite', 'radar', 'vegetation', 'creation_date', 'car_presence']:
            criteria_points = []
            for feature in features:
                props = feature.get('properties', {})
                criteria_data = props.get('total_score_criteria', {}).get(criteria_name, {})
                criteria_points.append(criteria_data.get('points', 0))
            
            criteria_stats[criteria_name] = {
                'mean': sum(criteria_points) / len(criteria_points) if criteria_points else 0,
                'max': max(criteria_points) if criteria_points else 0,
                'min': min(criteria_points) if criteria_points else 0
            }
        
        summary = {
            "analysis_date": datetime.now().isoformat(),
            "total_fincas": len(features),
            "score_statistics": {
                "mean": sum(scores) / len(scores) if scores else 0,
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "std": (sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores))**0.5 if scores else 0
            },
            "classification_distribution": {
                "Active": active_count,
                "Semi-active": semi_active_count,
                "Inactive": inactive_count
            },
            "score_ranges": score_ranges,
            "criteria_statistics": criteria_stats
        }
        
        # Sauvegarder le rapport
        with open('data/total_scores_20_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        with open('data/total_scores_20_report.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"    - Résumé: data/total_scores_20_summary.json")
        logger.info(f"    - Rapport détaillé: data/total_scores_20_report.json")
        
        return summary
    
    def save_updated_data(self, fincas_data: Dict) -> None:
        """Sauvegarder les données mises à jour"""
        logger.info("💾 Sauvegarde des données mises à jour...")
        
        with open(self.output_path, 'w') as f:
            json.dump(fincas_data, f, indent=2)
        
        logger.info("✅ Données sauvegardées:")
        logger.info(f"   - Fichier principal: {self.output_path}")
    
    def run_calculation(self):
        """Exécuter le calcul complet"""
        logger.info("🚀 Démarrage du calcul des scores totaux sur 20")
        
        try:
            # 1. Charger les données
            fincas_data = self.load_fincas_data()
            
            # 2. Calculer les scores
            updated_data = self.process_all_fincas(fincas_data)
            
            # 3. Sauvegarder
            self.save_updated_data(updated_data)
            
            # 4. Générer le rapport
            summary = self.generate_summary_report(updated_data)
            
            # 5. Afficher le résumé
            logger.info("")
            logger.info("📈 RÉSUMÉ DES SCORES TOTAUX:")
            logger.info(f"🏠 Fincas totales: {summary['total_fincas']}")
            logger.info(f"📊 Score moyen: {summary['score_statistics']['mean']:.1f}/20")
            logger.info(f"🟢 Active: {summary['classification_distribution']['Active']}")
            logger.info(f"🟠 Semi-active: {summary['classification_distribution']['Semi-active']}")
            logger.info(f"🔴 Inactive: {summary['classification_distribution']['Inactive']}")
            logger.info("✅ Calcul terminé avec succès!")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du calcul: {e}")
            raise

if __name__ == "__main__":
    calculator = TotalScoreCalculator20()
    calculator.run_calculation()
