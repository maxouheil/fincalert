export interface Finca {
  id: string;
  lat: number;
  lon: number;
  surface_estimee_m2: number;
  distance_plus_proche_voisin_m: number;
  qualifiee_finca: boolean;
  neighborhood?: string;
}

