import { Finca } from './types';

export async function loadFincas(path: string = '/data/fincas_extreme_west.geojson'): Promise<Finca[]> {
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
    } as Finca;
  });
}

