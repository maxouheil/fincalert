# 🏠 Fincalert - Système de Détection d'Abandon de Fincas

## 📋 Vue d'ensemble

Fincalert est un système complet de détection d'abandon de fincas (propriétés rurales) basé sur l'analyse multi-critères de données satellitaires et géospatiales. Le système utilise des algorithmes avancés pour évaluer l'activité des propriétés et identifier celles qui sont potentiellement abandonnées.

## 🎯 Objectif Principal

Calculer un **score d'abandon sur 25 points** indiquant la probabilité qu'une finca soit abandonnée, basé sur 6 critères distincts :

- **Score élevé (≥14)** : Finca active
- **Score moyen (11-13)** : Finca semi-active  
- **Score faible (≤10)** : Finca inactive/abandonnée
- **Données manquantes** : Finca incomplète

## 🏗️ Architecture du Système

### Backend (Python)
- **API REST** : FastAPI avec endpoints pour l'analyse et la détection
- **Détection d'objets** : YOLO pour piscines et véhicules
- **Analyse satellitaire** : NDVI, Sentinel-1, VIIRS
- **Traitement d'images** : PIL, OpenCV
- **Géolocalisation** : Mapbox API
- **Système d'annotation manuelle** : API pour mise à jour des conditions de toiture

### Frontend (React + TypeScript)
- **Interface cartographique** : Mapbox GL JS
- **Visualisation** : Composants React personnalisés
- **Filtres interactifs** : Par activité, score, localisation
- **Popups détaillés** : Informations complètes par finca
- **Page d'annotation toiture** : Interface d'édition des conditions de toiture

## 📊 Système de Scoring (25 points)

### 🚗 Présence de Voitures (5 points) - CRITÈRE PRINCIPAL
**Source de données :** Détection YOLO via Roboflow API
- **0 véhicules** : 0/5 points (Aucune activité)
- **1-2 véhicules** : 3/5 points (Activité modérée)
- **3+ véhicules** : 5/5 points (Activité élevée)

**Technologie :** Modèle "Finca cars in Ibiza 2" (mAP@50: 77.6%)

### 📅 Date de Création Cadastrale (5 points)
**Source de données :** Données cadastrales espagnoles (2001-2025)
- **> 20 ans** : 0/5 points (Très ancien)
- **15-20 ans** : 1/5 points (Ancien)
- **10-15 ans** : 2/5 points (Moyen)
- **5-10 ans** : 3/5 points (Récent)
- **< 5 ans** : 5/5 points (Très récent)

### 🏠 État de la Toiture (5 points) - NOUVEAU
**Source de données :** Annotation manuelle via interface dédiée
- **Excellente** : 5/5 points (Toiture parfaite)
- **Bonne** : 4/5 points (Toiture en bon état)
- **Moyenne** : 3/5 points (Toiture correcte)
- **Mauvaise** : 1/5 points (Toiture dégradée)
- **Très mauvaise** : 0/5 points (Toiture très dégradée)

**Interface :** Page `/roof-scores` avec édition en temps réel

### 🌿 Entretien Végétation - NDVI (5 points)
**Source de données :** Analyse NDVI Sentinel-2 (6 mois)
- **Variation forte (CV ≥ 25%)** : 5/5 points (Entretien actif)
- **Variation semi (CV 15-25%)** : 3/5 points (Entretien modéré)
- **Variation faible (CV < 15%)** : 1/5 points (Entretien faible)

**Données intégrées :** 631/631 fincas avec scores NDVI complets

### 📡 Activité Radar - Sentinel-1 (3 points)
**Source de données :** Sentinel-1 VV (6 mois)
- **≤ -11.404 dB** : 1/3 points (Faible)
- **-11.404 à -10.066 dB** : 2/3 points (Moyen)
- **> -10.066 dB** : 3/3 points (Fort)

### 🌙 Luminosité Nocturne - VIIRS (2 points)
**Source de données :** VIIRS Day/Night Band
- **≤ 0.700** : 1/2 points (Faible)
- **0.700 à 1.209** : 2/2 points (Moyen)
- **> 1.209** : 2/2 points (Fort)

## 🎯 Classification Finale

### 🟢 ACTIVE (≥14 points)
**Signification :** Finca très active avec activité humaine récente

### 🟠 SEMI-ACTIVE (11-13 points)
**Signification :** Finca avec activité modérée

### 🔴 INACTIVE (≤10 points)
**Signification :** Finca inactive ou abandonnée

### ⚪ INCOMPLETE (données manquantes)
**Signification :** Finca avec données insuffisantes pour évaluation

## 🛠️ Système d'Annotation Manuelle

### Page Roof-Scores (`/roof-scores`)
- **Interface d'édition** : Dropdowns pour modifier les conditions de toiture
- **Prévisualisation** : Images des fincas pour jugement visuel
- **Mise à jour temps réel** : Sauvegarde automatique des modifications
- **Recalcul automatique** : Scores mis à jour instantanément

### API Backend
- **Endpoint** : `POST /api/update-roof-condition`
- **Fonctionnalités** : Mise à jour condition + recalcul score total
- **Validation** : Vérification des données avant sauvegarde

## 📈 Statistiques Globales

- **Fincas analysées :** 631
- **Score moyen :** ~12/25 (48%)
- **Données complètes :** 100% (tous les critères disponibles)
- **Précision NDVI :** 100% (631/631 fincas)
- **Détection véhicules :** 100% (631/631 fincas)
- **Annotations toiture :** Interface complète disponible

## 🔧 Technologies Utilisées

### Détection d'Objets
- **YOLO v8** : Détection de piscines et véhicules
- **Roboflow** : API de détection cloud
- **Confidence threshold :** 20% (optimisé pour détection complète)

### Données Satellitaires
- **Sentinel-2** : NDVI (résolution 10m, 6 mois)
- **Sentinel-1** : Radar VV (résolution 10m, 6 mois)
- **VIIRS** : Luminosité nocturne (résolution 375m)

### Interface Utilisateur
- **Mapbox GL JS** : Cartographie interactive
- **React + TypeScript** : Interface moderne et responsive
- **FastAPI** : API backend performante
- **CORS** : Configuration pour développement local

## 🚀 Démarrage Rapide

### Backend
```bash
cd backend
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm start
```

### Accès
- **Carte principale** : http://localhost:3000
- **Annotation toiture** : http://localhost:3000/roof-scores
- **API Backend** : http://localhost:8000

## 📝 Notes de Version

### Version Actuelle (Août 2025)
- ✅ Système de scoring 25 points
- ✅ Intégration condition de toiture
- ✅ Interface d'annotation manuelle
- ✅ Nouveaux seuils de classification
- ✅ Unification des couleurs dots/popup
- ✅ Cache-busting pour données fraîches
