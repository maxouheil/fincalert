"""
🎯 Demo Detector - Simulation réaliste pour démonstration
Génère des résultats cohérents basés sur les données de finca
"""

import random
from typing import Dict
import hashlib


class DemoDetector:
    """Détecteur de démonstration avec résultats cohérents"""
    
    def __init__(self):
        pass
    
    def detect_pools_demo(self, finca_id: str, lat: float, lon: float) -> Dict:
        """
        Génère résultats de détection piscine cohérents
        Args:
            finca_id: ID de la finca
            lat, lon: Coordonnées
        Returns:
            Dict avec résultats détection réalistes
        """
        # Seed basé sur finca_id pour cohérence
        seed = int(hashlib.md5(finca_id.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Probabilités basées sur position géographique (plus proche côte = plus de piscines)
        coastal_factor = max(0, 1 - abs(lat - 38.9) * 10)  # Plus proche 38.9°N = plus côtier
        pool_probability = 0.15 + coastal_factor * 0.25  # 15-40% chance
        
        has_pool = random.random() < pool_probability
        
        if has_pool:
            # Types de piscines avec probabilités réalistes
            states = ['blue', 'green', 'empty', 'covered']
            weights = [0.6, 0.2, 0.15, 0.05]  # Majorité entretenues
            pool_state = random.choices(states, weights=weights)[0]
            
            confidence = 0.7 + random.random() * 0.25  # 70-95%
            area_pixels = random.randint(150, 800)  # Taille variable
            
            return {
                "pool_detected": True,
                "pool_count": 1,
                "best_pool": {
                    "state": pool_state,
                    "confidence": confidence,
                    "area_pixels": area_pixels,
                    "detected_class": "pool"
                },
                "all_pools": [{
                    "bbox": [100, 80, 180, 140],
                    "confidence": confidence,
                    "state": pool_state,
                    "color_confidence": 0.8,
                    "detected_class": "pool",
                    "area_pixels": area_pixels,
                    "combined_confidence": confidence * 0.8
                }],
                "summary": f"1 pool detected, state: {pool_state}"
            }
        else:
            return {
                "pool_detected": False,
                "pool_count": 0,
                "best_pool": None,
                "all_pools": [],
                "summary": "No pools detected"
            }
    
    def detect_mobility_demo(self, finca_id: str, lat: float, lon: float, time_gap_months: int = 6) -> Dict:
        """
        Génère résultats de mobilité cohérents
        Args:
            finca_id: ID de la finca
            lat, lon: Coordonnées
            time_gap_months: Écart temporel
        Returns:
            Dict avec analyse mobilité réaliste
        """
        # Seed basé sur finca_id pour cohérence
        seed = int(hashlib.md5((finca_id + "_mobility").encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Mobilité basée sur proximité zones urbaines
        urban_factor = max(0, 1 - abs(lon - 1.27) * 20)  # Plus proche 1.27°E = plus urbain
        base_mobility = 0.2 + urban_factor * 0.5  # 20-70%
        
        # Simulation objets détectés
        vehicles_t1 = random.randint(0, 3) if random.random() < base_mobility else 0
        vehicles_t2 = max(0, vehicles_t1 + random.randint(-1, 2))
        
        furniture_t1 = random.randint(0, 2) if random.random() < base_mobility * 0.7 else 0
        furniture_t2 = max(0, furniture_t1 + random.randint(-1, 1))
        
        boats_t1 = random.randint(0, 1) if random.random() < 0.1 else 0
        boats_t2 = boats_t1  # Bateaux changent moins
        
        total_change = abs(vehicles_t2 - vehicles_t1) + abs(furniture_t2 - furniture_t1)
        mobility_score = min(1.0, (total_change + base_mobility) / 3)
        
        if mobility_score >= 0.7:
            level = "high"
        elif mobility_score >= 0.4:
            level = "medium"
        else:
            level = "low"
        
        return {
            "mobility_score": mobility_score,
            "mobility_level": level,
            "objects_t1": self._generate_objects(vehicles_t1, furniture_t1, boats_t1),
            "objects_t2": self._generate_objects(vehicles_t2, furniture_t2, boats_t2),
            "changes": {
                "vehicles": vehicles_t2 - vehicles_t1,
                "furniture": furniture_t2 - furniture_t1,
                "boats": boats_t2 - boats_t1,
                "total_objects": (vehicles_t2 + furniture_t2 + boats_t2) - (vehicles_t1 + furniture_t1 + boats_t1)
            },
            "summary": f"Mobility: {level} (score: {mobility_score:.2f}) - {vehicles_t1 + furniture_t1 + boats_t1}→{vehicles_t2 + furniture_t2 + boats_t2} objects",
            "time_gap_months": time_gap_months
        }
    
    def _generate_objects(self, vehicles: int, furniture: int, boats: int) -> list:
        """Génère liste d'objets simulés"""
        objects = []
        
        # Ajouter véhicules
        for i in range(vehicles):
            objects.append({
                "class_name": random.choice(["car", "truck", "motorcycle"]),
                "confidence": 0.7 + random.random() * 0.25,
                "bbox": [random.randint(50, 150), random.randint(50, 100), 
                        random.randint(180, 250), random.randint(120, 180)],
                "center": [random.randint(100, 200), random.randint(75, 140)],
                "area": random.randint(1500, 4000)
            })
        
        # Ajouter mobilier
        for i in range(furniture):
            objects.append({
                "class_name": random.choice(["chair", "dining table"]),
                "confidence": 0.6 + random.random() * 0.3,
                "bbox": [random.randint(200, 300), random.randint(150, 200), 
                        random.randint(220, 340), random.randint(170, 220)],
                "center": [random.randint(210, 320), random.randint(160, 210)],
                "area": random.randint(400, 1200)
            })
        
        # Ajouter bateaux
        for i in range(boats):
            objects.append({
                "class_name": "boat",
                "confidence": 0.8 + random.random() * 0.15,
                "bbox": [random.randint(0, 50), random.randint(0, 50), 
                        random.randint(80, 150), random.randint(70, 120)],
                "center": [random.randint(40, 100), random.randint(35, 85)],
                "area": random.randint(2000, 6000)
            })
        
        return objects
    
    def get_visual_analysis_demo(self, finca_id: str, lat: float, lon: float) -> Dict:
        """Analyse visuelle complète démo"""
        pools = self.detect_pools_demo(finca_id, lat, lon)
        mobility = self.detect_mobility_demo(finca_id, lat, lon)
        
        # Générer résumé
        activity_indicators = []
        visual_score = 0.0
        
        # Analyse piscines
        if pools["pool_detected"]:
            pool_state = pools["best_pool"]["state"]
            if pool_state == "blue":
                activity_indicators.append("🏊 Piscine entretenue")
                visual_score += 0.3
            elif pool_state == "green":
                activity_indicators.append("🏊 Piscine sale")
                visual_score += 0.1
            else:
                activity_indicators.append("🏊 Piscine détectée")
                visual_score += 0.2
        
        # Analyse mobilité
        mobility_level = mobility["mobility_level"]
        if mobility_level == "high":
            activity_indicators.append("🚗 Activité élevée")
            visual_score += 0.4
        elif mobility_level == "medium":
            activity_indicators.append("🚗 Activité modérée")
            visual_score += 0.2
        
        visual_score += mobility["mobility_score"] * 0.3
        visual_score = min(1.0, visual_score)
        
        # Classification confiance
        if visual_score >= 0.6:
            confidence = "high"
        elif visual_score >= 0.3:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "finca_id": finca_id,
            "pools": {"detection_result": pools},
            "mobility": {"detection_result": mobility},
            "summary": {
                "activity_indicators": activity_indicators,
                "visual_score": visual_score,
                "confidence": confidence
            }
        }
