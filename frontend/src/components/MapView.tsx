import React, { useEffect, useMemo, useRef, useState } from 'react';
import 'mapbox-gl/dist/mapbox-gl.css';
import Map, { Source, Layer, Popup, MapRef } from 'react-map-gl';
import type { LayerProps } from 'react-map-gl';
import { Finca } from '../utils/types';

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
    'circle-color': '#2B6CB0',
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
  const [nnFilter, setNnFilter] = useState<'all' | 'lt30' | '30to60' | 'gt60'>('all');
  const [hasCentered, setHasCentered] = useState(false);

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

  const filteredFincas = useMemo(() => {
    return fincas.filter((f) => {
      const area = f.surface_estimee_m2;
      const dist = f.distance_plus_proche_voisin_m;

      let areaOk = true;
      if (sizeFilter === 'S') areaOk = area >= 50 && area < 80;
      else if (sizeFilter === 'M') areaOk = area >= 80 && area < 120;
      else if (sizeFilter === 'L') areaOk = area >= 120 && area <= 150;

      let distOk = true;
      if (nnFilter === 'lt30') distOk = dist < 30;
      else if (nnFilter === '30to60') distOk = dist >= 30 && dist <= 60;
      else if (nnFilter === 'gt60') distOk = dist > 60;

      return areaOk && distOk;
    });
  }, [fincas, sizeFilter, nnFilter]);

  useEffect(() => {
    if (selected && !filteredFincas.some((f) => f.id === selected.id)) {
      onSelect(null as unknown as string);
    }
  }, [filteredFincas, onSelect, selected]);

  const geojson = useMemo(() => ({
    type: 'FeatureCollection',
    features: filteredFincas.map((f) => ({
      type: 'Feature',
      properties: { id: f.id },
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
        // Center the map on the clicked dot
        const target = fincas.find((f) => f.id === String(id));
        if (target && mapRef.current) {
          const m: any = mapRef.current;
          const currentZoom = m.getZoom ? m.getZoom() : FALLBACK_VIEW_STATE.zoom;
          m.flyTo({ center: [target.lon, target.lat], zoom: currentZoom, duration: 500 });
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
        <div style={{ display: 'flex', gap: 16 }}>
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
            onChange={(e) => setNnFilter(e.target.value as 'all' | 'lt30' | '30to60' | 'gt60')}
            aria-label="Filter by isolation"
          >
            <option value="all">All isolations</option>
            <option value="lt30">Less than 30m</option>
            <option value="30to60">30 to 60m</option>
            <option value="gt60">More than 60m</option>
          </select>
        </div>
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
              'circle-color': '#2DD4BF',
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
          latitude={selected.lat}
          closeButton={false}
          closeOnClick={false}
          anchor="top"
          onClose={() => onSelect(null as unknown as string)}
        >
          <div style={{ width: 280, boxSizing: 'border-box' }}>
            <div style={{ width: 280, height: 200, margin: 0, overflow: 'hidden', borderTopLeftRadius: 12, borderTopRightRadius: 12, background: 'transparent' }}>
              <img
                src={`https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${selected.lon},${selected.lat},18.5,0/280x200@2x?access_token=${MAPBOX_TOKEN}`}
                srcSet={`https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${selected.lon},${selected.lat},18.5,0/280x200@1x?access_token=${MAPBOX_TOKEN} 1x, https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${selected.lon},${selected.lat},18.5,0/280x200@2x?access_token=${MAPBOX_TOKEN} 2x`}
                loading="eager"
                decoding="async"
                alt={selected.id}
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block', backgroundColor: 'transparent' }}
              />
            </div>
            <div style={{ background: '#FFFFFF', borderBottomLeftRadius: 12, borderBottomRightRadius: 12, padding: '12px 14px 12px' }}>
              <div style={{ fontSize: 18, fontWeight: 800, color: '#1A202C', marginBottom: 4 }}>{selected.id}</div>
              <div style={{ fontSize: 14, color: '#4A5568', marginBottom: 6 }}>
                {selected.neighborhood || placeCache[selected.id] || lookupReferenceArea(selected.lat, selected.lon) || '—'}
              </div>
              <div style={{ fontSize: 12, color: '#718096' }}>{Math.round(selected.surface_estimee_m2)} m² • {selected.distance_plus_proche_voisin_m} m from nearest neighbour</div>
            </div>
          </div>
        </Popup>
      )}
    </Map>
  );
};

export default MapView;