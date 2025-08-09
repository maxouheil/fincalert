# Fincalert MVP

Fincalert is a tool for detecting and mapping isolated fincas in Western Ibiza using satellite imagery.

For a complete documentation guide, see `docs/README.md`.

## Features

### Core Functionality
- Automatic detection of isolated buildings (fincas) using satellite imagery
- Interactive map visualization with Airbnb-style interface
- Advanced NDVI-based abandonment score calculation (0-100 scale)
- Machine learning classification: Active, Semi-active, Inactive fincas

### Map & Visualization
- **Dynamic Dot Colors**: Green (active), Orange (semi-active), Red (inactive) based on abandonment scores
- **Multi-level Filtering**: Size, isolation, activity status, and Street View availability
- **Smart Popup System**: Detailed finca information with NDVI history charts
- **Centered Navigation**: Click-to-center with popup positioning optimization

### NDVI Analysis Engine
- **Real-time NDVI Processing**: 12-month vegetation analysis using Sentinel-2 data
- **Sophisticated Scoring Algorithm**: Combines median NDVI, coefficient of variation, vegetation dips, and green persistence
- **Statistical Insights**: Standard deviation, variation percentages, and temporal patterns
- **Visual Charts**: Interactive NDVI evolution graphs with hover details

### Street View Integration
- **Google Street View API**: Real availability checking for each finca
- **Batch Processing**: "Check All Street View" button for complete dataset verification
- **Smart Caching**: Persistent results to avoid redundant API calls
- **Progress Tracking**: Real-time progress bar with batch processing (10 concurrent requests)
- **Filter Integration**: Filter fincas by Street View availability

### Enhanced UI/UX
- **Modern Popup Design**: Redesigned finca popups with structured sections
- **Activity Badges**: Visual status indicators with hover tooltips
- **Responsive Charts**: SVG-based NDVI charts with smooth curves and interactive tooltips
- **Unified Streetview CTA**: Context-aware button positioning and states

## Technical Stack

- **Frontend**: React 18 + TypeScript + Mapbox GL + SVG Charts
- **Backend**: Python + FastAPI + Google Earth Engine (GEE)
- **Satellite Data**: Sentinel-2 NDVI analysis via Google Earth Engine
- **Building Detection**: Microsoft Building Footprints API
- **APIs**: Google Street View Static API for availability checking
- **Data Processing**: Advanced statistical algorithms for vegetation analysis

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
GOOGLE_STREETVIEW_API_KEY=your_google_api_key
```

**Note**: The Google Street View API key should have the "Street View Static API" enabled for finca availability checking.

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

## Recent Updates (Latest Release)

### 🚀 Major Features Added:
- **NDVI Abandonment Scoring**: Advanced algorithm using Coefficient of Variation, vegetation dips, and statistical analysis
- **Street View Integration**: Google API integration with batch processing and smart caching
- **Dynamic Map Visualization**: Real-time color coding based on abandonment scores
- **Enhanced Popup System**: Redesigned UI with NDVI charts, activity badges, and Street View CTAs
- **Multi-dimensional Filtering**: Activity status and Street View availability filters
- **Batch Operations**: "Check All Street View" with progress tracking

### 📊 Algorithm Improvements:
- Realistic distribution: ~46% Active, 38% Semi-active, 16% Abandoned
- CV-based classification with median NDVI and dips analysis
- 12-month temporal NDVI analysis with statistical validation

### 🎨 UI/UX Enhancements:
- Interactive NDVI evolution charts with hover tooltips
- Smooth curve rendering with spline interpolation
- Context-aware Street View availability checking
- Progress bars and real-time status updates

## Development Status

**Current Version**: Enhanced MVP with full NDVI analysis and Street View integration
**Next Phase**: Advanced analytics dashboard and reporting features