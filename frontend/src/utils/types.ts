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
  
  // Nouvelles données visuelles YOLO
  pool_detected?: boolean;
  pool_state?: 'blue' | 'green' | 'empty' | 'covered' | 'unknown';
  pool_confidence?: number;
  mobility_score?: number;
  mobility_level?: 'high' | 'medium' | 'low' | 'unknown';
  visual_indicators?: string[];
  visual_analysis_date?: string;
}

// Types pour les résultats de détection
export interface PoolDetectionResult {
  pool_detected: boolean;
  pool_count: number;
  best_pool?: {
    state: 'blue' | 'green' | 'empty' | 'covered' | 'unknown';
    confidence: number;
    area_pixels: number;
    detected_class: string;
  };
  all_pools: any[];
  summary: string;
}

export interface MobilityDetectionResult {
  mobility_score: number;
  mobility_level: 'high' | 'medium' | 'low' | 'unknown';
  objects_t1: any[];
  objects_t2: any[];
  changes: {
    vehicles: number;
    furniture: number;
    boats: number;
    total_objects: number;
  };
  summary: string;
  time_gap_months: number;
}

export interface VisualAnalysisResult {
  finca_id: string;
  pools: {
    detection_result: PoolDetectionResult;
  };
  mobility: {
    detection_result: MobilityDetectionResult;
  };
  summary: {
    activity_indicators: string[];
    visual_score: number;
    confidence: 'high' | 'medium' | 'low';
  };
}

