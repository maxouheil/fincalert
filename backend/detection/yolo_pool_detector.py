"""
🏊 YOLO Pool Detector - Détection piscines avec état (bleue/verte/vide)
Utilise YOLOv8 + analyse couleur HSV pour classification état piscine
"""

import cv2
import numpy as np
from ultralytics import YOLO
# Stub torchvision ops.nms if missing to avoid _lzma dependency
try:
    import torchvision  # noqa: F401
    # if ops missing, add simple stub
    if not hasattr(__import__('torchvision'), 'ops'):
        raise ImportError
except Exception:
    import sys as _sys, types as _types, torch as _torch
    _parent = _types.ModuleType('torchvision')
    _ops = _types.ModuleType('torchvision.ops')
    def _nms(boxes: _torch.Tensor, scores: _torch.Tensor, iou_thres: float):
        if boxes.numel() == 0:
            return _torch.empty((0,), dtype=_torch.long)
        x1, y1, x2, y2 = boxes[:,0], boxes[:,1], boxes[:,2], boxes[:,3]
        areas = (x2 - x1).clamp(min=0) * (y2 - y1).clamp(min=0)
        order = scores.argsort(descending=True)
        keep = []
        while order.numel() > 0:
            i = int(order[0])
            keep.append(i)
            if order.numel() == 1:
                break
            xx1 = _torch.maximum(x1[i], x1[order[1:]])
            yy1 = _torch.maximum(y1[i], y1[order[1:]])
            xx2 = _torch.minimum(x2[i], x2[order[1:]])
            yy2 = _torch.minimum(y2[i], y2[order[1:]])
            w = (xx2 - xx1).clamp(min=0)
            h = (yy2 - yy1).clamp(min=0)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-6)
            inds = (iou <= iou_thres).nonzero(as_tuple=False).squeeze(1)
            order = order[inds + 1]
        return _torch.tensor(keep, dtype=_torch.long)
    _ops.nms = _nms
    _parent.ops = _ops
    _sys.modules['torchvision'] = _parent
    _sys.modules['torchvision.ops'] = _ops
    for _name in ['datasets','io','models','transforms','utils','_meta_registrations']:
        _sys.modules[f'torchvision.{_name}'] = _types.ModuleType(f'torchvision.{_name}')
import os
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
            preferred = os.environ.get("POOL_MODEL_PATH")
            fallback = model_path
            local_trained = os.path.join(os.path.dirname(__file__), "..", "yolo_pools.pt")
            local_trained = os.path.normpath(local_trained)
            chosen = preferred or (local_trained if os.path.exists(local_trained) else fallback)
            self.model = YOLO(chosen)
            logger.info(f"✅ YOLO model loaded: {chosen}")
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")
            raise
        # Detection thresholds
        self.conf_threshold_pool: float = 0.05
        # Central crop ratio to limit detection area (e.g., 0.7 keeps 70% width/height centered)
        try:
            self.crop_ratio: float = float(os.getenv("POOL_CROP_RATIO", "1.0"))
            if not (0.2 <= self.crop_ratio <= 1.0):
                self.crop_ratio = 1.0
        except Exception:
            self.crop_ratio = 1.0
    
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

            # Optional central crop to reduce detection zone
            x_off, y_off = 0, 0
            if self.crop_ratio < 1.0:
                h, w = cv_image.shape[:2]
                new_w = max(1, int(w * self.crop_ratio))
                new_h = max(1, int(h * self.crop_ratio))
                x_off = (w - new_w) // 2
                y_off = (h - new_h) // 2
                cv_image_cropped = cv_image[y_off:y_off+new_h, x_off:x_off+new_w]
            else:
                cv_image_cropped = cv_image

            result = self.detect_pools_from_image(cv_image_cropped, finca_id)

            # Shift bboxes back to original image coordinates if cropped
            if self.crop_ratio < 1.0 and result.get("all_pools"):
                for p in result["all_pools"]:
                    bx1, by1, bx2, by2 = p.get("bbox", [0, 0, 0, 0])
                    p["bbox"] = [bx1 + x_off, by1 + y_off, bx2 + x_off, by2 + y_off]
            if self.crop_ratio < 1.0:
                result["crop_ratio"] = self.crop_ratio
                result["crop_offsets"] = {"x": x_off, "y": y_off}

            return result
            
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
            # Run at higher img size for small pools
            results = self.model.predict(source=cv_image, imgsz=1280, conf=self.conf_threshold_pool, iou=0.6, verbose=False)
            
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
                    if self._is_pool_related(class_name) and confidence > self.conf_threshold_pool:
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
        # Bleu (eau propre)
        blue_lower = np.array([90, 55, 55])
        blue_upper = np.array([135, 255, 255])
        # Turquoise/cyan considéré comme bleu
        cyan_lower = np.array([80, 55, 55])
        cyan_upper = np.array([95, 255, 255])
        blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
        
        # Vert (eau sale/algues): resserré 55-75 et plus saturé/lumineux
        green_lower = np.array([55, 60, 60])
        green_upper = np.array([75, 255, 255])
        green_mask = cv2.inRange(hsv, green_lower, green_upper)
        
        # Gris/marron (vide/sale): S=0-50, V=30-150
        empty_lower = np.array([0, 0, 30])
        empty_upper = np.array([180, 50, 150])
        empty_mask = cv2.inRange(hsv, empty_lower, empty_upper)
        
        # Calculer pourcentages
        total_pixels = roi.shape[0] * roi.shape[1]
        # Union bleu + turquoise
        cyan_mask = cv2.inRange(hsv, cyan_lower, cyan_upper)
        blue_union = cv2.bitwise_or(blue_mask, cyan_mask)
        blue_cnt = cv2.countNonZero(blue_union)
        green_cnt = cv2.countNonZero(green_mask)
        blue_pct = blue_cnt / total_pixels
        green_pct = green_cnt / total_pixels
        empty_pct = cv2.countNonZero(empty_mask) / total_pixels
        # Moyenne de teinte sur pixels verts détectés pour éviter le turquoise
        green_h_mean = None
        if green_cnt > 0:
            green_h_mean = float(hsv[..., 0][green_mask > 0].mean())
        
        # Classification avec seuils (resserrer le vert vs turquoise)
        # Bleu si dominance marquée ou simplement proportion suffisante
        if blue_pct >= max(0.08, green_pct * 1.25):
            return {"state": "blue", "confidence": min(1.0, blue_pct * 2)}
        # Vert uniquement si suffisamment de pixels verts, dominance nette et teinte bien verte
        elif green_pct >= 0.12 and green_pct >= blue_pct * 1.25 and (green_h_mean is not None and 58 <= green_h_mean <= 72):
            return {"state": "green", "confidence": min(1.0, green_pct * 2.0)}
        elif empty_pct > 0.15:  # 15% de pixels "vides"
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
