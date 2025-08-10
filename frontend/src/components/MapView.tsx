import React, { useEffect, useMemo, useRef, useState } from 'react';
import 'mapbox-gl/dist/mapbox-gl.css';
import Map, { Source, Layer, Popup, MapRef } from 'react-map-gl';
import type { LayerProps } from 'react-map-gl';
import { Finca } from '../utils/types';
import NewPopup, { streetViewCache } from './NewPopup';

// Prefer REACT_APP_MAPBOX_TOKEN (CRA convention). Fallback to MAPBOX_TOKEN if present.
const env = process.env as unknown as Record<string, string | undefined>;
const MAPBOX_TOKEN = env.REACT_APP_MAPBOX_TOKEN || env.MAPBOX_TOKEN;

// Fallback center (Western Ibiza)
const FALLBACK_VIEW_STATE = {
  longitude: 1.3132,
  latitude: 38.9231,
  zoom: 14.0,
};

// Layer style for finca points
const fincaLayer: LayerProps = {
  id: 'finca-points',
  type: 'circle',
  paint: {
    'circle-radius': 6,
    'circle-color': [
      'case',
      ['>=', ['get', 'abandon_score'], 70], '#DC2626', // Red
      ['>=', ['get', 'abandon_score'], 40], '#FB923C', // Orange
      ['<', ['get', 'abandon_score'], 40], '#059669', // Green
      '#2B6CB0' // Default Blue
    ],
    'circle-stroke-width': 2,
    'circle-stroke-color': '#FFFFFF'
  }
};

type Props = {
  fincas: Finca[];
  selected: Finca | null;
  onSelect: (id: string) => void;
};

const MapView: React.FC<Props> = ({ fincas, selected, onSelect }) => {
  const mapRef = useRef<MapRef | null>(null);
  const [popupTick, setPopupTick] = useState(0);
  const [placeCache, setPlaceCache] = useState<Record<string, string>>({});
  const [sizeFilter, setSizeFilter] = useState<'all' | 'S' | 'M' | 'L'>('all');
  const [nnFilter, setNnFilter] = useState<'all' | '10to15' | '15to30' | 'lt30' | '30to60' | 'gt60'>('all');
  const [activityFilter, setActivityFilter] = useState<'all' | 'active' | 'semi-active' | 'inactive'>('all');
  const [streetViewFilter, setStreetViewFilter] = useState<'all' | 'available' | 'unavailable'>('all');
  const [hasCentered, setHasCentered] = useState(false);
  const [thumbLoaded, setThumbLoaded] = useState(false);
  const [top30Only, setTop30Only] = useState(false);

  // Reference areas for West Ibiza (approximate centers)
  const referenceAreas = useMemo(
    () => [
      { name: 'Cala Comte', lat: 38.9609, lon: 1.2217 },
      { name: 'Cala Bassa', lat: 38.9620, lon: 1.2460 },
      { name: 'Port des Torrent', lat: 38.9635, lon: 1.2800 },
      { name: 'Sant Agustí des Vedrà', lat: 38.9520, lon: 1.3200 },
      { name: 'Sant Josep de sa Talaia (west)', lat: 38.9210, lon: 1.3000 },
      { name: 'Cala Tarida', lat: 38.9395, lon: 1.2315 },
      { name: 'Cala Vadella', lat: 38.9145, lon: 1.2260 },
      { name: 'Es Cubells (western slopes)', lat: 38.8870, lon: 1.2740 },
    ],
    []
  );

  const toRad = (v: number) => (v * Math.PI) / 180;
  const haversineKm = (lat1: number, lon1: number, lat2: number, lon2: number) => {
    const R = 6371;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  const lookupReferenceArea = (lat: number, lon: number): string | null => {
    let best: { name: string; d: number } | null = null;
    for (const a of referenceAreas) {
      const d = haversineKm(lat, lon, a.lat, a.lon);
      if (!best || d < best.d) best = { name: a.name, d };
    }
    if (best && best.d <= 8) return best.name; // within ~8km radius
    return best ? best.name : null;
  };

  // Fonction pour vérifier Street View pour une finca
  const checkStreetViewForFinca = async (finca: Finca): Promise<'available' | 'unavailable'> => {
    const fincaKey = `${finca.lat}-${finca.lon}`;
    
    // Vérifier le cache d'abord
    const cachedResult = streetViewCache.get(fincaKey);
    if (cachedResult) {
      return cachedResult;
    }

    try {
      const metadataUrl = `https://maps.googleapis.com/maps/api/streetview/metadata?location=${finca.lat},${finca.lon}&key=AIzaSyDXkjUWbqx23PD0L_IKrF5K8xzO0N3ASLY`;
      
      const response = await fetch(metadataUrl);
      const data = await response.json();
      
      const result = data.status === 'OK' ? 'available' : 'unavailable';
      streetViewCache.set(fincaKey, result);
      return result;
      
    } catch (error) {
      console.warn('Erreur vérification Street View:', error);
      streetViewCache.set(fincaKey, 'unavailable');
      return 'unavailable';
    }
  };

  // checkAllStreetView désactivé (UI: bouton masqué)
  const checkAllStreetView = undefined as unknown as () => Promise<void>;

  const filteredFincas = useMemo(() => {
    return fincas.filter((f) => {
      // Top 30 filter (IDs finca_00001..finca_00030)
      if (top30Only) {
        const m = /^finca_(\d{5})$/.exec(f.id);
        if (!m) return false;
        const n = parseInt(m[1], 10);
        if (!(n >= 1 && n <= 30)) return false;
      }
      const area = f.surface_estimee_m2;
      const dist = f.distance_plus_proche_voisin_m;
      const activity = f.activity_status;

      let areaOk = true;
      if (sizeFilter === 'S') areaOk = area >= 50 && area < 80;
      else if (sizeFilter === 'M') areaOk = area >= 80 && area < 120;
      else if (sizeFilter === 'L') areaOk = area >= 120 && area <= 150;

      let distOk = true;
      if (nnFilter === 'lt30') distOk = dist < 30;
      else if (nnFilter === '10to15') distOk = dist >= 10 && dist < 15;
      else if (nnFilter === '15to30') distOk = dist >= 15 && dist < 30;
      else if (nnFilter === '30to60') distOk = dist >= 30 && dist <= 60;
      else if (nnFilter === 'gt60') distOk = dist > 60;
      // Ensure minimum isolation of 10m (instead of 15m)
      if (dist < 10) distOk = false;

      let activityOk = true;
      if (activityFilter !== 'all') {
        activityOk = activity === activityFilter;
      }

      let streetViewOk = true;
      if (streetViewFilter !== 'all') {
        const fincaKey = `${f.lat}-${f.lon}`;
        const streetViewStatus = streetViewCache.get(fincaKey);
        if (streetViewStatus) {
          streetViewOk = streetViewStatus === streetViewFilter;
        } else {
          // Si pas encore vérifié, on inclut dans le filtre pour permettre la vérification
          streetViewOk = true;
        }
      }

      return areaOk && distOk && activityOk && streetViewOk;
    });
  }, [fincas, sizeFilter, nnFilter, activityFilter, streetViewFilter, top30Only]);

  useEffect(() => {
    if (selected && !filteredFincas.some((f) => f.id === selected.id)) {
      onSelect(null as unknown as string);
    }
  }, [filteredFincas, onSelect, selected]);

  const geojson = useMemo(() => ({
    type: 'FeatureCollection',
    features: filteredFincas.map((f) => ({
      type: 'Feature',
      properties: { 
        id: f.id,
        abandon_score: f.abandon_score || 50,
        activity_status: f.activity_status || 'unknown'
      },
      geometry: { type: 'Point', coordinates: [f.lon, f.lat] },
    })),
  }), [filteredFincas]);

  // Compute geometric center of all fincas for initial centering
  const datasetCenter = useMemo(() => {
    if (!fincas || fincas.length === 0) return { longitude: FALLBACK_VIEW_STATE.longitude, latitude: FALLBACK_VIEW_STATE.latitude };
    const sum = fincas.reduce(
      (acc, f) => ({ lon: acc.lon + f.lon, lat: acc.lat + f.lat }),
      { lon: 0, lat: 0 }
    );
    return { longitude: sum.lon / fincas.length, latitude: sum.lat / fincas.length };
  }, [fincas]);

  // Center the map once on initial load
  useEffect(() => {
    if (hasCentered) return;
    if (mapRef.current && fincas.length) {
      const m: any = mapRef.current;
      const currentZoom = m.getZoom ? m.getZoom() : FALLBACK_VIEW_STATE.zoom;
      m.flyTo({ center: [datasetCenter.longitude, datasetCenter.latitude], zoom: currentZoom, duration: 700 });
      setHasCentered(true);
    }
  }, [datasetCenter, fincas.length, hasCentered]);

  // Reset thumbnail loading state when popup changes
  useEffect(() => {
    setThumbLoaded(false);
  }, [selected?.id, popupTick]);

  // Lazy reverse geocoding for selected finca
  useEffect(() => {
    const doFetch = async () => {
      if (!selected || !MAPBOX_TOKEN) return;
      if (placeCache[selected.id]) return;
      try {
        const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${selected.lon},${selected.lat}.json?types=neighborhood,locality,place&limit=5&language=en&access_token=${MAPBOX_TOKEN}`;
        const res = await fetch(url);
        if (!res.ok) return;
        const data = await res.json();
        const feats = Array.isArray(data?.features) ? data.features : [];
        const pick =
          feats.find((f: any) => (f?.place_type || []).includes('neighborhood')) ||
          feats.find((f: any) => (f?.place_type || []).includes('locality')) ||
          feats.find((f: any) => (f?.place_type || []).includes('place')) ||
          feats[0];
        const text = pick?.text || pick?.place_name || lookupReferenceArea(selected.lat, selected.lon) || '';
        if (text) setPlaceCache((c) => ({ ...c, [selected.id]: text }));
      } catch {}
    };
    doFetch();
  }, [selected, MAPBOX_TOKEN, placeCache]);

  if (!MAPBOX_TOKEN) {
    return (
      <div style={{ padding: 16 }}>
        Missing Mapbox token. Add REACT_APP_MAPBOX_TOKEN (or MAPBOX_TOKEN) in your .env and restart.
      </div>
    );
  }

  return (
    <Map
      ref={mapRef}
      initialViewState={{ ...FALLBACK_VIEW_STATE, longitude: datasetCenter.longitude, latitude: datasetCenter.latitude }}
      style={{ width: '100%', height: '100%' }}
      mapStyle="mapbox://styles/mapbox/satellite-v9"
      mapboxAccessToken={MAPBOX_TOKEN}
      interactiveLayerIds={[fincaLayer.id as string]}
      onMouseMove={(e) => {
        if (!mapRef.current) return;
        const m: any = mapRef.current;
          const box = [
            [e.point.x - 4, e.point.y - 4],
            [e.point.x + 4, e.point.y + 4],
          ];
          const feats = m.queryRenderedFeatures(box, { layers: [String(fincaLayer.id)] });
          const canvas = m.getCanvas?.() || m.getMap?.().getCanvas?.();
          if (canvas) canvas.style.cursor = feats && feats.length ? 'pointer' : '';
      }}
      onClick={(e) => {
        let feature = e.features && e.features.find((ft: any) => ft.layer?.id === fincaLayer.id);
        if (!feature && mapRef.current) {
          const m: any = mapRef.current;
          const box = [
            [e.point.x - 6, e.point.y - 6],
            [e.point.x + 6, e.point.y + 6],
          ];
          const feats = m.queryRenderedFeatures(box, { layers: [String(fincaLayer.id)] });
          feature = feats && feats[0];
        }
        const id = feature?.properties?.id;
        if (!id) {
          onSelect(null as unknown as string);
          return;
        }
        // Center the map on the clicked dot (100px higher to show popup fully)
        const target = fincas.find((f) => f.id === String(id));
        if (target && mapRef.current) {
          const m: any = mapRef.current;
          const currentZoom = m.getZoom ? m.getZoom() : FALLBACK_VIEW_STATE.zoom;
          
          // Calculate offset to center 100px higher
          const container = m.getContainer();
          const containerHeight = container.offsetHeight;
          const offsetPixels = 100;
          
          // Convert pixel offset to geographic offset
          const pointAtCenter = m.project([target.lon, target.lat]);
          const pointOffset = { x: pointAtCenter.x, y: pointAtCenter.y + offsetPixels };
          const centerOffset = m.unproject(pointOffset);
          
          m.flyTo({ 
            center: [centerOffset.lng, centerOffset.lat], 
            zoom: currentZoom, 
            duration: 500 
          });
        }
        if (selected?.id === String(id)) {
          setPopupTick((t) => t + 1);
        } else {
          onSelect(String(id));
        }
      }}
    >
      {/* Filters overlay */}
      <div style={{ position: 'absolute', top: 12, left: 12, zIndex: 1 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <button
            onClick={() => setTop30Only((v) => !v)}
            aria-pressed={top30Only}
            title="Afficher uniquement les 30 premières fincas"
            style={{
              padding: '6px 10px',
              borderRadius: 6,
              border: top30Only ? '2px solid #2563EB' : '1px solid #D1D5DB',
              background: top30Only ? '#EFF6FF' : '#FFFFFF',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Top 30
          </button>
          <select
            className="filter-select"
            value={sizeFilter}
            onChange={(e) => setSizeFilter(e.target.value as 'all' | 'S' | 'M' | 'L')}
            aria-label="Filter by size"
          >
            <option value="all">All sizes</option>
            <option value="S">S (50–80)</option>
            <option value="M">M (80–120)</option>
            <option value="L">L (120–150)</option>
          </select>
          <select
            className="filter-select"
            value={nnFilter}
            onChange={(e) => setNnFilter(e.target.value as 'all' | '10to15' | '15to30' | 'lt30' | '30to60' | 'gt60')}
            aria-label="Filter by isolation"
          >
            <option value="all">All isolations</option>
            <option value="10to15">10 to 15m</option>
            <option value="15to30">15 to 30m</option>
            <option value="lt30">Less than 30m</option>
            <option value="30to60">30 to 60m</option>
            <option value="gt60">More than 60m</option>
          </select>
          <select
            className="filter-select"
            value={activityFilter}
            onChange={(e) => setActivityFilter(e.target.value as 'all' | 'active' | 'semi-active' | 'inactive')}
            aria-label="Filter by activity status"
          >
            <option value="all">All activities</option>
            <option value="active">🟢 Active</option>
            <option value="semi-active">🟡 Semi-active</option>
            <option value="inactive">🔴 Inactive</option>
          </select>
          <select
            className="filter-select"
            value={streetViewFilter}
            onChange={(e) => setStreetViewFilter(e.target.value as 'all' | 'available' | 'unavailable')}
            aria-label="Filter by Street View availability"
          >
            <option value="all">All Street View</option>
            <option value="available">🗺️ Available</option>
            <option value="unavailable">🚫 Unavailable</option>
          </select>
          
          {/* Bouton Street View (masqué) */}
          <span style={{ display: 'none' }} />
        </div>
        
        {/* Barre de progression masquée */}
      </div>
      <Source id="fincas" type="geojson" data={geojson as any}>
        <Layer {...fincaLayer} />
        {selected && (
          <Layer
            id="finca-selected"
            type="circle"
            filter={["==", ["get", "id"], selected.id] as any}
            paint={{
              'circle-radius': 8,
              'circle-color': [
                'case',
                ['>=', ['get', 'abandon_score'], 70], '#DC2626', // Red
                ['>=', ['get', 'abandon_score'], 40], '#FB923C', // Orange
                ['<', ['get', 'abandon_score'], 40], '#059669', // Green
                '#2B6CB0' // Default Blue
              ],
              'circle-stroke-width': 3,
              'circle-stroke-color': '#FFFFFF',
            }}
          />
        )}
      </Source>

      {selected && (
        <Popup
          className="finca-popup"
          key={`${selected.id}-${popupTick}`}
          longitude={selected.lon}
          latitude={selected.lat - 0.0008}
          closeButton={false}
          closeOnClick={false}
          anchor="top"
          onClose={() => onSelect(null as unknown as string)}
        >
          <NewPopup selected={selected} onClose={() => onSelect(null as unknown as string)} />
        </Popup>
      )}
    </Map>
  );
};

export default MapView;