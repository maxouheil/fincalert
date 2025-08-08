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
./start-frontend.sh   # Frontend (React) sur http://localhost:3001
```

Pré-requis:
- Avoir un environnement Python virtuel `venv` (au besoin: `python3 -m venv venv`)
- Node.js et npm installés
- Fichier `.env` à la racine (ou variables d’environnement) avec au minimum:
```
REACT_APP_MAPBOX_TOKEN=...   # ou MAPBOX_TOKEN
GEE_SERVICE_ACCOUNT=...      # si vous utilisez le backend GEE
```

Logs pratiques:
```bash
tail -f backend.log frontend.log
```


### 2) Comment ça fonctionne (vue d’ensemble)

- Frontend (React, `frontend/`)
  - Charge les données de fincas depuis un GeoJSON statique servi par le frontend: `public/data/fincas_extreme_west.geojson`.
  - Affiche les points sur une carte Mapbox (style satellite) via `react-map-gl` et `mapbox-gl`.
  - Filtres interactifs (par taille et par isolement) directement côté client.
  - Une popup affiche un extrait satellite (image statique Mapbox) pour la finca sélectionnée.

- Backend (FastAPI, `backend/`)
  - Fournit des endpoints pour lire une liste de fincas (depuis un JSON statique) et pour récupérer une imagerie Sentinel via Google Earth Engine (GEE).
  - Le frontend actuel n’appelle pas l’API pour la liste; il lit un GeoJSON statique. L’endpoint satellite peut servir aux évolutions.

- Données
  - Données de démo servies par le frontend: `frontend/public/data/fincas_extreme_west.geojson`.
  - Schéma d’une finca (côté frontend):
    - `id: string`
    - `lat: number`
    - `lon: number`
    - `surface_estimee_m2: number`
    - `distance_plus_proche_voisin_m: number`
    - `qualifiee_finca: boolean`
    - `neighborhood?: string`


### 3) Flux de données côté frontend

- `frontend/src/utils/data.ts`
  - `loadFincas('/data/fincas_extreme_west.geojson')` charge le GeoJSON depuis le dossier `public`.
  - Transforme chaque feature en objet `Finca` (extraction lat/lon, arrondis simples).

- `frontend/src/App.tsx`
  - Charge les fincas au montage, stocke dans l’état React.
  - Passe la liste et la sélection à `MapView` (et potentiellement `FincaList`).

- `frontend/src/components/MapView.tsx`
  - Affiche la carte, les points, la popup.
  - Implémente les filtres côté client (voir section suivante).


### 4) Filtres et "sorting" (tri)

- Filtres (dans `MapView.tsx`):
  - Taille (`sizeFilter`):
    - S: `50 ≤ surface < 80` m²
    - M: `80 ≤ surface < 120` m²
    - L: `120 ≤ surface ≤ 150` m²
  - Isolement (`nnFilter`, distance au plus proche voisin):
    - `< 30` m
    - `30 à 60` m
    - `> 60` m

- Tri (actuel):
  - Par défaut, aucun tri spécifique n’est appliqué; l’ordre provient du fichier GeoJSON chargé.
  - Pour ajouter un tri, vous pouvez trier la liste juste après le chargement (exemples):
```ts
// Exemple: trier par surface décroissante
setFincas((items) => [...items].sort((a, b) => b.surface_estimee_m2 - a.surface_estimee_m2));

// Exemple: trier par isolement croissant
setFincas((items) => [...items].sort((a, b) => a.distance_plus_proche_voisin_m - b.distance_plus_proche_voisin_m));
```
  - Emplacement conseillé: après `loadFincas().then(setFincas)` dans `App.tsx`, ou directement dans `loadFincas` si vous voulez un ordre global.


### 5) API Backend (résumé)

- Base: `http://localhost:8000`
- `GET /` → `{ "message": "Fincalert API" }`
- `GET /api/fincas` → renvoie une liste de fincas depuis `data/fincas.json` (MVP, non utilisé par le frontend actuel).
- `GET /api/satellite/{finca_id}` → calcule une emprise autour de la finca et renvoie une URL de tuiles Map (via GEE). Nécessite une configuration GEE valide (`GEE_SERVICE_ACCOUNT`).

Notes GEE:
- `backend/satellite/sentinel.py` initialise Earth Engine avec un compte de service et compose un median composite Sentinel-2.
- Assurez-vous que `GEE_SERVICE_ACCOUNT` pointe vers le chemin de la clé JSON et que le compte a les accès nécessaires.


### 6) Configuration / Environnements

- Variables d’environnement (frontend)
  - `REACT_APP_MAPBOX_TOKEN` (ou `MAPBOX_TOKEN`) requis pour la carte et les images statiques.

- Variables d’environnement (backend & GEE)
  - `GEE_SERVICE_ACCOUNT` requis pour initialiser Earth Engine.

- Ports
  - Frontend: `3001` (configuré dans `start-frontend.sh`)
  - Backend: `8000`


### 7) Structure du projet

```
fincalert/
├── frontend/
│   ├── public/data/fincas_extreme_west.geojson
│   └── src/
│       ├── components/MapView.tsx
│       ├── components/FincaList.tsx
│       ├── utils/data.ts
│       └── utils/types.ts
├── backend/
│   ├── api/main.py
│   ├── satellite/sentinel.py
│   └── detection/
├── data/            # Données brutes / travail (non servies par le frontend)
├── start-all.sh, stop-all.sh, start-backend.sh, start-frontend.sh
└── README.md
```


### 8) Dépannage rapide

- Le frontend n’affiche pas la carte → vérifier `REACT_APP_MAPBOX_TOKEN`.
- Conflit de port → `stop-all.sh` puis relancer (`start-all.sh`).
- `uvicorn: command not found` → lancer `./start-backend.sh` (installe les deps) ou `source venv/bin/activate && pip install -r requirements.txt`.
- GEE non initialisé → vérifier `GEE_SERVICE_ACCOUNT` et les droits du compte.
