## Fincalert — Guide de Documentation

### 1) Lancer le projet (dev)

- Démarrer tous les serveurs
```bash
./start-all.sh
```
- Arrêter tous les serveurs
```bash
./stop-all.sh
```
- Démarrer individuellement
```bash
./start-backend.sh    # Backend (FastAPI) sur http://localhost:8000
./start-frontend.sh   # Frontend (React) sur http://localhost:3000
```

Pré-requis:
- Avoir un environnement Python virtuel `venv` (au besoin: `python3 -m venv venv`)
- Node.js et npm installés
- Fichier `.env` dans `frontend/` avec:
```
REACT_APP_MAPBOX_TOKEN=...   # Token Mapbox requis
REACT_APP_GOOGLE_MAPS_API_KEY=...  # Pour Street View
```

Logs pratiques:
```bash
tail -f backend.log frontend.log
```


### 2) Comment ça fonctionne (vue d'ensemble)

- Frontend (React, `frontend/`)
  - Charge les données de fincas depuis un GeoJSON statique: `public/data/fincas_with_abandon_scores.geojson`.
  - Affiche les points sur une carte Mapbox (style satellite) via `react-map-gl` et `mapbox-gl`.
  - Filtres interactifs (taille, isolement, activité, Street View, piscine) directement côté client.
  - Une popup affiche les détails de la finca sélectionnée avec score d'abandon combiné et indicateurs visuels.

- Backend (FastAPI, `backend/`)
  - Fournit des endpoints pour l'analyse visuelle des fincas et la détection d'objets.
  - API de détection de piscines et d'analyse d'abandon via YOLO et traitement d'images.

- Données
  - Données principales: `frontend/public/data/fincas_with_abandon_scores.geojson` (631 fincas avec scores NDVI).
  - Données piscines: `frontend/public/data/pools_full_summary.json` (résultats de détection YOLO).
  - Données véhicules: `frontend/public/data/vehicles_full_summary.json` (détection véhicules YOLO COCO).
  - **Données de scoring simplifié**: API `/api/scoring/simple/{finca_id}` (3 critères : radar, luminosité, végétation).
  - Schéma d'une finca (côté frontend):
    - `id: string`
    - `lat: number`
    - `lon: number`
    - `surface_estimee_m2: number`
    - `distance_plus_proche_voisin_m: number`
    - `qualifiee_finca: boolean`
    - `abandon_score: number` (score NDVI 0-1)
    - `mobility_score: number` (score de mobilité)
    - `mobility_level: string` (low/medium/high)
    - `visual_indicators: object` (indicateurs visuels)
    - `visual_analysis_date: string` (date d'analyse)
    - `luminosity_score: number` (score VIIRS 1-5)
    - `luminosity_mean: number` (luminosité moyenne)
    - `luminosity_level: string` (Faible/Moyen/Fort)
    - `simple_score: number` (score global 1-15)
    - `simple_classification: string` (Active/Moderate/Inactive)
    - `radar_score: number` (score radar 1-5)
    - `luminosite_score: number` (score luminosité 1-5)
    - `vegetation_score: number` (score végétation 1-5)


### 3) Flux de données côté frontend

- `frontend/src/utils/data.ts`
  - `loadFincas('/data/fincas_with_abandon_scores.geojson')` charge le GeoJSON principal.
  - `loadPoolData('/data/pools_full_summary.json')` charge les données de détection de piscines.
  - `loadSimpleScoringData(fincaId)` charge les données de scoring simplifié.
  - Transforme chaque feature en objet `Finca` avec scores et indicateurs.

- `frontend/src/App.tsx`
  - Charge les fincas et données piscines au montage, stocke dans l'état React.
  - Passe la liste et la sélection à `MapView`.

- `frontend/src/components/MapView.tsx`
  - Affiche la carte, les points colorés par score simplifié, la popup.
  - Implémente tous les filtres côté client.

- `frontend/src/components/NewPopup.tsx`
  - Affiche les détails de la finca avec scoring simplifié à 3 critères.
  - Intègre les données radar, luminosité et végétation avec seuils optimisés.
  - **Image de la finca** : Affiche la photo satellite au-dessus du titre.
  - **Score global** : Affiche le total sur 15 points avec classification.
  - **Interface harmonisée** : Styles cohérents avec drop shadow amélioré.


### 4) Filtres et système de couleurs

- Filtres (dans `MapView.tsx`):
  - **Top 30** (bouton toggle): Affiche uniquement les 30 premières fincas
  - **Taille** (`sizeFilter`):
    - S: `50 ≤ surface < 80` m²
    - M: `80 ≤ surface < 120` m²
    - L: `120 ≤ surface ≤ 150` m²
  - **Activité** (`activityFilter`): Basé sur le scoring simplifié
    - 🟢 **Active** (≥10 pts)
    - 🟡 **Moderate** (5-9 pts)
    - 🔴 **Inactive** (<5 pts)
  - **More** (menu déroulant):
    - **Isolement** (`nnFilter`, distance au plus proche voisin):
      - `< 30` m
      - `30 à 60` m
      - `> 60` m
    - **Street View** (`streetViewFilter`):
      - Toutes / Disponible / Non disponible
    - **Piscine** (`poolFilter`):
      - Toutes / Pool (blue) / Pool (other) / No pool
    - **Véhicules** (`vehicleFilter`):
      - Toutes / Présents / Absents

- **Système de couleurs des points** (basé sur le scoring simplifié):
  - 🟢 **Vert**: `Active` (10-15 points, finca active)
  - 🟠 **Orange**: `Moderate` (5-9 points, finca moyennement active)
  - 🔴 **Rouge**: `Inactive` (1-4 points, finca inactive)

- **Données piscines** (filtrage uniquement, pas de coloration):
  - Source: `pools_full_summary.json` (631 entrées)
  - États: `blue` (piscine bleue), `green`, `empty`, `covered`, `unknown`
  - Filtre "Pool (blue)" = piscines en état `blue`
  - Filtre "Pool (other)" = piscines en autres états


### 5) Système de Scoring Simplifié (Nouveau)

- **Scoring Simplifié à 3 Critères** (1/3/5 points par critère, total sur 15):
  - **📡 Activité Radar (Sentinel-1 VV)**: Mesure l'activité radar sur 6 mois
  - **💡 Luminosité Nocturne (VIIRS)**: Indicateur d'activité humaine nocturne
  - **🌿 Entretien Végétation (NDVI)**: Variabilité de la végétation (entretien)

- **Seuils par critère**:
  - **Radar (VV en dB)**:
    - Faible (1 pt): VV ≤ -11.404 dB
    - Moyen (3 pts): -11.404 < VV ≤ -10.066 dB
    - Fort (5 pts): VV > -10.066 dB
  - **Luminosité (nW/cm²/sr)**:
    - Faible (1 pt): ≤ 0.700
    - Moyen (3 pts): 0.700 < luminosité ≤ 1.209
    - Fort (5 pts): > 1.209
  - **Végétation (CV NDVI)**:
    - Faible (1 pt): CV < 12% (peu d'entretien)
    - Moyen (3 pts): 12% ≤ CV < 25% (entretien modéré)
    - Fort (5 pts): CV ≥ 25% (beaucoup d'entretien)

- **Classification finale**:
  - **🟢 Active**: Total ≥ 10 points (finca active)
  - **🟠 Moderate**: 5 ≤ Total < 10 points (finca moyennement active)
  - **🔴 Inactive**: Total < 5 points (finca inactive)

- **Logique du scoring**:
  - **Plus de points = Moins de risque d'abandon**
  - **Radar**: Plus d'activité radar = plus de points
  - **Luminosité**: Plus de lumière nocturne = plus de points
  - **Végétation**: Plus de variation NDVI (entretien) = plus de points

- **Sources de données**:
  - **NDVI**: `data/abandon_analysis_FULL/fincas_abandon_scores_REALISTIC_*.csv`
  - **Sentinel-1**: `data/sentinel1_all_fincas_6months/*latest*.json`
  - **VIIRS**: `data/luminosity_analysis/luminosity_*latest*.json`
  - **Données intégrées**: `frontend/public/data/fincas_with_abandon_scores.geojson` (avec propriétés `luminosity_*` et `simple_*`)


### 6) API Backend (résumé)

- Base: `http://localhost:8000`
- `GET /` → `{ "message": "Fincalert API" }`
- `GET /api/detection/visual-analysis/{finca_id}` → analyse visuelle d'une finca
- `GET /api/detection/pools/{finca_id}` → détection de piscines sur une finca
- `GET /api/detection/vehicles/{finca_id}` → détection de véhicules autour d'une finca
- `GET /api/scoring/simple/{finca_id}` → scoring simplifié à 3 critères
- `GET /api/luminosity/{finca_id}` → données de luminosité VIIRS

Modules de détection:
- `backend/detection/building_detector.py` - Détection de bâtiments
- `backend/detection/yolo_pool_detector.py` - Détection de piscines YOLO
- `backend/detection/extract_fincas.py` - Extraction de fincas


### 7) Configuration / Environnements

- Variables d'environnement (frontend)
  - `REACT_APP_MAPBOX_TOKEN` requis pour la carte et les images statiques.
  - `REACT_APP_GOOGLE_MAPS_API_KEY` pour les liens Street View.

- Variables d'environnement (backend)
  - Variables pour Google Earth Engine si utilisé.

- Ports
  - Frontend: `3000` (configuré dans `start-frontend.sh`)
  - Backend: `8000`


### 8) Structure du projet

```
fincalert/
├── frontend/
│   ├── public/data/
│   │   ├── fincas_with_abandon_scores.geojson           # Données principales (631 fincas)
│   │   ├── pools_full_summary.json                      # Détection piscines (631 entrées)
│   │   ├── vehicles_full_summary.json                   # Détection véhicules (30→631 entrées)
│   │   ├── combined_scoring_optimized_sentinel1.json    # Scoring combiné optimisé (Nouveau)
│   │   └── fincas_extreme_west.geojson                  # Données brutes
│   └── src/
│       ├── components/MapView.tsx                       # Carte + filtres
│       ├── components/NewPopup.tsx                      # Popup détaillée (mis à jour)
│       ├── utils/data.ts                                # Chargement données (mis à jour)
│       └── utils/types.ts                               # Types TypeScript (mis à jour)
├── backend/
│   ├── api/main.py
│   ├── detection/                                       # Modules de détection
│   └── satellite/                                       # Traitement satellite
├── data/
│   ├── test_results/pools_full_summary.json             # Source données piscines
│   ├── test_results/vehicles_full_summary.json          # Résultats batch véhicules
│   ├── sentinel1_all_fincas_6months_optimized.json      # Données Sentinel-1 optimisées (Nouveau)
│   ├── combined_scoring_optimized_sentinel1.json        # Scoring combiné (Nouveau)
│   ├── optimized_thresholds_analysis.json               # Seuils optimisés (Nouveau)
│   └── pools/                                           # Résultats détection piscines
├── scripts/                                             # Scripts d'analyse
│   ├── batch_luminosity_analysis_all_631_real_optimized.py  # Analyse VIIRS complète optimisée
│   ├── monitor_real_luminosity_progress.py              # Monitoring temps réel VIIRS
│   ├── start_real_luminosity_analysis.sh                # Lancement analyse VIIRS
│   ├── integrate_luminosity_data.py                     # Intégration données luminosité
│   ├── fix_simple_scoring.py                            # Correction score global
│   ├── analyze_all_fincas_sentinel1_6months.py          # Analyse Sentinel-1 complète
│   ├── adjust_activity_thresholds.py                    # Optimisation des seuils
│   ├── apply_optimized_thresholds.py                    # Application des seuils
│   ├── integrate_optimized_sentinel1_scoring.py         # Intégration scoring
│   ├── monitor_all_fincas_sentinel1_6months.py          # Monitoring en temps réel
│   ├── display_optimized_integration_summary.py         # Résumé intégration
│   ├── explain_scoring_system.py                        # Explication scoring
│   ├── correct_scoring_interpretation.py                # Correction interprétation
│   └── recap_viirs_scores_top20.py                      # Récapitulatif VIIRS
└── start-all.sh, stop-all.sh, etc.
```


### 9) Dépannage rapide

- Le frontend n'affiche pas la carte → vérifier `REACT_APP_MAPBOX_TOKEN` dans `frontend/.env`.
- Conflit de port 3000 → `lsof -ti :3000 | xargs kill -9` puis relancer.
- `npm start` depuis la racine → utiliser `cd frontend && npm start`.
- Données piscines manquantes → vérifier `frontend/public/data/pools_full_summary.json`.
- Données véhicules manquantes → copier `data/test_results/vehicles_full_summary.json` vers `frontend/public/data/vehicles_full_summary.json`.
- Erreur "index.html not found" → s'assurer d'être dans `frontend/` pour `npm start`.
- **Données de scoring manquantes** → vérifier l'API `/api/scoring/simple/{finca_id}` et les sources de données NDVI/Sentinel-1/VIIRS.
- **Données de luminosité manquantes** → vérifier l'API `/api/luminosity/{finca_id}` et les fichiers `data/luminosity_analysis/`.
- **Interface des filtres** → les filtres sont maintenant organisés avec "More" pour les filtres avancés.
- **Styles des boutons** → harmonisés avec la typographie `var(--app-font)` et les ombres cohérentes.
- **Erreur npm "Missing script: dev"** → utiliser `npm start` au lieu de `npm run dev`.


### 10) Dernières modifications

- **Commit récent**: Analyse de luminosité complète et intégration système
  - **Analyse VIIRS complète** : 631/631 fincas analysées avec vraies données
  - **Cache optimisé** : 99.8% d'efficacité, ~1 minute de traitement total
  - **Intégration frontend/backend** : Données de luminosité intégrées dans GeoJSON
  - **API endpoint** `/api/luminosity/{finca_id}` ajouté
  - **Types TypeScript** mis à jour avec propriétés `luminosity_*`
  - **Interface harmonisée** : Filtres nettoyés, styles cohérents

- **Commit précédent**: Système de scoring simplifié à 3 critères
  - **Scoring simplifié** (radar + luminosité + végétation, 1/3/5 points)
  - **Classification** Active/Moderate/Inactive (10+/5-9/<5 points)
  - **Interface utilisateur** mise à jour avec popup détaillée
  - **API endpoint** `/api/scoring/simple/{finca_id}` fonctionnel
  - **Logique cohérente** : plus de points = moins de risque d'abandon

- **Commit c097b09**: Ajout du filtre "💦 Pool" branché sur `pools_full_summary.json`
  - Filtre piscine fonctionnel (All/Blue/Other/None)
  - Données de détection YOLO intégrées pour 631 fincas

### 11) Analyse de Luminosité VIIRS (Complète)

- **Analyse complète** : 631/631 fincas analysées avec succès
- **Performance optimisée** :
  - **Cache persistant** : 99.8% d'efficacité, évite les appels GEE répétés
  - **Parallélisation** : ThreadPoolExecutor avec 3 workers par défaut
  - **Temps total** : ~1 minute pour l'ensemble des 631 fincas
  - **Monitoring temps réel** : Barre de progression et statistiques détaillées

- **Intégration système** :
  - **GeoJSON mis à jour** : Propriétés `luminosity_*` ajoutées
  - **API endpoint** : `/api/luminosity/{finca_id}` pour accès direct
  - **Frontend intégré** : Données disponibles directement dans les composants
  - **Types TypeScript** : Interface `Finca` mise à jour

- **Résultats statistiques** :
  - **Score moyen** : 4.0/5 points
  - **Distribution** : 14.2% faible, 21.5% moyen, 64.3% fort
  - **Luminosité moyenne** : 2.524 nW/cm²/sr
  - **Plage** : 0.390 à 21.579 nW/cm²/sr

### 12) Interface Utilisateur (Améliorations)

- **Filtres réorganisés** :
  - **Filtres principaux** : Top 30, Taille, Activité (basé sur scoring simplifié)
  - **Filtres avancés** : Menu "More" avec Isolation, Street View, Pool, Véhicules
  - **Styles harmonisés** : Typographie `var(--app-font)`, ombres cohérentes

- **Popup améliorée** :
  - **Image de la finca** : Photo satellite au-dessus du titre
  - **Score global** : Affichage du total sur 15 points avec classification
  - **Drop shadow** : Ombre portée améliorée pour plus de profondeur
  - **Données intégrées** : Radar, luminosité, végétation directement depuis GeoJSON

- **Carte optimisée** :
  - **Couleurs cohérentes** : Même couleur au clic qu'en état normal
  - **Système de scoring** : Points colorés selon le score global simplifié
  - **Performance** : Données pré-calculées, pas d'appels API redondants

### 13) Analyse Satellite (Nouveau)

- **Sentinel-1 SAR**:
  - **Résolution**: 10m (ultra-précise)
  - **Période**: 6 mois d'analyse
  - **Métrique**: VV_mean (backscatter vertical)
  - **Avantages**: Fonctionne jour/nuit, indépendant des nuages
  - **Seuils simplifiés**:
    - `Faible (1 pt)`: VV ≤ -11.404 dB
    - `Moyen (3 pts)`: -11.404 < VV ≤ -10.066 dB
    - `Fort (5 pts)`: VV > -10.066 dB

- **VIIRS DNB** (système complet et optimisé):
  - **Résolution**: 750m
  - **Période**: 6 mois d'analyse (optimisée)
  - **Métrique**: Luminosité nocturne (nW/cm²/sr)
  - **Cache**: Système de cache persistant pour GEE
  - **Parallélisation**: ThreadPoolExecutor (3 workers par défaut)
  - **Seuils simplifiés**:
    - `Faible (1 pt)`: ≤ 0.700 nW/cm²/sr
    - `Moyen (3 pts)`: 0.700 < luminosité ≤ 1.209 nW/cm²/sr
    - `Fort (5 pts)`: > 1.209 nW/cm²/sr
  - **Résultats** : 631/631 fincas analysées, 99.8% cache efficiency

- **NDVI** (système existant):
  - **Métrique**: Indice de végétation normalisé
  - **Période**: Analyse saisonnière
  - **Utilisation**: Coefficient de variation (CV) pour l'entretien végétation
