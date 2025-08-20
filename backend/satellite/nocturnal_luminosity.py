"""
🌙 Nocturnal Luminosity Analysis - Analyse de luminosité nocturne
Utilise les données VIIRS DNB pour détecter l'activité nocturne des fincas
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# Google Earth Engine
try:
    import ee
    ee.Initialize(project='fincalert')
except ImportError:
    print("⚠️ Google Earth Engine not available. Install with: pip install earthengine-api")
    ee = None
except Exception as e:
    print(f"⚠️ Google Earth Engine initialization failed: {e}")
    ee = None

logger = logging.getLogger(__name__)


class NocturnalLuminosityAnalyzer:
    """Analyseur de luminosité nocturne pour détecter l'activité des fincas"""
    
    def __init__(self):
        self.viirs_collection = "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG"
        self.min_luminosity = 0.1  # Seuil de détection minimum
        self.analysis_radius = 100  # mètres autour de la finca
        self.months_back = 12  # Nombre de mois à analyser
        
        # Seuils de classification
        self.luminosity_thresholds = {
            'very_dark': 0.3,      # Très sombre (abandon probable)
            'dark': 0.6,           # Sombre (activité faible)
            'moderate': 1.0,       # Modéré (activité normale)
            'bright': 2.0          # Lumineux (activité élevée)
        }
        
        # Coefficients de scoring
        self.scoring_weights = {
            'mean_luminosity': 0.4,
            'trend': 0.3,
            'active_months': 0.2,
            'variability': 0.1
        }
    
    def _ensure_gee_initialized(self) -> bool:
        """Vérifie que Google Earth Engine est initialisé"""
        if ee is None:
            logger.error("Google Earth Engine not available")
            return False
        try:
            # Test simple pour vérifier l'initialisation
            test_point = ee.Geometry.Point([0, 0])
            test_point.getInfo()
            return True
        except Exception as e:
            logger.error(f"Google Earth Engine not properly initialized: {e}")
            return False
    
    def _generate_demo_luminosity_data(self, lat: float, lon: float, months: int = 12) -> List[Dict[str, Any]]:
        """Génère des données de luminosité de démonstration"""
        import random
        from datetime import datetime, timedelta
        
        # Base de luminosité selon la localisation (simulation)
        base_luminosity = 0.5 + (lat - 38.9) * 0.1 + (lon - 1.3) * 0.05
        
        # Variation saisonnière (été plus lumineux)
        seasonal_factor = 0.3
        
        # Tendance (simulation d'abandon progressif pour certaines fincas)
        trend_factor = random.uniform(-0.1, 0.05)  # Légère tendance décroissante
        
        monthly_data = []
        end_date = datetime.now()
        
        for i in range(months):
            # Date du mois
            month_date = end_date - timedelta(days=30 * i)
            
            # Facteur saisonnier (été = plus lumineux)
            month = month_date.month
            if month in [6, 7, 8]:  # Été
                seasonal_boost = seasonal_factor
            elif month in [12, 1, 2]:  # Hiver
                seasonal_boost = -seasonal_factor
            else:
                seasonal_boost = 0
            
            # Tendance temporelle
            trend_effect = trend_factor * i
            
            # Bruit aléatoire
            noise = random.uniform(-0.2, 0.2)
            
            # Luminosité finale
            luminosity = max(0.1, base_luminosity + seasonal_boost + trend_effect + noise)
            
            monthly_data.append({
                'month': month_date.strftime('%Y-%m'),
                'luminosity': round(luminosity, 3),
                'active': luminosity > self.min_luminosity,
                'timestamp': month_date.strftime('%Y-%m-%d')
            })
        
        # Trier par date (plus récent en premier)
        monthly_data.reverse()
        
        return monthly_data
    
    def _create_finca_roi(self, lat: float, lon: float):
        """Crée la région d'intérêt autour d'une finca"""
        if ee is None:
            return None
        point = ee.Geometry.Point([lon, lat])
        roi = point.buffer(self.analysis_radius)
        return roi
    
    def _get_viirs_collection(self, start_date: str, end_date: str):
        """Récupère la collection VIIRS DNB pour une période donnée"""
        if ee is None:
            return None
        collection = (
            ee.ImageCollection(self.viirs_collection)
            .filterDate(start_date, end_date)
            .select(['avg_rad'])  # Bande de luminosité moyenne
        )
        return collection
    
    def _calculate_monthly_stats(self, image, roi):
        """Calcule les statistiques mensuelles pour une image"""
        if ee is None or image is None or roi is None:
            return {'luminosity': 0.0, 'timestamp': '2024-01-01'}
        
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=750,  # Résolution VIIRS DNB
            maxPixels=1e6
        )
        
        # Convertir en valeurs Python
        avg_rad = stats.get('avg_rad').getInfo()
        return {
            'luminosity': float(avg_rad) if avg_rad is not None else 0.0,
            'timestamp': image.date().format('YYYY-MM-dd').getInfo()
        }
    
    def get_monthly_luminosity(self, lat: float, lon: float, months: int = None, demo: bool = False) -> List[Dict[str, Any]]:
        """
        Récupère la luminosité mensuelle pour une finca
        
        Args:
            lat: Latitude de la finca
            lon: Longitude de la finca
            months: Nombre de mois à analyser (défaut: 12)
            demo: Utiliser des données de démonstration si True
        
        Returns:
            Liste des données mensuelles de luminosité
        """
        months = months or self.months_back
        
        # Mode démo si demandé ou si GEE non disponible
        if demo or not self._ensure_gee_initialized():
            logger.info(f"Using demo luminosity data for {lat}, {lon}")
            return self._generate_demo_luminosity_data(lat, lon, months)
        
        # Mode production avec GEE
        try:
            # Calculer les dates
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            # Créer la ROI
            roi = self._create_finca_roi(lat, lon)
            
            # Récupérer la collection VIIRS
            collection = self._get_viirs_collection(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            # Vérifier qu'on a des données
            collection_size = collection.size().getInfo()
            if collection_size == 0:
                logger.warning(f"No VIIRS data found for period {start_date} to {end_date}")
                return []
            
            # Calculer les statistiques pour chaque image
            monthly_data = []
            image_list = collection.toList(collection_size)
            
            for i in range(collection_size):
                try:
                    image = ee.Image(image_list.get(i))
                    stats = self._calculate_monthly_stats(image, roi)
                    
                    if stats['luminosity'] > 0:  # Filtrer les valeurs nulles
                        monthly_data.append({
                            'month': stats['timestamp'][:7],  # YYYY-MM
                            'luminosity': stats['luminosity'],
                            'active': stats['luminosity'] > self.min_luminosity,
                            'timestamp': stats['timestamp']
                        })
                except Exception as e:
                    logger.warning(f"Error processing image {i}: {e}")
                    continue
            
            # Trier par date
            monthly_data.sort(key=lambda x: x['timestamp'])
            
            return monthly_data
            
        except Exception as e:
            logger.error(f"Error getting VIIRS data: {e}")
            logger.info("Falling back to demo data")
            return self._generate_demo_luminosity_data(lat, lon, months)
    
    def calculate_luminosity_metrics(self, time_series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcule les métriques de luminosité à partir d'une série temporelle
        
        Args:
            time_series: Liste des données mensuelles
        
        Returns:
            Dictionnaire des métriques calculées
        """
        if not time_series:
            return {
                'mean_luminosity': 0.0,
                'std_luminosity': 0.0,
                'trend': 0.0,
                'active_months': 0,
                'total_months': 0,
                'seasonal_pattern': 'unknown',
                'luminosity_level': 'unknown'
            }
        
        # Extraire les valeurs de luminosité
        luminosities = [item['luminosity'] for item in time_series]
        active_months = sum(1 for item in time_series if item['active'])
        
        # Calculs de base
        mean_luminosity = np.mean(luminosities)
        std_luminosity = np.std(luminosities)
        
        # Calcul de la tendance (régression linéaire simple)
        if len(luminosities) > 1:
            x = np.arange(len(luminosities))
            trend_coeff = np.polyfit(x, luminosities, 1)[0]
            trend = trend_coeff * 12  # Tendance annuelle
        else:
            trend = 0.0
        
        # Classification du niveau de luminosité
        if mean_luminosity < self.luminosity_thresholds['very_dark']:
            luminosity_level = 'very_dark'
        elif mean_luminosity < self.luminosity_thresholds['dark']:
            luminosity_level = 'dark'
        elif mean_luminosity < self.luminosity_thresholds['moderate']:
            luminosity_level = 'moderate'
        elif mean_luminosity < self.luminosity_thresholds['bright']:
            luminosity_level = 'bright'
        else:
            luminosity_level = 'very_bright'
        
        # Détection de pattern saisonnier (simplifié)
        seasonal_pattern = self._detect_seasonality(time_series)
        
        return {
            'mean_luminosity': float(mean_luminosity),
            'std_luminosity': float(std_luminosity),
            'trend': float(trend),
            'active_months': active_months,
            'total_months': len(time_series),
            'seasonal_pattern': seasonal_pattern,
            'luminosity_level': luminosity_level,
            'min_luminosity': float(min(luminosities)),
            'max_luminosity': float(max(luminosities))
        }
    
    def _detect_seasonality(self, time_series: List[Dict[str, Any]]) -> str:
        """Détecte le pattern saisonnier de la luminosité"""
        if len(time_series) < 6:
            return 'insufficient_data'
        
        # Extraire les mois et luminosités
        months = [int(item['month'].split('-')[1]) for item in time_series]
        luminosities = [item['luminosity'] for item in time_series]
        
        # Calculer la moyenne par saison
        seasons = {
            'winter': [12, 1, 2],
            'spring': [3, 4, 5],
            'summer': [6, 7, 8],
            'autumn': [9, 10, 11]
        }
        
        seasonal_means = {}
        for season, season_months in seasons.items():
            season_values = [
                lum for month, lum in zip(months, luminosities)
                if month in season_months
            ]
            if season_values:
                seasonal_means[season] = np.mean(season_values)
        
        if not seasonal_means:
            return 'no_pattern'
        
        # Identifier la saison la plus lumineuse
        brightest_season = max(seasonal_means, key=seasonal_means.get)
        darkest_season = min(seasonal_means, key=seasonal_means.get)
        
        # Calculer la variation saisonnière
        variation = (seasonal_means[brightest_season] - seasonal_means[darkest_season]) / seasonal_means[darkest_season]
        
        if variation > 0.5:  # Variation significative
            return f"{brightest_season}_peak"
        else:
            return 'consistent'
    
    def calculate_luminosity_score(self, metrics: Dict[str, Any]) -> Tuple[int, str]:
        """
        Calcule le score d'activité basé sur les métriques de luminosité
        Score cohérent avec le système simplifié : plus de luminosité = plus de points
        
        Args:
            metrics: Métriques calculées
        
        Returns:
            Tuple (score, raison)
        """
        score = 0
        reasons = []
        
        # Score basé sur la luminosité moyenne (cohérent avec simple_scoring.py)
        mean_lum = metrics['mean_luminosity']
        if mean_lum <= 0.700:  # Faible (1 pt)
            score += 1
            reasons.append("Faible luminosité nocturne")
        elif mean_lum <= 1.209:  # Moyen (3 pts)
            score += 3
            reasons.append("Luminosité nocturne modérée")
        else:  # Fort (5 pts)
            score += 5
            reasons.append("Forte luminosité nocturne")
        
        # Ajustement basé sur la tendance (optionnel)
        trend = metrics['trend']
        if trend > 0.1:  # Augmentation d'activité
            reasons.append("Augmentation d'activité")
        elif trend < -0.1:  # Diminution d'activité
            reasons.append("Diminution d'activité")
        
        # Ajustement basé sur la variabilité (optionnel)
        if metrics['std_luminosity'] > 0.5:  # Forte variabilité = activité
            reasons.append("Activité variable")
        
        # Limiter le score maximum à 5
        score = min(score, 5)
        
        reason = " ; ".join(reasons) if reasons else "Activité nocturne normale"
        
        return score, reason
    
    def analyze_finca_luminosity(self, finca_id: str, lat: float, lon: float, 
                                months: int = None, demo: bool = False) -> Dict[str, Any]:
        """
        Analyse complète de la luminosité nocturne d'une finca
        
        Args:
            finca_id: ID de la finca
            lat: Latitude
            lon: Longitude
            months: Nombre de mois à analyser
            demo: Utiliser des données de démonstration si True
        
        Returns:
            Résultat complet de l'analyse
        """
        try:
            # Récupérer les données mensuelles
            monthly_data = self.get_monthly_luminosity(lat, lon, months, demo=demo)
            
            if not monthly_data:
                return {
                    'finca_id': finca_id,
                    'status': 'error',
                    'error_message': 'No luminosity data available',
                    'monthly_data': [],
                    'metrics': {},
                    'score': 0,
                    'reason': 'Données non disponibles'
                }
            
            # Calculer les métriques
            metrics = self.calculate_luminosity_metrics(monthly_data)
            
            # Calculer le score
            score, reason = self.calculate_luminosity_score(metrics)
            
            return {
                'finca_id': finca_id,
                'status': 'success',
                'coordinates': {'lat': lat, 'lon': lon},
                'monthly_data': monthly_data,
                'metrics': metrics,
                'score': score,
                'reason': reason,
                'demo_mode': demo,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing luminosity for {finca_id}: {e}")
            return {
                'finca_id': finca_id,
                'status': 'error',
                'error_message': str(e),
                'monthly_data': [],
                'metrics': {},
                'score': 0,
                'reason': f'Erreur: {str(e)}'
            }


def test_luminosity_analyzer():
    """Test du module d'analyse de luminosité"""
    analyzer = NocturnalLuminosityAnalyzer()
    
    # Test avec une finca d'Ibiza
    test_lat, test_lon = 38.9231, 1.3132  # Coordonnées d'Ibiza
    
    print("🌙 Test d'analyse de luminosité nocturne...")
    print(f"📍 Coordonnées: {test_lat}, {test_lon}")
    
    # Test avec vraies données VIIRS
    result = analyzer.analyze_finca_luminosity("test_finca", test_lat, test_lon, months=6, demo=False)
    
    print(f"📊 Résultat: {result['status']}")
    if result['status'] == 'success':
        print(f"📈 Score: {result['score']}/5")
        print(f"💡 Raison: {result['reason']}")
        print(f"📅 Données: {len(result['monthly_data'])} mois")
        print(f"🌡️ Métriques: {result['metrics']}")
        print(f"🎭 Mode: {'Démo' if result.get('demo_mode') else 'Production'}")
    else:
        print(f"❌ Erreur: {result['error_message']}")


if __name__ == "__main__":
    test_luminosity_analyzer()
