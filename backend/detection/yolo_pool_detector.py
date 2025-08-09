"""
🏊 YOLO Pool Detector - Détection piscines avec état (bleue/verte/vide)
Utilise YOLOv8 + analyse couleur HSV pour classification état piscine
"""

import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class YOLOPoolDetector:
    """Détecteur de piscines utilisant YOLO + analyse couleur"""
    
    def __init__(self, model_path: str = "yolov8n.pt"):
        """
        Initialise le détecteur YOLO
        Args:
            model_path: Chemin vers le modèle YOLO (téléchargé automatiquement si nécessaire)
        """
        try:
            self.model = YOLO(model_path)
            logger.info(f"✅ YOLO model loaded: {model_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")
            raise
    
    def detect_pools_from_url(self, image_url: str, finca_id: str = None) -> Dict:
        """
        Détecte piscines depuis une URL d'image (Mapbox Static API)
        Args:
            image_url: URL de l'image satellite
            finca_id: ID de la finca pour logging
        Returns:
            Dict avec résultats détection
        """
        try:
            # Télécharger l'image
            response = requests.get(image_url, timeout=10)
            if not response.ok:
                return self._empty_result(f"Failed to download image: {response.status_code}")
            
            # Convertir en format OpenCV (éviter problème lzma)
            try:
                image = Image.open(BytesIO(response.content))
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            except Exception as img_error:
                # Fallback si problème avec PIL
                return self._empty_result(f"Image processing error: {str(img_error)}")
            
            return self.detect_pools_from_image(cv_image, finca_id)
            
        except Exception as e:
            logger.error(f"❌ Pool detection failed for {finca_id}: {e}")
            return self._empty_result(str(e))
    
    def detect_pools_from_image(self, cv_image: np.ndarray, finca_id: str = None) -> Dict:
        """
        Détecte piscines dans une image OpenCV
        Args:
            cv_image: Image au format OpenCV (BGR)
            finca_id: ID de la finca pour logging
        Returns:
            Dict avec résultats détection
        """
        try:
            # Prédiction YOLO
            results = self.model(cv_image, verbose=False)
            
            pools_detected = []
            
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                
                for i, box in enumerate(boxes):
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id]
                    confidence = float(box.conf[0])
                    
                    # Chercher objets liés aux piscines
                    if self._is_pool_related(class_name) and confidence > 0.3:
                        # Extraire bbox
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        # Analyser couleur dans la zone détectée
                        pool_state = self._analyze_pool_color(cv_image, (x1, y1, x2, y2))
                        
                        pool_info = {
                            "bbox": [x1, y1, x2, y2],
                            "confidence": confidence,
                            "state": pool_state["state"],
                            "color_confidence": pool_state["confidence"],
                            "detected_class": class_name,
                            "area_pixels": (x2 - x1) * (y2 - y1)
                        }
                        
                        pools_detected.append(pool_info)
                        
                        if finca_id:
                            logger.info(f"🏊 {finca_id}: Pool detected - {class_name} "
                                      f"(conf: {confidence:.2f}, state: {pool_state['state']})")
            
            # Résumé final
            return self._summarize_detection(pools_detected, finca_id)
            
        except Exception as e:
            logger.error(f"❌ YOLO detection failed for {finca_id}: {e}")
            return self._empty_result(str(e))
    
    def _is_pool_related(self, class_name: str) -> bool:
        """Vérifie si la classe détectée est liée aux piscines"""
        pool_keywords = [
            'pool', 'swimming', 'water', 'blue', 'basin',
            'tennis', 'court'  # Courts de tennis parfois confondus avec piscines
        ]
        class_lower = class_name.lower()
        return any(keyword in class_lower for keyword in pool_keywords)
    
    def _analyze_pool_color(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict:
        """
        Analyse la couleur dans la zone détectée pour déterminer l'état de la piscine
        Args:
            image: Image complète (BGR)
            bbox: (x1, y1, x2, y2) zone à analyser
        Returns:
            Dict avec état et confiance
        """
        x1, y1, x2, y2 = bbox
        
        # Extraire région d'intérêt avec marges de sécurité
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if x2 <= x1 or y2 <= y1:
            return {"state": "unknown", "confidence": 0.0}
        
        roi = image[y1:y2, x1:x2]
        
        if roi.size == 0:
            return {"state": "unknown", "confidence": 0.0}
        
        # Conversion HSV pour analyse couleur
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Masques couleur pour eau
        # Bleu (eau propre): H=100-130, S=50-255, V=50-255
        blue_lower = np.array([100, 50, 50])
        blue_upper = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
        
        # Vert (eau sale/algues): H=40-80, S=50-255, V=50-255  
        green_lower = np.array([40, 50, 50])
        green_upper = np.array([80, 255, 255])
        green_mask = cv2.inRange(hsv, green_lower, green_upper)
        
        # Gris/marron (vide/sale): S=0-50, V=30-150
        empty_lower = np.array([0, 0, 30])
        empty_upper = np.array([180, 50, 150])
        empty_mask = cv2.inRange(hsv, empty_lower, empty_upper)
        
        # Calculer pourcentages
        total_pixels = roi.shape[0] * roi.shape[1]
        blue_pct = cv2.countNonZero(blue_mask) / total_pixels
        green_pct = cv2.countNonZero(green_mask) / total_pixels
        empty_pct = cv2.countNonZero(empty_mask) / total_pixels
        
        # Classification avec seuils
        if blue_pct > 0.15:  # 15% de pixels bleus
            return {"state": "blue", "confidence": min(1.0, blue_pct * 2)}
        elif green_pct > 0.10:  # 10% de pixels verts
            return {"state": "green", "confidence": min(1.0, green_pct * 2.5)}
        elif empty_pct > 0.20:  # 20% de pixels "vides"
            return {"state": "empty", "confidence": min(1.0, empty_pct * 1.5)}
        else:
            # Analyse luminosité moyenne pour piscine couverte/sombre
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)
            if mean_brightness < 80:  # Sombre = couverte
                return {"state": "covered", "confidence": 0.6}
            else:
                return {"state": "unknown", "confidence": 0.3}
    
    def _summarize_detection(self, pools: List[Dict], finca_id: str = None) -> Dict:
        """Résume les résultats de détection"""
        if not pools:
            return {
                "pool_detected": False,
                "pool_count": 0,
                "best_pool": None,
                "all_pools": [],
                "summary": "No pools detected"
            }
        
        # Trier par confiance (YOLO confidence * color confidence)
        for pool in pools:
            pool["combined_confidence"] = pool["confidence"] * pool["color_confidence"]
        
        pools.sort(key=lambda x: x["combined_confidence"], reverse=True)
        best_pool = pools[0]
        
        # États par priorité (bleu = meilleur état)
        state_priority = {"blue": 4, "green": 3, "covered": 2, "empty": 1, "unknown": 0}
        best_state = max(pools, key=lambda x: state_priority.get(x["state"], 0))
        
        return {
            "pool_detected": True,
            "pool_count": len(pools),
            "best_pool": {
                "state": best_state["state"],
                "confidence": best_state["combined_confidence"],
                "area_pixels": best_state["area_pixels"],
                "detected_class": best_state["detected_class"]
            },
            "all_pools": pools,
            "summary": f"{len(pools)} pool(s) detected, best state: {best_state['state']}"
        }
    
    def _empty_result(self, error_msg: str = "") -> Dict:
        """Retourne un résultat vide en cas d'erreur"""
        return {
            "pool_detected": False,
            "pool_count": 0,
            "best_pool": None,
            "all_pools": [],
            "summary": f"Detection failed: {error_msg}" if error_msg else "No pools detected"
        }


def test_pool_detector():
    """Test rapide du détecteur"""
    try:
        detector = YOLOPoolDetector()
        print("✅ YOLO Pool Detector loaded successfully!")
        
        # Test avec image exemple (remplacer par vraie URL)
        test_url = "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/1.2735,38.9269,18.5,0/400x300@2x?access_token=pk.test"
        # result = detector.detect_pools_from_url(test_url, "test_finca")
        # print(f"Test result: {result}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_pool_detector()
