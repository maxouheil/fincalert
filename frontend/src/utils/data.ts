import { Finca, CombinedScoringResult } from './types';

export async function loadFincas(path: string = '/data/fincas_with_abandon_scores.geojson'): Promise<Finca[]> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`Failed to load fincas: ${res.status}`);
  const geojson = await res.json();
  const features = Array.isArray(geojson.features) ? geojson.features : [];
  return features.map((f: any) => {
    const coords = f.geometry?.type === 'Point' ? f.geometry?.coordinates : undefined;
    const lat = Number(f.properties?.lat ?? coords?.[1] ?? 0);
    const lon = Number(f.properties?.lon ?? coords?.[0] ?? 0);
    // round neighbor distance to nearest 5m
    const neighborRaw = Number(f.properties?.distance_plus_proche_voisin_m ?? 0);
    const neighborRounded = Math.round(neighborRaw / 5) * 5;
    return {
      id: String(f.properties?.id ?? ''),
      lat,
      lon,
      surface_estimee_m2: Math.round(Number(f.properties?.surface_estimee_m2 ?? 0) / 5) * 5,
      distance_plus_proche_voisin_m: neighborRounded,
      qualifiee_finca: Boolean(f.properties?.qualifiee_finca ?? true),
      neighborhood: f.properties?.neighborhood,
      // Nouvelles données NDVI
      abandon_score: f.properties?.abandon_score,
      activity_status: f.properties?.activity_status,
      std_deviation: f.properties?.std_deviation,
      median_ndvi: f.properties?.median_ndvi,
      valid_periods: f.properties?.valid_periods,
      processing_duration_s: f.properties?.processing_duration_s,
      ndvi_timeseries: f.properties?.ndvi_timeseries,
    } as Finca;
  });
}

export async function loadVehicleData(path: string = '/data/vehicles_full_summary.json'): Promise<Record<string, {
  vehicle_detected: boolean;
  total_count: number;
  counts_by_class: Record<string, number>;
}>> {
  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Failed to load vehicles: ${res.status}`);
    const arr = await res.json();
    const map: Record<string, any> = {};
    for (const item of arr) {
      const id = String(item.finca_id);
      map[id] = {
        vehicle_detected: Boolean(item.vehicle_detected),
        total_count: Number(item.total_count || 0),
        counts_by_class: item.counts_by_class || {},
      };
    }
    return map;
  } catch {
    return {} as any;
  }
}

export async function loadCombinedScoringData(fincaId: string, demo: boolean = true): Promise<CombinedScoringResult | null> {
  try {
    const res = await fetch(`http://localhost:8000/api/scoring/combined/${fincaId}?demo=${demo}`);
    if (!res.ok) throw new Error(`Failed to load scoring: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.warn(`Failed to load combined scoring for ${fincaId}:`, error);
    return null;
  }
}

export async function loadOptimizedSentinel1Data(fincaId: string): Promise<any> {
  try {
    const response = await fetch('/data/combined_scoring_optimized_sentinel1.json');
    if (!response.ok) {
      throw new Error('Failed to load optimized Sentinel-1 data');
    }
    
    const data = await response.json();
    const fincaData = data.results.find((f: any) => f.finca_id === fincaId);
    
    return fincaData || null;
  } catch (error) {
    console.warn('⚠️ Failed to load optimized Sentinel-1 data:', error);
    return null;
  }
}

