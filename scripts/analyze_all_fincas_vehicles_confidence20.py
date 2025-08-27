#!/usr/bin/env python3
"""
🚗 Analyse Véhicules Toutes les Fincas - CONFIDENCE 20%
Script optimisé pour analyser la présence de véhicules sur les 631 fincas avec confidence 20%
Optimisations: Cache Mapbox, Parallélisation, Réduction I/O
"""

import os
import sys
import json
from pathlib import Path
import logging
from typing import List, Dict, Optional
import time
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import hashlib
import pickle
from PIL import Image
import io

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chemins
BACKEND_DETECTION_DIR = Path("backend/detection")

class Confidence20VehicleAnalyzer:
    """Analyseur de véhicules optimisé avec confidence 20% pour toutes les fincas"""
    
    def __init__(self, max_workers: int = 10, use_cache: bool = True, save_images: bool = True):
        """Initialiser l'analyseur optimisé avec confidence 20%"""
        self.max_workers = max_workers
        self.use_cache = use_cache
        self.save_images = save_images
        self.results = []
        self.lock = threading.Lock()
        self.processed_count = 0
        self.total_count = 0
        
        # Cache pour les images Mapbox
        self.mapbox_cache = {}
        self.cache_dir = Path("data/vehicles_roboflow_analysis/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "mapbox_cache.pkl"
        
        # Charger le cache existant
        if self.use_cache and self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    self.mapbox_cache = pickle.load(f)
                logger.info(f"✅ Cache Mapbox chargé: {len(self.mapbox_cache)} images")
            except Exception as e:
                logger.warning(f"⚠️ Erreur chargement cache: {e}")
                self.mapbox_cache = {}
        
        # Importer le détecteur (une seule fois)
        sys.path.append(str(BACKEND_DETECTION_DIR))
        from roboflow_vehicle_detector import RoboflowVehicleDetector
        self.detector = RoboflowVehicleDetector()
        self.detector.confidence_threshold = 0.2  # Confidence 20% pour maximiser la détection
        
        # Token Mapbox
        self.mapbox_token = os.getenv("MAPBOX_TOKEN") or os.getenv("REACT_APP_MAPBOX_TOKEN")
        if not self.mapbox_token:
            raise ValueError("Token Mapbox requis")
        
        # Paramètres optimaux
        self.zoom = 19
        self.image_width = 1280
        self.image_height = 960
        
        logger.info(f"✅ Analyseur confidence 20% initialisé:")
        logger.info(f"   - Workers: {max_workers}")
        logger.info(f"   - Cache: {'Activé' if use_cache else 'Désactivé'}")
        logger.info(f"   - Images: {'Sauvegardées' if save_images else 'Mémoire uniquement'}")
        logger.info(f"   - Zoom: {self.zoom}")
        logger.info(f"   - Confidence: {self.detector.confidence_threshold*100}%")
    
    def get_image_hash(self, lat: float, lon: float) -> str:
        """Générer un hash unique pour les coordonnées"""
        coord_str = f"{lat:.6f}_{lon:.6f}_{self.zoom}_{self.image_width}x{self.image_height}"
        return hashlib.md5(coord_str.encode()).hexdigest()
    
    def get_cached_image(self, lat: float, lon: float) -> Optional[bytes]:
        """Récupérer une image depuis le cache"""
        if not self.use_cache:
            return None
        
        image_hash = self.get_image_hash(lat, lon)
        return self.mapbox_cache.get(image_hash)
    
    def cache_image(self, lat: float, lon: float, image_data: bytes):
        """Mettre en cache une image"""
        if not self.use_cache:
            return
        
        image_hash = self.get_image_hash(lat, lon)
        self.mapbox_cache[image_hash] = image_data
    
    def save_cache(self):
        """Sauvegarder le cache"""
        if not self.use_cache:
            return
        
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.mapbox_cache, f)
            logger.info(f"✅ Cache sauvegardé: {len(self.mapbox_cache)} images")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde cache: {e}")
    
    def get_mapbox_image(self, lat: float, lon: float) -> bytes:
        """Récupérer une image Mapbox avec cache"""
        # Vérifier le cache d'abord
        cached_image = self.get_cached_image(lat, lon)
        if cached_image:
            return cached_image
        
        # Télécharger depuis Mapbox
        url = f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/{lon},{lat},{self.zoom}/{self.image_width}x{self.image_height}?access_token={self.mapbox_token}"
        
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Erreur Mapbox: {response.status_code}")
        
        # Mettre en cache
        self.cache_image(lat, lon, response.content)
        
        return response.content
    
    def load_fincas_data(self) -> List[Dict]:
        """Charger les données des fincas"""
        logger.info("📂 Chargement des données fincas...")
        
        geojson_path = "frontend/public/data/fincas_with_abandon_scores.geojson"
        
        if not Path(geojson_path).exists():
            raise FileNotFoundError(f"Fichier GeoJSON non trouvé: {geojson_path}")
        
        with open(geojson_path, 'r') as f:
            data = json.load(f)
        
        fincas = []
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            fincas.append({
                'id': props.get('id'),
                'lat': props.get('lat'),
                'lon': props.get('lon'),
                'surface_estimee_m2': props.get('surface_estimee_m2'),
                'abandon_score': props.get('abandon_score')
            })
        
        logger.info(f"✅ {len(fincas)} fincas chargées")
        return fincas
    
    def analyze_single_finca(self, finca: Dict) -> Dict:
        """Analyser une seule finca (optimisé avec confidence 20%)"""
        try:
            finca_id = finca['id']
            lat = finca['lat']
            lon = finca['lon']
            
            # 1. Récupérer l'image (avec cache)
            image_data = self.get_mapbox_image(lat, lon)
            
            # 2. Créer une image PIL en mémoire
            image = Image.open(io.BytesIO(image_data))
            
            # 3. Sauvegarder temporairement si nécessaire pour Roboflow
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file.write(image_data)
                temp_image_path = temp_file.name
            
            try:
                # 4. Détection Roboflow avec confidence 20%
                detections = self.detector.detect_vehicles_from_image(temp_image_path)
                vehicles = detections.get('detections', [])
                total_vehicles = detections.get('total_vehicles', 0)
                
                # 5. Traitement des résultats
                vehicle_details = []
                for j, vehicle in enumerate(vehicles):
                    bbox = vehicle.get('bbox', [])
                    conf = vehicle.get('confidence', 0)
                    
                    if len(bbox) >= 4:
                        vehicle_details.append({
                            'id': j + 1,
                            'bbox': bbox,
                            'confidence': conf,
                            'area': (bbox[2]-bbox[0]) * (bbox[3]-bbox[1])
                        })
                
                # 6. Sauvegarder l'image avec détection
                image_path = None
                if self.save_images:
                    detection_img = image.copy()
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(detection_img)
                    
                    for vehicle in vehicle_details:
                        bbox = vehicle['bbox']
                        conf = vehicle['confidence']
                        
                        x1, y1, x2, y2 = bbox
                        
                        # Couleur basée sur la confiance (ajustée pour confidence 20%)
                        if conf >= 0.7:
                            color = 'green'
                        elif conf >= 0.5:
                            color = 'yellow'
                        elif conf >= 0.3:
                            color = 'orange'
                        else:
                            color = 'red'
                        
                        # Dessiner le rectangle
                        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
                        
                        # Ajouter le label
                        label = f"V{vehicle['id']} ({conf:.2f})"
                        draw.text((x1, y1-20), label, fill=color, font=None)
                    
                    # Sauvegarder
                    output_dir = Path("data/vehicles_roboflow_analysis/confidence20_analysis")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    image_path = output_dir / f"{finca_id}_detection.jpg"
                    detection_img.save(image_path)
                
                # 7. Résultat
                result = {
                    'finca_id': finca_id,
                    'lat': lat,
                    'lon': lon,
                    'surface_estimee_m2': finca.get('surface_estimee_m2'),
                    'abandon_score': finca.get('abandon_score'),
                    'analysis_date': datetime.now().isoformat(),
                    'workflow': 'confidence20_optimized',
                    'parameters': {
                        'zoom': self.zoom,
                        'confidence_threshold': self.detector.confidence_threshold,
                        'image_size': f"{self.image_width}x{self.image_height}",
                        'cache_used': self.use_cache,
                        'images_saved': self.save_images
                    },
                    'total_vehicles': total_vehicles,
                    'vehicles': vehicle_details,
                    'avg_confidence': sum(v['confidence'] for v in vehicle_details) / len(vehicle_details) if vehicle_details else 0,
                    'image_path': str(image_path) if image_path else None,
                    'success': True
                }
                
            finally:
                # Nettoyage
                os.unlink(temp_image_path)
            
            # Mettre à jour le compteur
            with self.lock:
                self.processed_count += 1
                logger.info(f"✅ {finca_id} terminé ({self.processed_count}/{self.total_count}) - {total_vehicles} véhicules")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur analyse {finca_id}: {e}")
            return {
                'finca_id': finca_id,
                'error': str(e),
                'analysis_date': datetime.now().isoformat(),
                'success': False
            }
    
    def analyze_all_fincas(self, limit: Optional[int] = None) -> List[Dict]:
        """Analyser toutes les fincas avec optimisations et confidence 20%"""
        logger.info("🚀 Démarrage analyse confidence 20%...")
        
        # Charger les données
        fincas = self.load_fincas_data()
        
        if limit:
            fincas = fincas[:limit]
            logger.info(f"🔢 Limite appliquée: {limit} fincas")
        
        self.total_count = len(fincas)
        logger.info(f"📊 Analyse de {self.total_count} fincas")
        logger.info(f"🚀 Workers: {self.max_workers}")
        logger.info(f"💾 Cache: {'Activé' if self.use_cache else 'Désactivé'}")
        logger.info(f"🖼️ Images: {'Sauvegardées' if self.save_images else 'Mémoire uniquement'}")
        logger.info(f"🎯 Confidence: {self.detector.confidence_threshold*100}%")
        
        # Créer le répertoire de sortie
        output_dir = Path("data/vehicles_roboflow_analysis/confidence20_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Analyser avec ThreadPoolExecutor
        results = []
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Soumettre toutes les tâches
            future_to_finca = {
                executor.submit(self.analyze_single_finca, finca): finca 
                for finca in fincas
            }
            
            # Traiter les résultats au fur et à mesure
            for future in as_completed(future_to_finca):
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Sauvegarde intermédiaire tous les 100 résultats
                    if len(results) % 100 == 0:
                        self.save_intermediate_results(results)
                        
                except Exception as e:
                    finca = future_to_finca[future]
                    logger.error(f"❌ Erreur future {finca['id']}: {e}")
                    results.append({
                        'finca_id': finca['id'],
                        'error': str(e),
                        'analysis_date': datetime.now().isoformat(),
                        'success': False
                    })
        
        # Sauvegarder le cache
        self.save_cache()
        
        # Temps total
        total_time = time.time() - start_time
        successful_fincas = len([r for r in results if r.get('success', False)])
        total_vehicles = sum(r.get('total_vehicles', 0) for r in results if r.get('success', False))
        
        logger.info(f"\n📊 RÉSUMÉ FINAL")
        logger.info(f"⏱️ Temps total: {total_time:.1f} secondes ({total_time/60:.1f} minutes)")
        logger.info(f"🚀 Vitesse: {self.total_count / total_time:.1f} fincas/minute")
        logger.info(f"✅ Fincas réussies: {successful_fincas}/{self.total_count}")
        logger.info(f"🚗 Total véhicules détectés: {total_vehicles}")
        logger.info(f"📊 Moyenne véhicules/finca: {total_vehicles/successful_fincas:.2f}" if successful_fincas > 0 else "📊 Moyenne véhicules/finca: 0")
        
        return results
    
    def save_intermediate_results(self, results: List[Dict]):
        """Sauvegarder les résultats intermédiaires"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vehicles_analysis_confidence20_intermediate_{timestamp}.json"
        filepath = Path("data/vehicles_roboflow_analysis/confidence20_analysis") / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"💾 Sauvegarde intermédiaire: {filename}")
    
    def save_final_results(self, results: List[Dict]):
        """Sauvegarder les résultats finaux"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Résultats complets
        full_filename = f"vehicles_analysis_confidence20_complete_{timestamp}.json"
        full_filepath = Path("data/vehicles_roboflow_analysis/confidence20_analysis") / full_filename
        
        with open(full_filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Résumé statistique
        summary = self.create_summary(results)
        summary_filename = f"vehicles_analysis_confidence20_summary_{timestamp}.json"
        summary_filepath = Path("data/vehicles_roboflow_analysis/confidence20_analysis") / summary_filename
        
        with open(summary_filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"💾 Résultats sauvegardés:")
        logger.info(f"   - Complets: {full_filename}")
        logger.info(f"   - Résumé: {summary_filename}")
        
        return full_filepath, summary_filepath
    
    def create_summary(self, results: List[Dict]) -> Dict:
        """Créer un résumé des résultats"""
        successful_results = [r for r in results if r.get('success', False)]
        
        total_vehicles = sum(r.get('total_vehicles', 0) for r in successful_results)
        fincas_with_vehicles = len([r for r in successful_results if r.get('total_vehicles', 0) > 0])
        
        # Statistiques de confiance
        all_confidences = []
        for r in successful_results:
            vehicles = r.get('vehicles', [])
            all_confidences.extend([v.get('confidence', 0) for v in vehicles])
        
        return {
            'analysis_type': 'confidence20_vehicle_detection',
            'analysis_date': datetime.now().isoformat(),
            'parameters': {
                'zoom': self.zoom,
                'confidence_threshold': self.detector.confidence_threshold,
                'max_workers': self.max_workers,
                'cache_used': self.use_cache,
                'images_saved': self.save_images
            },
            'statistics': {
                'total_fincas': len(results),
                'successful_fincas': len(successful_results),
                'failed_fincas': len(results) - len(successful_results),
                'total_vehicles_detected': total_vehicles,
                'fincas_with_vehicles': fincas_with_vehicles,
                'fincas_without_vehicles': len(successful_results) - fincas_with_vehicles,
                'avg_vehicles_per_finca': total_vehicles / len(successful_results) if successful_results else 0,
                'vehicle_detection_rate': fincas_with_vehicles / len(successful_results) if successful_results else 0,
                'avg_confidence': sum(all_confidences) / len(all_confidences) if all_confidences else 0,
                'min_confidence': min(all_confidences) if all_confidences else 0,
                'max_confidence': max(all_confidences) if all_confidences else 0
            },
            'workflow_performance': {
                'cache_hit_rate': len(self.mapbox_cache) / (len(self.mapbox_cache) + len(successful_results)) if self.use_cache else 0,
                'cache_size': len(self.mapbox_cache)
            }
        }

def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyse optimisée des véhicules sur toutes les fincas avec confidence 20%")
    parser.add_argument("--limit", type=int, help="Limiter le nombre de fincas à analyser")
    parser.add_argument("--workers", type=int, default=10, help="Nombre de workers (défaut: 10)")
    parser.add_argument("--no-cache", action="store_true", help="Désactiver le cache Mapbox")
    parser.add_argument("--no-images", action="store_true", help="Ne pas sauvegarder les images avec détection")
    
    args = parser.parse_args()
    
    # Créer l'analyseur
    analyzer = Confidence20VehicleAnalyzer(
        max_workers=args.workers,
        use_cache=not args.no_cache,
        save_images=not args.no_images
    )
    
    # Analyser
    results = analyzer.analyze_all_fincas(limit=args.limit)
    
    # Sauvegarder
    analyzer.save_final_results(results)
    
    return results

if __name__ == "__main__":
    main()
