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
  - Une popup affiche les détails de la finca sélectionnée avec score d'abandon et indicateurs visuels.

- Backend (FastAPI, `backend/`)
  - Fournit des endpoints pour l'analyse visuelle des fincas et la détection d'objets.
  - API de détection de piscines et d'analyse d'abandon via YOLO et traitement d'images.

- Données
  - Données principales: `frontend/public/data/fincas_with_abandon_scores.geojson` (631 fincas avec scores NDVI).
  - Données piscines: `frontend/public/data/pools_full_summary.json` (résultats de détection YOLO).
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


### 3) Flux de données côté frontend

- `frontend/src/utils/data.ts`
  - `loadFincas('/data/fincas_with_abandon_scores.geojson')` charge le GeoJSON principal.
  - `loadPoolData('/data/pools_full_summary.json')` charge les données de détection de piscines.
  - Transforme chaque feature en objet `Finca` avec scores et indicateurs.

- `frontend/src/App.tsx`
  - Charge les fincas et données piscines au montage, stocke dans l'état React.
  - Passe la liste et la sélection à `MapView`.

- `frontend/src/components/MapView.tsx`
  - Affiche la carte, les points colorés par score d'abandon, la popup.
  - Implémente tous les filtres côté client.


### 4) Filtres et système de couleurs

- Filtres (dans `MapView.tsx`):
  - **Taille** (`sizeFilter`):
    - S: `50 ≤ surface < 80` m²
    - M: `80 ≤ surface < 120` m²
    - L: `120 ≤ surface ≤ 150` m²
  - **Isolement** (`nnFilter`, distance au plus proche voisin):
    - `< 30` m
    - `30 à 60` m
    - `> 60` m
  - **Activité** (`activityFilter`):
    - Toutes / Actives / Inactives
  - **Street View** (`streetViewFilter`):
    - Toutes / Disponible / Non disponible
  - **Piscine** (`poolFilter`):
    - Toutes / Pool (blue) / Pool (other) / No pool

- **Système de couleurs des points** (basé sur `abandon_score`):
  - 🟢 **Vert**: `abandon_score < 0.3` (faible abandon)
  - 🟠 **Orange**: `0.3 ≤ abandon_score < 0.6` (abandon moyen)
  - 🔴 **Rouge**: `abandon_score ≥ 0.6` (fort abandon)
  - 🔵 **Bleu**: valeur par défaut (données manquantes)

- **Données piscines** (filtrage uniquement, pas de coloration):
  - Source: `pools_full_summary.json` (631 entrées)
  - États: `blue` (piscine bleue), `green`, `empty`, `covered`, `unknown`
  - Filtre "Pool (blue)" = piscines en état `blue`
  - Filtre "Pool (other)" = piscines en autres états


### 5) API Backend (résumé)

- Base: `http://localhost:8000`
- `GET /` → `{ "message": "Fincalert API" }`
- `GET /api/detection/visual-analysis/{finca_id}` → analyse visuelle d'une finca
- `GET /api/detection/pools/{finca_id}` → détection de piscines sur une finca

Modules de détection:
- `backend/detection/building_detector.py` - Détection de bâtiments
- `backend/detection/yolo_pool_detector.py` - Détection de piscines YOLO
- `backend/detection/extract_fincas.py` - Extraction de fincas


### 6) Configuration / Environnements

- Variables d'environnement (frontend)
  - `REACT_APP_MAPBOX_TOKEN` requis pour la carte et les images statiques.
  - `REACT_APP_GOOGLE_MAPS_API_KEY` pour les liens Street View.

- Variables d'environnement (backend)
  - Variables pour Google Earth Engine si utilisé.

- Ports
  - Frontend: `3000` (configuré dans `start-frontend.sh`)
  - Backend: `8000`


### 7) Structure du projet

```
fincalert/
├── frontend/
│   ├── public/data/
│   │   ├── fincas_with_abandon_scores.geojson  # Données principales (631 fincas)
│   │   ├── pools_full_summary.json             # Détection piscines (631 entrées)
│   │   └── fincas_extreme_west.geojson         # Données brutes
│   └── src/
│       ├── components/MapView.tsx              # Carte + filtres
│       ├── components/NewPopup.tsx             # Popup détaillée
│       ├── utils/data.ts                       # Chargement données
│       └── utils/types.ts                      # Types TypeScript
├── backend/
│   ├── api/main.py
│   ├── detection/                              # Modules de détection
│   └── satellite/                              # Traitement satellite
├── data/
│   ├── test_results/pools_full_summary.json    # Source données piscines
│   └── pools/                                  # Résultats détection piscines
├── scripts/                                    # Scripts d'analyse
└── start-all.sh, stop-all.sh, etc.
```


### 8) Dépannage rapide

- Le frontend n'affiche pas la carte → vérifier `REACT_APP_MAPBOX_TOKEN` dans `frontend/.env`.
- Conflit de port 3000 → `lsof -ti :3000 | xargs kill -9` puis relancer.
- `npm start` depuis la racine → utiliser `cd frontend && npm start`.
- Données piscines manquantes → vérifier `frontend/public/data/pools_full_summary.json`.
- Erreur "index.html not found" → s'assurer d'être dans `frontend/` pour `npm start`.

### 9) Dernières modifications

- **Commit c097b09**: Ajout du filtre "💦 Pool" branché sur `pools_full_summary.json`
  - Filtre piscine fonctionnel (All/Blue/Other/None)
  - Couleurs des points inchangées (système NDVI vert/orange/rouge)
  - Données de détection YOLO intégrées pour 631 fincas
