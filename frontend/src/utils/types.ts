export interface Finca {
  id: string;
  lat: number;
  lon: number;
  surface_estimee_m2: number;
  distance_plus_proche_voisin_m: number;
  qualifiee_finca: boolean;
  neighborhood?: string;
  // Nouvelles données NDVI
  abandon_score?: number;
  activity_status?: 'active' | 'potential' | 'inactive' | 'unknown';
  std_deviation?: number;
  median_ndvi?: number;
  valid_periods?: number;
  processing_duration_s?: number;
  ndvi_timeseries?: Array<{ start: string; end: string; ndvi: number | null; cloud_pct: number; thumb?: string | null }>;
}

