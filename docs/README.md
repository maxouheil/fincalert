# 🏠 Fincalert - Système de Détection d'Abandon de Fincas

## 📋 Vue d'ensemble

Fincalert est un système complet de détection d'abandon de fincas (propriétés rurales) basé sur l'analyse multi-critères de données satellitaires et géospatiales. Le système utilise des algorithmes avancés pour évaluer l'activité des propriétés et identifier celles qui sont potentiellement abandonnées.

## 🎯 Objectif Principal

Calculer un **score d'abandon sur 20 points** indiquant la probabilité qu'une finca soit abandonnée, basé sur 5 critères distincts :

- **Score élevé (15-20)** : Finca très active
- **Score moyen (7-14)** : Finca semi-active  
- **Score faible (0-6)** : Finca inactive/abandonnée

## 🏗️ Architecture du Système

### Backend (Python)
- **API REST** : FastAPI avec endpoints pour l'analyse et la détection
- **Détection d'objets** : YOLO pour piscines et véhicules
- **Analyse satellitaire** : NDVI, Sentinel-1, VIIRS
- **Traitement d'images** : PIL, OpenCV
- **Géolocalisation** : Mapbox API

### Frontend (React + TypeScript)
- **Interface cartographique** : Mapbox GL JS
- **Visualisation** : Composants React personnalisés
- **Filtres interactifs** : Par activité, score, localisation
- **Popups détaillés** : Informations complètes par finca

## 📊 Système de Scoring (20 points)

### 🚗 Présence de Voitures (5 points) - CRITÈRE PRINCIPAL
**Source de données :** Détection YOLO via Roboflow API
- **0 véhicules** : 0/5 points (Aucune activité)
- **1-2 véhicules** : 3/5 points (Activité modérée)
- **3+ véhicules** : 5/5 points (Activité élevée)

**Technologie :** Modèle "Finca cars in Ibiza 2" (mAP@50: 77.6%)

### 📅 Date de Création Cadastrale (5 points)
**Source de données :** Données cadastrales espagnoles
- **> 20 ans** : 0/5 points (Très ancien)
- **15-20 ans** : 1/5 points (Ancien)
- **10-15 ans** : 2/5 points (Moyen)
- **5-10 ans** : 3/5 points (Récent)
- **< 5 ans** : 5/5 points (Très récent)

### 🌿 Entretien Végétation - NDVI (4 points)
**Source de données :** Analyse NDVI Sentinel-2 (6 mois)
- **Variation forte (CV ≥ 25%)** : 4/4 points (Entretien actif)
- **Variation semi (CV 15-25%)** : 2/4 points (Entretien modéré)
- **Variation faible (CV < 15%)** : 0/4 points (Entretien faible)

**Données intégrées :** 631/631 fincas avec scores NDVI complets

### 📡 Activité Radar - Sentinel-1 (3 points)
**Source de données :** Sentinel-1 VV (6 mois)
- **≤ -11.404 dB** : 1/3 points (Faible)
- **-11.404 à -10.066 dB** : 2/3 points (Moyen)
- **> -10.066 dB** : 3/3 points (Fort)

### 🌙 Luminosité Nocturne - VIIRS (3 points)
**Source de données :** VIIRS Day/Night Band
- **≤ 0.700** : 1/3 points (Faible)
- **0.700 à 1.209** : 2/3 points (Moyen)
- **> 1.209** : 3/3 points (Fort)

## 🎯 Classification Finale

### 🟢 ACTIVE (>10 points)
**Distribution actuelle :** 56.7% (358/631 fincas)
**Signification :** Finca très active avec activité humaine récente

### 🟠 SEMI-ACTIVE (7-10 points)
**Distribution actuelle :** 41.8% (264/631 fincas)
**Signification :** Finca avec activité modérée

### 🔴 INACTIVE (<7 points)
**Distribution actuelle :** 1.4% (9/631 fincas)
**Signification :** Finca inactive ou abandonnée

## 📈 Statistiques Globales

- **Fincas analysées :** 631
- **Score moyen :** 11.3/20 (56.5%)
- **Données complètes :** 100% (tous les critères disponibles)
- **Précision NDVI :** 100% (631/631 fincas)
- **Détection véhicules :** 100% (631/631 fincas)

## 🔧 Technologies Utilisées

### Détection d'Objets
- **YOLO v8** : Détection de piscines et véhicules
- **Roboflow** : API de détection cloud
- **Confidence threshold :** 20% (optimisé pour détection complète)

### Données Satellitaires
- **Sentinel-2** : NDVI (résolution 10m, 6 mois)
- **Sentinel-1** : Radar VV (résolution 10m, 6 mois)
- **VIIRS** : Luminosité nocturne (résolution 375m)

### Géolocalisation
- **Mapbox** : Images satellitaires et cartes
- **Zoom optimal :** 19 (1280x960 pixels)
- **Cache local :** Images mises en cache pour performance

## 🚀 Workflow d'Analyse

### 1. Collecte des Données
```bash
# Détection véhicules (Roboflow)
python scripts/analyze_all_fincas_vehicles_confidence20.py

# Intégration données NDVI
python scripts/extract_ndvi_scores.py

# Calcul scores totaux
python scripts/calculate_total_scores_20.py
```

### 2. Intégration des Critères
- **Véhicules** : Résultats Roboflow → GeoJSON
- **NDVI** : Fichier `combined_scoring_optimized_sentinel1.json` → GeoJSON
- **Sentinel-1** : Données 6 mois → GeoJSON
- **VIIRS** : Données luminosité → GeoJSON
- **Cadastre** : Données espagnoles → GeoJSON

### 3. Calcul Final
- **Score total** : Somme des 5 critères (0-20 points)
- **Classification** : Basée sur les barèmes définis
- **Export** : GeoJSON avec tous les scores et métadonnées

## 📁 Structure des Données

### Fichiers Principaux
```
frontend/public/data/
├── fincas_with_abandon_scores.geojson  # Données complètes (631 fincas)
├── fincas_total_scores_20.geojson      # Scores calculés
└── fincas_with_all_data.geojson        # Données intégrées
```

### Données par Finca
```json
{
  "id": "finca_00045",
  "total_score_20": 7,
  "total_score_classification": "Semi-active",
  "total_score_criteria": {
    "car_presence": {"points": 0, "level": "Aucune"},
    "creation_date": {"points": 3, "level": "Récent"},
    "vegetation": {"points": 2, "level": "Variation semi"},
    "radar": {"points": 1, "level": "Faible"},
    "luminosite": {"points": 1, "level": "Faible"}
  },
  "surface_estimee_m2": 138,
  "creation_date": "2019-12-02T00:00:00",
  "total_vehicles_detected": 0,
  "ndvi_score_old": 50,
  "viirs_mean_luminosity": 0.650,
  "sentinel1_vv_db": -12.57
}
```

## 🎨 Interface Utilisateur

### Carte Interactive
- **Points colorés** : Vert (Active), Orange (Semi-active), Rouge (Inactive)
- **Filtres** : Par classification, score, localisation
- **Zoom** : Niveaux 15-20 avec images satellitaires

### Popup Détaillé
- **Informations cadastrales** : Surface, date de création
- **Score complet** : 5 critères avec points et niveaux
- **Données brutes** : Valeurs NDVI, radar, luminosité
- **Classification** : Statut final avec description

## 🔄 Mise à Jour des Données

### Processus Automatisé
1. **Détection véhicules** : Toutes les 631 fincas
2. **Intégration NDVI** : Extraction depuis fichiers existants
3. **Calcul scores** : Application des nouveaux barèmes
4. **Export frontend** : Mise à jour des fichiers GeoJSON

### Performance
- **Temps d'analyse** : ~10 minutes pour 631 fincas
- **Parallélisation** : ThreadPoolExecutor (5 workers)
- **Cache** : Images Mapbox mises en cache localement

## 📊 Validation et Qualité

### Métriques de Performance
- **NDVI** : 100% de couverture (631/631 fincas)
- **Véhicules** : 100% de détection (631/631 fincas)
- **Sentinel-1** : 100% de couverture (631/631 fincas)
- **VIIRS** : 100% de couverture (631/631 fincas)

### Distribution Réaliste
- **Actives** : 56.7% (majorité logique pour Ibiza)
- **Semi-actives** : 41.8% (activité modérée)
- **Inactives** : 1.4% (très peu d'abandonnées)

## 🚀 Déploiement

### Backend
```bash
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm start
```

### Accès
- **Frontend** : http://localhost:3000
- **API** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs

## 📝 Notes Techniques

### Optimisations Récentes
- **Confidence threshold** : Optimisé à 20% pour détection complète
- **Zoom Mapbox** : Standardisé à 19 pour cohérence
- **Cache images** : Réduction des appels API
- **Parallélisation** : Amélioration des performances

### Données Intégrées
- **Scores NDVI** : Extraits de `combined_scoring_optimized_sentinel1.json`
- **Détection véhicules** : Roboflow API avec modèle optimisé
- **Données cadastrales** : Priorité aux données principales
- **Métadonnées** : Conservation des données brutes pour traçabilité

---

**Dernière mise à jour :** 27 août 2025
**Version :** 2.0 (Système 20 points)
**Statut :** Production avec données complètes
