#!/usr/bin/env python3
"""
🚗 Détecteur de Véhicules Roboflow (Meilleur Modèle)
Module de détection utilisant le SDK Roboflow - Modèle "Finca cars in Ibiza 2" (v2)
Performance: mAP@50: 77.6%, Precision: 79.7%, Recall: 86.0%
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import logging
from PIL import Image
import io
import requests # Added missing import for requests

logger = logging.getLogger(__name__)

class RoboflowVehicleDetector:
    """Détecteur de véhicules utilisant le SDK Roboflow (meilleur modèle)"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialiser le détecteur avec paramètres optimaux"""
        self.api_key = api_key or os.getenv("ROBOFLOW_API_KEY")
        if not self.api_key:
            raise ValueError("Clé API Roboflow requise")
        
        self.project = "fincalert/finca-cars-in-ibiza-jpcb2"
        self.version = "2"  # Version 2 avec meilleures performances
        self.confidence_threshold = 0.5
        
        # Paramètres optimaux (workflow gagnant)
        self.zoom = 19  # Zoom optimal pour détection
        self.full_width = 1280  # Largeur image complète
        self.full_height = 960  # Hauteur image complète
        self.crop_width = 960   # Largeur crop optimale
        self.crop_height = 720  # Hauteur crop optimale
        
        # Initialiser le SDK Roboflow
        try:
            from roboflow import Roboflow
            self.rf = Roboflow(api_key=self.api_key)
            self.model = self.rf.workspace("fincalert").project("finca-cars-in-ibiza-jpcb2").version(2).model
            logger.info(f"✅ Détecteur Roboflow initialisé: {self.project} v{self.version}")
            logger.info(f"📊 Performance: mAP@50: 77.6%, Precision: 79.7%, Recall: 86.0%")
            logger.info(f"🎯 Paramètres optimaux: Zoom {self.zoom}, Crop {self.crop_width}x{self.crop_height}")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation SDK Roboflow: {e}")
            raise
    
    def detect_vehicles_from_image(self, image_path: str) -> Dict:
        """Détecter les véhicules dans une image via SDK Roboflow"""
        try:
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image non trouvée: {image_path}")
            
            # Prédiction avec le SDK
            prediction = self.model.predict(
                image_path, 
                confidence=int(self.confidence_threshold * 100), 
                overlap=30
            )
            
            # Traitement des résultats
            predictions_data = prediction.json()
            detections = []
            vehicle_count = 0
            
            for pred in predictions_data.get("predictions", []):
                if pred.get("confidence", 0) >= self.confidence_threshold:
                    # CORRECTION: Roboflow retourne des coordonnées centrées
                    # x, y = centre de la boîte, width, height = dimensions
                    center_x = pred.get("x", 0)
                    center_y = pred.get("y", 0)
                    width = pred.get("width", 0)
                    height = pred.get("height", 0)
                    
                    # Convertir en coordonnées de coin supérieur gauche pour compatibilité
                    x1 = center_x - width // 2
                    y1 = center_y - height // 2
                    x2 = center_x + width // 2
                    y2 = center_y + height // 2
                    
                    detection = {
                        "class": pred.get("class", "unknown"),
                        "confidence": pred.get("confidence", 0),
                        "bbox": [x1, y1, x2, y2],  # Format [x1, y1, x2, y2] pour compatibilité
                        "bbox_center": [center_x, center_y, width, height],  # Format original Roboflow
                        "area": width * height
                    }
                    
                    detections.append(detection)
                    vehicle_count += 1
            
            # Résultats
            api_result = {
                "image_path": image_path,
                "total_vehicles": vehicle_count,
                "detections": detections,
                "classes_detected": list(set([d["class"] for d in detections])),
                "confidence_threshold": self.confidence_threshold,
                "api_info": {
                    "project": self.project,
                    "version": self.version,
                    "performance": {
                        "mAP@50": "77.6%",
                        "precision": "79.7%",
                        "recall": "86.0%"
                    }
                }
            }
            
            logger.info(f"🚗 Détecté {vehicle_count} véhicules dans {image_path}")
            return api_result
            
        except Exception as e:
            logger.error(f"❌ Erreur détection: {e}")
            return {
                "image_path": image_path,
                "error": str(e),
                "total_vehicles": 0,
                "detections": []
            }
    
    def detect_vehicles_from_url(self, image_url: str) -> Dict:
        """Détecter les véhicules depuis une URL d'image"""
        try:
            # URL de l'API Roboflow avec paramètres
            api_url = f"https://detect.roboflow.com/{self.project}/{self.version}"
            
            # Paramètres de la requête (méthode GET)
            params = {
                "api_key": self.api_key,
                "confidence": int(self.confidence_threshold * 100),
                "format": "json",
                "image": image_url
            }
            
            # Appel API (GET au lieu de POST)
            response = requests.get(api_url, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                # Traitement identique à detect_vehicles_from_image
                detections = []
                vehicle_count = 0
                
                for prediction in result.get("predictions", []):
                    if prediction.get("confidence", 0) >= self.confidence_threshold:
                        # CORRECTION: Roboflow retourne des coordonnées centrées
                        center_x = prediction.get("x", 0)
                        center_y = prediction.get("y", 0)
                        width = prediction.get("width", 0)
                        height = prediction.get("height", 0)
                        
                        # Convertir en coordonnées de coin supérieur gauche
                        x1 = center_x - width // 2
                        y1 = center_y - height // 2
                        x2 = center_x + width // 2
                        y2 = center_y + height // 2
                        
                        detection = {
                            "class": prediction.get("class", "unknown"),
                            "confidence": prediction.get("confidence", 0),
                            "bbox": [x1, y1, x2, y2],
                            "bbox_center": [center_x, center_y, width, height],
                            "area": width * height
                        }
                        
                        detections.append(detection)
                        vehicle_count += 1
                
                return {
                    "image_url": image_url,
                    "total_vehicles": vehicle_count,
                    "detections": detections,
                    "classes_detected": list(set([d["class"] for d in detections])),
                    "confidence_threshold": self.confidence_threshold
                }
            else:
                return {
                    "image_url": image_url,
                    "error": f"API Error: {response.status_code}",
                    "total_vehicles": 0,
                    "detections": []
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur détection URL: {e}")
            return {
                "image_url": image_url,
                "error": str(e),
                "total_vehicles": 0,
                "detections": []
            }
    
    def detect_vehicles_optimized(self, lat: float, lon: float, mapbox_token: str) -> Dict:
        """Détection optimisée avec workflow gagnant (Zoom 19 + Crop 960x720)"""
        try:
            import requests
            from PIL import Image
            import tempfile
            
            # 1. Récupérer l'image complète depuis Mapbox
            url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},{self.zoom}/{self.full_width}x{self.full_height}?access_token={mapbox_token}"
            
            response = requests.get(url)
            if response.status_code != 200:
                raise Exception(f"Erreur Mapbox: {response.status_code}")
            
            # 2. Créer un fichier temporaire pour l'image complète
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_full:
                temp_full.write(response.content)
                full_image_path = temp_full.name
            
            # 3. Crop l'image au centre
            full_image = Image.open(full_image_path)
            left = (full_image.width - self.crop_width) // 2
            top = (full_image.height - self.crop_height) // 2
            right = left + self.crop_width
            bottom = top + self.crop_height
            
            cropped_image = full_image.crop((left, top, right, bottom))
            
            # 4. Sauvegarder l'image cropée temporairement
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_crop:
                cropped_image.save(temp_crop.name, 'JPEG')
                crop_image_path = temp_crop.name
            
            # 5. Détection sur l'image cropée
            detections = self.detect_vehicles_from_image(crop_image_path)
            
            # 6. Nettoyer les fichiers temporaires
            os.unlink(full_image_path)
            os.unlink(crop_image_path)
            
            # 7. Ajouter les métadonnées du workflow
            detections.update({
                "workflow": "optimized",
                "parameters": {
                    "zoom": self.zoom,
                    "full_size": f"{self.full_width}x{self.full_height}",
                    "crop_size": f"{self.crop_width}x{self.crop_height}",
                    "crop_offset": {"left": left, "top": top, "right": right, "bottom": bottom}
                },
                "coordinates": {"lat": lat, "lon": lon}
            })
            
            logger.info(f"✅ Détection optimisée: {detections.get('total_vehicles', 0)} véhicules détectés")
            return detections
            
        except Exception as e:
            logger.error(f"❌ Erreur détection optimisée: {e}")
            return {
                "error": str(e),
                "total_vehicles": 0,
                "detections": [],
                "workflow": "optimized",
                "coordinates": {"lat": lat, "lon": lon}
            }
    
    def calculate_vehicle_score(self, detection_results: List[Dict]) -> Dict:
        """Calculer le score d'activité véhicules (1-5 points)"""
        try:
            if not detection_results:
                return {"score": 1, "reason": "Aucune détection", "details": {}}
            
            # Statistiques
            total_images = len(detection_results)
            images_with_vehicles = sum(1 for r in detection_results if r.get("total_vehicles", 0) > 0)
            total_vehicles = sum(r.get("total_vehicles", 0) for r in detection_results)
            
            # Calcul du score
            vehicle_ratio = images_with_vehicles / total_images if total_images > 0 else 0
            avg_vehicles_per_image = total_vehicles / total_images if total_images > 0 else 0
            
            # Logique de scoring (à ajuster selon vos besoins)
            if vehicle_ratio >= 0.8 and avg_vehicles_per_image >= 2:
                score = 5
                reason = "Activité véhiculaire très élevée"
            elif vehicle_ratio >= 0.6 and avg_vehicles_per_image >= 1:
                score = 4
                reason = "Activité véhiculaire élevée"
            elif vehicle_ratio >= 0.4 and avg_vehicles_per_image >= 0.5:
                score = 3
                reason = "Activité véhiculaire modérée"
            elif vehicle_ratio >= 0.2:
                score = 2
                reason = "Activité véhiculaire faible"
            else:
                score = 1
                reason = "Aucune activité véhiculaire détectée"
            
            return {
                "score": score,
                "reason": reason,
                "details": {
                    "total_images": total_images,
                    "images_with_vehicles": images_with_vehicles,
                    "total_vehicles": total_vehicles,
                    "vehicle_ratio": vehicle_ratio,
                    "avg_vehicles_per_image": avg_vehicles_per_image
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul score: {e}")
            return {"score": 1, "reason": f"Erreur: {e}", "details": {}}

# Instance globale pour réutilisation
_vehicle_detector = None

def get_vehicle_detector() -> RoboflowVehicleDetector:
    """Obtenir l'instance du détecteur (singleton)"""
    global _vehicle_detector
    if _vehicle_detector is None:
        _vehicle_detector = RoboflowVehicleDetector()
    return _vehicle_detector
