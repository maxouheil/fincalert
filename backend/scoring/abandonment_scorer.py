"""
🏚️ Abandonment Scoring System - Système de scoring d'abandon
Combine vehicle detection and NDVI analysis for comprehensive abandonment scoring
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class AbandonmentScorer:
    """Système de scoring d'abandon combinant véhicules et NDVI"""
    
    def __init__(self):
        # Vehicle scoring parameters
        self.vehicle_score_config = {
            "no_vehicles_6months": 5,    # +5pts if no cars in 6 months
            "few_vehicles_6months": 2,   # +2pts if 2/12 images have cars
            "many_vehicles_6months": 0   # 0pts if >4/12 images have cars
        }
        
        # NDVI scoring parameters  
        self.ndvi_score_config = {
            "low_variation": 2,          # +2pts if NDVI variation < 10%
            "high_variation": -1         # -1pts if NDVI variation > 25%
        }
        
        # Thresholds
        self.vehicle_thresholds = {
            "few_vehicles": 2,           # 2/12 images with vehicles
            "many_vehicles": 4           # >4/12 images with vehicles
        }
        
        self.ndvi_thresholds = {
            "low_variation": 0.10,       # 10% variation
            "high_variation": 0.25       # 25% variation
        }

    def calculate_vehicle_score(self, vehicle_history: List[Dict]) -> Dict:
        """
        Calcule le score d'abandon basé sur l'historique des véhicules
        
        Args:
            vehicle_history: Liste de 12 détections (6 mois) avec structure:
                [{"date": "2024-01-01", "vehicles_detected": True, "count": 2}, ...]
        
        Returns:
            Dict avec score et détails
        """
        if not vehicle_history or len(vehicle_history) != 12:
            logger.warning(f"Invalid vehicle history length: {len(vehicle_history) if vehicle_history else 0}")
            return {"score": 0, "reason": "Invalid data", "details": {}}
        
        # Compter les images avec véhicules
        images_with_vehicles = sum(1 for det in vehicle_history if det.get("vehicles_detected", False))
        total_images = len(vehicle_history)
        
        # Calculer le score
        if images_with_vehicles == 0:
            score = self.vehicle_score_config["no_vehicles_6months"]
            reason = f"Aucun véhicule détecté sur {total_images} images (6 mois)"
        elif images_with_vehicles <= self.vehicle_thresholds["few_vehicles"]:
            score = self.vehicle_score_config["few_vehicles_6months"]
            reason = f"Peu de véhicules: {images_with_vehicles}/{total_images} images"
        else:
            score = self.vehicle_score_config["many_vehicles_6months"]
            reason = f"Activité normale: {images_with_vehicles}/{total_images} images avec véhicules"
        
        return {
            "score": score,
            "reason": reason,
            "details": {
                "images_with_vehicles": images_with_vehicles,
                "total_images": total_images,
                "vehicle_ratio": images_with_vehicles / total_images
            }
        }

    def calculate_ndvi_score(self, ndvi_data: Dict) -> Dict:
        """
        Calcule le score d'abandon basé sur l'analyse NDVI
        
        Args:
            ndvi_data: Données NDVI avec structure:
                {"variation_percent": 15.5, "mean_ndvi": 0.45, ...}
        
        Returns:
            Dict avec score et détails
        """
        variation = ndvi_data.get("variation_percent", 0) / 100.0  # Convert to decimal
        
        if variation < self.ndvi_thresholds["low_variation"]:
            score = self.ndvi_score_config["low_variation"]
            reason = f"Faible variation NDVI: {variation*100:.1f}% (< {self.ndvi_thresholds['low_variation']*100}%)"
        elif variation > self.ndvi_thresholds["high_variation"]:
            score = self.ndvi_score_config["high_variation"]
            reason = f"Forte variation NDVI: {variation*100:.1f}% (> {self.ndvi_thresholds['high_variation']*100}%)"
        else:
            score = 0
            reason = f"Variation NDVI normale: {variation*100:.1f}%"
        
        return {
            "score": score,
            "reason": reason,
            "details": {
                "variation_percent": variation * 100,
                "mean_ndvi": ndvi_data.get("mean_ndvi", 0)
            }
        }

    def calculate_combined_score(self, vehicle_history: List[Dict], ndvi_data: Dict) -> Dict:
        """
        Calcule le score d'abandon combiné
        
        Args:
            vehicle_history: Historique des véhicules (12 images)
            ndvi_data: Données NDVI
        
        Returns:
            Dict avec score total et breakdown
        """
        vehicle_score = self.calculate_vehicle_score(vehicle_history)
        ndvi_score = self.calculate_ndvi_score(ndvi_data)
        
        total_score = vehicle_score["score"] + ndvi_score["score"]
        
        # Classification d'abandon
        if total_score >= 5:
            abandonment_level = "high"
            level_description = "Fort risque d'abandon"
        elif total_score >= 3:
            abandonment_level = "medium"
            level_description = "Risque d'abandon modéré"
        elif total_score >= 1:
            abandonment_level = "low"
            level_description = "Faible risque d'abandon"
        else:
            abandonment_level = "none"
            level_description = "Aucun signe d'abandon"
        
        return {
            "total_score": total_score,
            "abandonment_level": abandonment_level,
            "level_description": level_description,
            "vehicle_score": vehicle_score,
            "ndvi_score": ndvi_score,
            "max_possible_score": (
                self.vehicle_score_config["no_vehicles_6months"] + 
                self.ndvi_score_config["low_variation"]
            )
        }

    def generate_vehicle_history_from_detections(self, detections: List[Dict]) -> List[Dict]:
        """
        Génère l'historique des véhicules à partir des détections
        
        Args:
            detections: Liste des détections avec dates
        
        Returns:
            Historique formaté pour le scoring
        """
        # Trier par date
        sorted_detections = sorted(detections, key=lambda x: x.get("date", ""))
        
        # Prendre les 12 plus récentes
        recent_detections = sorted_detections[-12:] if len(sorted_detections) >= 12 else sorted_detections
        
        # Formater pour le scoring
        history = []
        for det in recent_detections:
            history.append({
                "date": det.get("date", ""),
                "vehicles_detected": det.get("vehicle_detected", False),
                "count": det.get("total_count", 0),
                "classes": det.get("counts_by_class", {})
            })
        
        return history


def test_scoring_system():
    """Test du système de scoring"""
    scorer = AbandonmentScorer()
    
    # Test 1: Finca abandonnée (aucun véhicule + faible variation NDVI)
    vehicle_history_abandoned = [
        {"date": "2024-01-01", "vehicles_detected": False, "count": 0},
        {"date": "2024-01-15", "vehicles_detected": False, "count": 0},
        {"date": "2024-02-01", "vehicles_detected": False, "count": 0},
        {"date": "2024-02-15", "vehicles_detected": False, "count": 0},
        {"date": "2024-03-01", "vehicles_detected": False, "count": 0},
        {"date": "2024-03-15", "vehicles_detected": False, "count": 0},
        {"date": "2024-04-01", "vehicles_detected": False, "count": 0},
        {"date": "2024-04-15", "vehicles_detected": False, "count": 0},
        {"date": "2024-05-01", "vehicles_detected": False, "count": 0},
        {"date": "2024-05-15", "vehicles_detected": False, "count": 0},
        {"date": "2024-06-01", "vehicles_detected": False, "count": 0},
        {"date": "2024-06-15", "vehicles_detected": False, "count": 0}
    ]
    
    ndvi_data_abandoned = {"variation_percent": 5.0, "mean_ndvi": 0.35}
    
    result_abandoned = scorer.calculate_combined_score(vehicle_history_abandoned, ndvi_data_abandoned)
    print("🏚️ Finca abandonnée:")
    print(f"Score total: {result_abandoned['total_score']}")
    print(f"Niveau: {result_abandoned['abandonment_level']} - {result_abandoned['level_description']}")
    print(f"Véhicules: {result_abandoned['vehicle_score']['reason']}")
    print(f"NDVI: {result_abandoned['ndvi_score']['reason']}")
    print()
    
    # Test 2: Finca active (véhicules + forte variation NDVI)
    vehicle_history_active = [
        {"date": "2024-01-01", "vehicles_detected": True, "count": 2},
        {"date": "2024-01-15", "vehicles_detected": True, "count": 1},
        {"date": "2024-02-01", "vehicles_detected": False, "count": 0},
        {"date": "2024-02-15", "vehicles_detected": True, "count": 3},
        {"date": "2024-03-01", "vehicles_detected": True, "count": 1},
        {"date": "2024-03-15", "vehicles_detected": False, "count": 0},
        {"date": "2024-04-01", "vehicles_detected": True, "count": 2},
        {"date": "2024-04-15", "vehicles_detected": True, "count": 1},
        {"date": "2024-05-01", "vehicles_detected": True, "count": 2},
        {"date": "2024-05-15", "vehicles_detected": False, "count": 0},
        {"date": "2024-06-01", "vehicles_detected": True, "count": 1},
        {"date": "2024-06-15", "vehicles_detected": True, "count": 2}
    ]
    
    ndvi_data_active = {"variation_percent": 30.0, "mean_ndvi": 0.55}
    
    result_active = scorer.calculate_combined_score(vehicle_history_active, ndvi_data_active)
    print("🏠 Finca active:")
    print(f"Score total: {result_active['total_score']}")
    print(f"Niveau: {result_active['abandonment_level']} - {result_active['level_description']}")
    print(f"Véhicules: {result_active['vehicle_score']['reason']}")
    print(f"NDVI: {result_active['ndvi_score']['reason']}")


if __name__ == "__main__":
    test_scoring_system()
