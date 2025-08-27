#!/usr/bin/env python3
"""
🔧 Intégration des Données Manquantes - VIIRS, Sentinel-1, NDVI
Script pour intégrer les données manquantes dans le GeoJSON avant le calcul des scores
"""

import os
import sys
import json
from pathlib import Path
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MissingDataIntegrator:
    """Intégrateur des données manquantes"""
    
    def __init__(self):
        """Initialiser l'intégrateur"""
        self.geojson_path = "frontend/public/data/fincas_with_cars_abandon_scores.geojson"
        self.output_path = "frontend/public/data/fincas_with_all_data.geojson"
        
        # Chemins des données
        self.luminosity_path = "data/luminosity_analysis/luminosity_all631_real_20250820_150136.json"
        self.sentinel1_path = "data/sentinel1_all_fincas_6months/sentinel1_all_fincas_6months_20250820_003359.json"
        self.ndvi_base_path = "data/ndvi"
        
        logger.info("🔧 Initialisation de l'intégrateur de données manquantes")
        logger.info(f"📂 GeoJSON source: {self.geojson_path}")
        logger.info(f"💾 Fichier de sortie: {self.output_path}")
    
    def load_luminosity_data(self) -> Dict[str, float]:
        """Charger les données de luminosité VIIRS"""
        logger.info("🌙 Chargement des données de luminosité VIIRS...")
        
        if not Path(self.luminosity_path).exists():
            logger.warning(f"⚠️ Fichier de luminosité non trouvé: {self.luminosity_path}")
            return {}
        
        with open(self.luminosity_path, 'r') as f:
            data = json.load(f)
        
        luminosity_data = {}
        for finca in data:
            finca_id = finca.get('finca_id')
            if finca_id and finca.get('status') == 'success':
                mean_luminosity = finca.get('metrics', {}).get('mean_luminosity')
                if mean_luminosity is not None:
                    luminosity_data[finca_id] = mean_luminosity
        
        logger.info(f"✅ {len(luminosity_data)} données de luminosité chargées")
        return luminosity_data
    
    def load_sentinel1_data(self) -> Dict[str, float]:
        """Charger les données Sentinel-1"""
        logger.info("📡 Chargement des données Sentinel-1...")
        
        if not Path(self.sentinel1_path).exists():
            logger.warning(f"⚠️ Fichier Sentinel-1 non trouvé: {self.sentinel1_path}")
            return {}
        
        with open(self.sentinel1_path, 'r') as f:
            data = json.load(f)
        
        sentinel1_data = {}
        for finca in data.get('fincas', []):
            finca_id = finca.get('finca_id')
            if finca_id and finca.get('status') == 'success':
                vv_mean = finca.get('sentinel1_6months', {}).get('vv_mean')
                if vv_mean is not None:
                    sentinel1_data[finca_id] = vv_mean
        
        logger.info(f"✅ {len(sentinel1_data)} données Sentinel-1 chargées")
        return sentinel1_data
    
    def load_ndvi_data(self) -> Dict[str, Dict]:
        """Charger les données NDVI"""
        logger.info("🌿 Chargement des données NDVI...")
        
        if not Path(self.ndvi_base_path).exists():
            logger.warning(f"⚠️ Dossier NDVI non trouvé: {self.ndvi_base_path}")
            return {}
        
        ndvi_data = {}
        ndvi_dirs = [d for d in Path(self.ndvi_base_path).iterdir() if d.is_dir()]
        
        for ndvi_dir in ndvi_dirs:
            finca_id = ndvi_dir.name
            summary_path = ndvi_dir / "summary.json"
            
            if summary_path.exists():
                try:
                    with open(summary_path, 'r') as f:
                        summary = json.load(f)
                    
                    median_ndvi = summary.get('summary', {}).get('median')
                    std_ndvi = summary.get('summary', {}).get('std')
                    
                    if median_ndvi is not None and std_ndvi is not None:
                        ndvi_data[finca_id] = {
                            'median_ndvi': median_ndvi,
                            'std_ndvi': std_ndvi
                        }
                except Exception as e:
                    logger.warning(f"⚠️ Erreur lecture NDVI {finca_id}: {e}")
        
        logger.info(f"✅ {len(ndvi_data)} données NDVI chargées")
        return ndvi_data
    
    def integrate_data_into_geojson(self, geojson_data: Dict, 
                                  luminosity_data: Dict[str, float],
                                  sentinel1_data: Dict[str, float],
                                  ndvi_data: Dict[str, Dict]) -> tuple:
        """Intégrer toutes les données dans le GeoJSON"""
        logger.info("🔗 Intégration des données dans le GeoJSON...")
        
        integrated_count = 0
        luminosity_integrated = 0
        sentinel1_integrated = 0
        ndvi_integrated = 0
        
        for feature in geojson_data.get('features', []):
            props = feature.get('properties', {})
            finca_id = props.get('id')
            
            if not finca_id:
                continue
            
            # Intégrer luminosité VIIRS
            if finca_id in luminosity_data:
                props['viirs_mean_luminosity'] = luminosity_data[finca_id]
                luminosity_integrated += 1
            
            # Intégrer Sentinel-1
            if finca_id in sentinel1_data:
                props['sentinel1_vv_db'] = sentinel1_data[finca_id]
                sentinel1_integrated += 1
            
            # Intégrer NDVI
            if finca_id in ndvi_data:
                ndvi_info = ndvi_data[finca_id]
                props['ndvi_median'] = ndvi_info['median_ndvi']
                props['ndvi_std_deviation'] = ndvi_info['std_ndvi']
                ndvi_integrated += 1
            
            # Compter les fincas avec au moins une donnée intégrée
            if (finca_id in luminosity_data or 
                finca_id in sentinel1_data or 
                finca_id in ndvi_data):
                integrated_count += 1
        
        logger.info(f"✅ Intégration terminée:")
        logger.info(f"   - Fincas avec données intégrées: {integrated_count}")
        logger.info(f"   - Luminosité VIIRS: {luminosity_integrated}")
        logger.info(f"   - Sentinel-1: {sentinel1_integrated}")
        logger.info(f"   - NDVI: {ndvi_integrated}")
        
        integration_stats = {
            'integrated_count': integrated_count,
            'luminosity_integrated': luminosity_integrated,
            'sentinel1_integrated': sentinel1_integrated,
            'ndvi_integrated': ndvi_integrated
        }
        
        return geojson_data, integration_stats
    
    def run_integration(self):
        """Exécuter l'intégration complète"""
        logger.info("🚀 Démarrage de l'intégration des données manquantes")
        
        try:
            # 1. Charger le GeoJSON source
            logger.info("📂 Chargement du GeoJSON source...")
            if not Path(self.geojson_path).exists():
                raise FileNotFoundError(f"GeoJSON source non trouvé: {self.geojson_path}")
            
            with open(self.geojson_path, 'r') as f:
                geojson_data = json.load(f)
            
            logger.info(f"✅ {len(geojson_data.get('features', []))} fincas chargées")
            
            # 2. Charger toutes les données manquantes
            luminosity_data = self.load_luminosity_data()
            sentinel1_data = self.load_sentinel1_data()
            ndvi_data = self.load_ndvi_data()
            
            # 3. Intégrer les données dans le GeoJSON
            updated_geojson, integration_stats = self.integrate_data_into_geojson(
                geojson_data, luminosity_data, sentinel1_data, ndvi_data
            )
            
            # 4. Sauvegarder le GeoJSON mis à jour
            logger.info("💾 Sauvegarde du GeoJSON avec données intégrées...")
            with open(self.output_path, 'w') as f:
                json.dump(updated_geojson, f, indent=2)
            
            logger.info(f"✅ GeoJSON sauvegardé: {self.output_path}")
            
            # 5. Générer un rapport
            total_fincas = len(geojson_data.get('features', []))
            report = {
                'integration_date': datetime.now().isoformat(),
                'total_fincas': total_fincas,
                'data_availability': {
                    'luminosity_viirs': len(luminosity_data),
                    'sentinel1_radar': len(sentinel1_data),
                    'ndvi_vegetation': len(ndvi_data)
                },
                'integration_summary': {
                    'luminosity_integrated': integration_stats['luminosity_integrated'],
                    'sentinel1_integrated': integration_stats['sentinel1_integrated'],
                    'ndvi_integrated': integration_stats['ndvi_integrated'],
                    'total_integrated': integration_stats['integrated_count']
                },
                'availability_percentages': {
                    'luminosity': (len(luminosity_data) / total_fincas) * 100,
                    'sentinel1': (len(sentinel1_data) / total_fincas) * 100,
                    'ndvi': (len(ndvi_data) / total_fincas) * 100
                }
            }
            
            report_path = Path("data/missing_data_integration_report.json")
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"📊 Rapport généré: {report_path}")
            
            # 6. Afficher le résumé
            logger.info(f"\n📈 RÉSUMÉ DE L'INTÉGRATION:")
            logger.info(f"🏠 Fincas totales: {total_fincas}")
            logger.info(f"🌙 Luminosité VIIRS: {integration_stats['luminosity_integrated']}/{total_fincas} ({(integration_stats['luminosity_integrated']/total_fincas)*100:.1f}%)")
            logger.info(f"📡 Sentinel-1: {integration_stats['sentinel1_integrated']}/{total_fincas} ({(integration_stats['sentinel1_integrated']/total_fincas)*100:.1f}%)")
            logger.info(f"🌿 NDVI: {integration_stats['ndvi_integrated']}/{total_fincas} ({(integration_stats['ndvi_integrated']/total_fincas)*100:.1f}%)")
            
            return {
                'geojson_path': self.output_path,
                'report_path': str(report_path),
                'data_availability': report['data_availability']
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'intégration: {e}")
            raise

def main():
    """Fonction principale"""
    integrator = MissingDataIntegrator()
    return integrator.run_integration()

if __name__ == "__main__":
    main()
