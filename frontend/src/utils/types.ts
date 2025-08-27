export interface Finca {
  id: string;
  lat: number;
  lon: number;
  surface_estimee_m2: number;
  distance_plus_proche_voisin_m: number;
  qualifiee_finca: boolean;
  neighborhood?: string;
  creation_date?: string; // Date de création cadastrale
  
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
  
  // Nouvelles données de luminosité nocturne VIIRS
  luminosity_score?: number;
  luminosity_mean?: number;
  luminosity_level?: string;
  luminosity_reason?: string;
  luminosity_trend?: number;
  luminosity_seasonal?: string;
  
  // Score global simplifié (/15)
  simple_score?: number;
  simple_classification?: string;
  radar_score?: number;
  luminosite_score?: number;
  vegetation_score?: number;
  cv_percent?: number;
  
  // Score V3 avec bonus d'ancienneté (/20)
  simple_score_v3?: number;
  simple_classification_v3?: string;
  simple_base_total_v3?: number;
  simple_age_bonus_v3?: number;
  
  // NOUVEAU: Score total sur 20 points avec tous les critères
  total_score_20?: number;
  total_score_classification?: 'Active' | 'Semi-active' | 'Inactive';
  total_score_criteria?: {
    luminosite?: {
      points: number;
      level: string;
      description: string;
    };
    radar?: {
      points: number;
      level: string;
      description: string;
    };
    vegetation?: {
      points: number;
      level: string;
      description: string;
    };
    creation_date?: {
      points: number;
      level: string;
      description: string;
    };

    car_presence?: {
      points: number;
      level: string;
      description: string;
    };
  };
  
  // Données brutes pour les nouveaux critères
  viirs_mean_luminosity?: number;
  sentinel1_vv_db?: number;
  ndvi_median?: number;
  ndvi_std_deviation?: number;
  total_vehicles_detected?: number;
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

export interface VehicleDetectionSummary {
  vehicle_detected: boolean;
  total_count: number;
  counts_by_class: Record<string, number>;
  best_vehicle: {
    class: string;
    confidence: number;
    bbox: [number, number, number, number];
    area_pixels?: number;
  } | null;
  all_vehicles: Array<{
    class: string;
    confidence: number;
    bbox: [number, number, number, number];
    area_pixels?: number;
  }>;
  summary: string;
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

// Types pour le système de scoring d'abandon
export interface VehicleHistoryEntry {
  date: string;
  vehicles_detected: boolean;
  count: number;
  classes: Record<string, number>;
  finca_id: string;
}

export interface NDVIData {
  variation_percent: number;
  mean_ndvi: number;
  min_ndvi?: number;
  max_ndvi?: number;
}

export interface VehicleScore {
  score: number;
  reason: string;
  details: {
    images_with_vehicles: number;
    total_images: number;
    vehicle_ratio: number;
  };
}

export interface NDVIScore {
  score: number;
  reason: string;
  details: {
    variation_percent: number;
    mean_ndvi: number;
  };
}

export interface CombinedAbandonmentScore {
  total_score: number;
  abandonment_level: 'high' | 'medium' | 'low' | 'none';
  level_description: string;
  vehicle_score: VehicleScore;
  ndvi_score: NDVIScore;
  max_possible_score: number;
}

export interface CombinedScoringResult {
  finca_id: string;
  demo: boolean;
  scoring_result: CombinedAbandonmentScore;
  // Nouvelles propriétés Sentinel-1 et VIIRS
  sentinel1_activity_level?: string;
  activity_score?: number;
  viirs_activity_level?: string;
  viirs_score?: number;
}

// Types pour les données Sentinel-1 optimisées
export interface Sentinel1OptimizedData {
  vv_mean: number;
  activity_level: 'Très élevée' | 'Élevée' | 'Modérée' | 'Faible' | 'Très faible';
  score: number;
  period: string;
  images_count?: number;
  date_range?: {
    start: string;
    end: string;
  };
}

export interface NDVIOptimizedData {
  score: number;
  status: string;
  median_ndvi: number;
  risk_category: string;
}

export interface CombinedScoringOptimized {
  overall_score: number;
  abandonment_level: 'Très faible' | 'Faible' | 'Modéré' | 'Élevé' | 'Très élevé';
  weights_used: {
    ndvi: number;
    sentinel1: number;
  };
  components: {
    ndvi: NDVIOptimizedData;
    sentinel1: Sentinel1OptimizedData;
  };
}

export interface FincaOptimizedData {
  finca_id: string;
  coordinates: {
    lat: number;
    lon: number;
  };
  combined_scoring: CombinedScoringOptimized;
}

// Types pour le système de scoring simple
export interface SimpleScoringCriteria {
  level: 'Faible' | 'Moyen' | 'Fort';
  points: 1 | 3 | 5;
}

export interface SimpleScoringThresholds {
  viirs: {
    low_max: number;
    medium_max: number;
  };
  radar: {
    low_max_db: number;
    medium_max_db: number;
  };
  ndvi: {
    active_max: number;
    moderate_max: number;
  };
}

export interface SimpleScoringResult {
  criteria: {
    luminosite: SimpleScoringCriteria;
    radar: SimpleScoringCriteria;
    entretien_vegetation: SimpleScoringCriteria;
  };
  total_points: number;
  out_of: number;
  classification: 'Inactive' | 'Moderate' | 'Active';
  thresholds: SimpleScoringThresholds;
}

export interface SimpleScoringResponse {
  finca_id: string;
  data_available: {
    ndvi: boolean;
    sentinel1: boolean;
    viirs: boolean;
  };
  simple_scoring: SimpleScoringResult;
}

// Types pour les données NDVI 631 fincas
export interface NDVI631Finca {
  finca_id: string;
  median_ndvi: number;
  std_deviation: number;
  cv_percent: number;
  abandon_score: number;
  activity_status: 'active' | 'semi-active' | 'inactive';
  valid_periods: number;
}

export interface NDVI631Response {
  total_fincas: number;
  data_source: string;
  fincas: NDVI631Finca[];
}

