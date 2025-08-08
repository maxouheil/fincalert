# Fincalert MVP

Fincalert is a tool for detecting and mapping isolated fincas in Western Ibiza using satellite imagery.

For a complete documentation guide, see `docs/README.md`.

## Features

- Automatic detection of isolated buildings (fincas) using satellite imagery
- Interactive map visualization with Airbnb-style interface
- Building filtering based on size and isolation criteria
- Satellite imagery integration for visual verification

## Technical Stack

- Frontend: React + Mapbox GL
- Backend: Python + FastAPI
- Satellite Data: Sentinel-2 via Google Earth Engine
- Building Detection: Microsoft Building Footprints API

## Quick Start

### Start all servers at once
```bash
./start-all.sh
```

This will start:
- Backend API on http://localhost:8000
- Frontend on http://localhost:3001

### Stop all servers
```bash
./stop-all.sh
```

### Start servers individually
```bash
# Backend only
./start-backend.sh

# Frontend only  
./start-frontend.sh
```

## Manual Setup (if needed)

### Frontend
```bash
cd frontend
npm install
PORT=3001 npm start
```

### Backend
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
export PYTHONPATH=$(pwd)/backend
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Variables
Create a `.env` file with:
```
MAPBOX_TOKEN=your_mapbox_token
GEE_SERVICE_ACCOUNT=your_gee_service_account.json
```

## Project Structure

```
fincalert/
├── frontend/           # React application
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── utils/
├── backend/            # Python processing scripts
│   ├── satellite/      # Satellite data processing
│   ├── detection/      # Building detection
│   └── api/           # FastAPI endpoints
└── data/              # GeoJSON and processed data
```

## Development Status

Current MVP (Phase 1) focuses on:
- Basic building detection
- Size and isolation filtering
- Interactive map visualization
- List view of detected fincas