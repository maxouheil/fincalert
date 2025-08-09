"""
🚗 YOLO Mobile Objects Detector - Détection changements objets mobiles
Utilise YOLOv8 pour détecter voitures, bateaux, mobilier et calculer mobilité
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import Dict, List, Optional, Tuple
import requests
from io import BytesIO
from PIL import Image
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedObject:
    """Objet détecté avec ses caractéristiques"""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    center: Tuple[float, float]      # x_center, y_center
    area: float


class YOLOMobileDetector:
    """Détecteur d'objets mobiles pour analyse temporelle"""
    
    def __init__(self, model_path: str = "yolov8n.pt"):
        """
        Initialise le détecteur YOLO
        Args:
            model_path: Chemin vers le modèle YOLO
        """
        try:
            self.model = YOLO(model_path)
            logger.info(f"✅ YOLO mobile detector loaded: {model_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")
            raise
        
        # Classes d'objets mobiles d'intérêt (indices COCO)
        self.mobile_classes = {
            2: 'car',           # Voitures
            3: 'motorcycle',    # Motos
            5: 'bus',          # Bus
            7: 'truck',        # Camions
            8: 'boat',         # Bateaux
            56: 'chair',       # Chaises
            60: 'dining table', # Tables
            67: 'cell phone',   # Téléphones (proxy pour activité humaine)
            72: 'tv',          # TV extérieure
            73: 'laptop',      # Ordinateurs portables
        }
    
    def detect_mobility_from_urls(self, image_url_1: str, image_url_2: str, 
                                 finca_id: str = None, time_gap_months: int = 6) -> Dict:
        """
        Détecte changements mobilité entre deux images (URLs)
        Args:
            image_url_1: URL image période 1 (plus ancienne)
            image_url_2: URL image période 2 (plus récente)
            finca_id: ID finca pour logging
            time_gap_months: Écart temporel en mois
        Returns:
            Dict avec score mobilité et détails
        """
        try:
            # Télécharger les deux images
            img1 = self._download_image(image_url_1)
            img2 = self._download_image(image_url_2)
            
            if img1 is None or img2 is None:
                return self._empty_mobility_result("Failed to download images")
            
            return self.detect_mobility_from_images(img1, img2, finca_id, time_gap_months)
            
        except Exception as e:
            logger.error(f"❌ Mobility detection failed for {finca_id}: {e}")
            return self._empty_mobility_result(str(e))
    
    def detect_mobility_from_images(self, img1: np.ndarray, img2: np.ndarray, 
                                   finca_id: str = None, time_gap_months: int = 6) -> Dict:
        """
        Détecte changements mobilité entre deux images OpenCV
        Args:
            img1: Image période 1 (BGR)
            img2: Image période 2 (BGR)
            finca_id: ID finca pour logging
            time_gap_months: Écart temporel en mois
        Returns:
            Dict avec score mobilité et analyse
        """
        try:
            # Détection objets dans les deux images
            objects_t1 = self._detect_mobile_objects(img1, "t1")
            objects_t2 = self._detect_mobile_objects(img2, "t2")
            
            # Analyse des changements
            mobility_analysis = self._analyze_mobility_changes(
                objects_t1, objects_t2, time_gap_months
            )
            
            if finca_id:
                logger.info(f"🚗 {finca_id}: Mobility score: {mobility_analysis['mobility_score']:.2f} "
                          f"({len(objects_t1)} -> {len(objects_t2)} objects)")
            
            return {
                "mobility_score": mobility_analysis["mobility_score"],
                "mobility_level": mobility_analysis["level"],
                "objects_t1": [obj.__dict__ for obj in objects_t1],
                "objects_t2": [obj.__dict__ for obj in objects_t2],
                "changes": mobility_analysis["changes"],
                "summary": mobility_analysis["summary"],
                "time_gap_months": time_gap_months
            }
            
        except Exception as e:
            logger.error(f"❌ Mobility analysis failed for {finca_id}: {e}")
            return self._empty_mobility_result(str(e))
    
    def _download_image(self, url: str) -> Optional[np.ndarray]:
        """Télécharge et convertit image en format OpenCV"""
        try:
            response = requests.get(url, timeout=10)
            if not response.ok:
                return None
            
            image = Image.open(BytesIO(response.content))
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            logger.error(f"❌ Image download failed: {e}")
            return None
    
    def _detect_mobile_objects(self, image: np.ndarray, period: str) -> List[DetectedObject]:
        """
        Détecte objets mobiles dans une image
        Args:
            image: Image OpenCV (BGR)
            period: Identifiant période ("t1" ou "t2")
        Returns:
            Liste d'objets détectés
        """
        try:
            results = self.model(image, verbose=False)
            detected_objects = []
            
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                
                for box in boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    
                    # Filtrer uniquement les objets mobiles avec confiance suffisante
                    if class_id in self.mobile_classes and confidence > 0.4:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Calculer centre et aire
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        area = (x2 - x1) * (y2 - y1)
                        
                        obj = DetectedObject(
                            class_name=self.mobile_classes[class_id],
                            confidence=confidence,
                            bbox=(x1, y1, x2, y2),
                            center=(center_x, center_y),
                            area=area
                        )
                        
                        detected_objects.append(obj)
            
            return detected_objects
            
        except Exception as e:
            logger.error(f"❌ Object detection failed for {period}: {e}")
            return []
    
    def _analyze_mobility_changes(self, objects_t1: List[DetectedObject], 
                                 objects_t2: List[DetectedObject], 
                                 time_gap_months: int) -> Dict:
        """
        Analyse les changements entre deux périodes
        Args:
            objects_t1: Objets détectés en t1
            objects_t2: Objets détectés en t2
            time_gap_months: Écart temporel
        Returns:
            Dict avec analyse de mobilité
        """
        
        # Compter objets par type
        def count_by_type(objects):
            counts = {}
            for obj in objects:
                counts[obj.class_name] = counts.get(obj.class_name, 0) + 1
            return counts
        
        counts_t1 = count_by_type(objects_t1)
        counts_t2 = count_by_type(objects_t2)
        
        # Calcul changements par catégorie
        vehicle_change = self._calculate_category_change(
            counts_t1, counts_t2, ['car', 'motorcycle', 'truck', 'bus']
        )
        
        furniture_change = self._calculate_category_change(
            counts_t1, counts_t2, ['chair', 'dining table']
        )
        
        boat_change = self._calculate_category_change(
            counts_t1, counts_t2, ['boat']
        )
        
        # Calcul score global de mobilité (0-1)
        total_objects_t1 = len(objects_t1)
        total_objects_t2 = len(objects_t2)
        
        # Changement absolu normalisé
        object_change_ratio = abs(total_objects_t2 - total_objects_t1) / max(1, max(total_objects_t1, total_objects_t2))
        
        # Bonus pour nouveaux véhicules (signe d'activité)
        vehicle_bonus = max(0, vehicle_change) * 0.3
        
        # Bonus pour changements mobilier (réaménagement)
        furniture_bonus = abs(furniture_change) * 0.2
        
        # Score final (0-1)
        mobility_score = min(1.0, object_change_ratio + vehicle_bonus + furniture_bonus)
        
        # Ajustement temporel (plus d'écart = changements plus normaux)
        time_factor = max(0.5, min(1.2, time_gap_months / 6))  # Référence: 6 mois
        mobility_score = mobility_score / time_factor
        
        # Classification niveau
        if mobility_score >= 0.7:
            level = "high"
        elif mobility_score >= 0.4:
            level = "medium"
        else:
            level = "low"
        
        return {
            "mobility_score": mobility_score,
            "level": level,
            "changes": {
                "vehicles": vehicle_change,
                "furniture": furniture_change,
                "boats": boat_change,
                "total_objects": total_objects_t2 - total_objects_t1
            },
            "summary": f"Mobility: {level} (score: {mobility_score:.2f}) - "
                      f"{total_objects_t1}→{total_objects_t2} objects, "
                      f"vehicles: {vehicle_change:+.1f}, furniture: {furniture_change:+.1f}"
        }
    
    def _calculate_category_change(self, counts_t1: Dict, counts_t2: Dict, 
                                  category_classes: List[str]) -> float:
        """Calcule changement pour une catégorie d'objets"""
        total_t1 = sum(counts_t1.get(cls, 0) for cls in category_classes)
        total_t2 = sum(counts_t2.get(cls, 0) for cls in category_classes)
        return total_t2 - total_t1
    
    def _empty_mobility_result(self, error_msg: str = "") -> Dict:
        """Retourne résultat vide en cas d'erreur"""
        return {
            "mobility_score": 0.0,
            "mobility_level": "unknown",
            "objects_t1": [],
            "objects_t2": [],
            "changes": {},
            "summary": f"Mobility detection failed: {error_msg}" if error_msg else "No mobility data",
            "time_gap_months": 0
        }


def test_mobile_detector():
    """Test rapide du détecteur mobilité"""
    try:
        detector = YOLOMobileDetector()
        print("✅ YOLO Mobile Detector loaded successfully!")
        print(f"🎯 Tracking {len(detector.mobile_classes)} mobile object classes:")
        for class_id, name in detector.mobile_classes.items():
            print(f"   - {name} (ID: {class_id})")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_mobile_detector()
