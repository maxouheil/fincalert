import React, { useEffect, useState } from 'react';
import { Finca } from '../utils/types';

interface Props {
  selected: Finca;
  onClose: () => void;
}

interface CadastreData {
  reference?: string;
  surface_m2?: number;
  creation_date?: string;
  address?: string;
  wfs_surface_m2?: number;
  wfs_surface_unit?: string;
  cadastral_surface_m2?: number;
}

// Cache global pour les vérifications Street View (exporté pour utilisation dans MapView)
export const streetViewCache = new Map<string, 'available' | 'unavailable'>();

const NewPopup: React.FC<Props> = ({ selected, onClose }) => {
  const [cadastreData, setCadastreData] = useState<CadastreData | null>(null);
  const [cadastreLoading, setCadastreLoading] = useState(false);

  // Charger les données cadastrales pour cette finca
  useEffect(() => {
    const loadCadastreData = async () => {
      setCadastreLoading(true);
      try {
        // Essayer d'abord l'API backend
        const apiResponse = await fetch(`http://localhost:8000/api/cadastral/${selected.id}`);
        if (apiResponse.ok) {
          const apiData = await apiResponse.json();
          const cadastralData = apiData.cadastral_data;
          setCadastreData({
            reference: cadastralData.vpn_data.reference,
            surface_m2: cadastralData.wfs_data.surface_m2,
            creation_date: cadastralData.wfs_data.creation_date,
            address: cadastralData.vpn_data.address,
            wfs_surface_m2: cadastralData.wfs_data.surface_m2,
            wfs_surface_unit: cadastralData.wfs_data.surface_unit,
            cadastral_surface_m2: cadastralData.vpn_data.surface_m2
          });
        } else {
          // Fallback vers le fichier GeoJSON principal mis à jour
          const response = await fetch('/data/fincas_with_abandon_scores.geojson');
          if (response.ok) {
            const data = await response.json();
            const fincaData = data.features.find((f: any) => f.properties.id === selected.id);
            if (fincaData) {
              const props = fincaData.properties;
              setCadastreData({
                reference: props.cadastral_reference,
                surface_m2: props.wfs_surface_m2,
                creation_date: props.creation_date,
                address: props.cadastral_address,
                wfs_surface_m2: props.wfs_surface_m2,
                wfs_surface_unit: props.wfs_surface_unit,
                cadastral_surface_m2: props.cadastral_surface_m2
              });
            }
          }
        }
      } catch (error) {
        console.error('Erreur chargement données cadastrales:', error);
      } finally {
        setCadastreLoading(false);
      }
    };

    loadCadastreData();
  }, [selected.id]);

  // Fonctions helper pour le scoring total sur 30 points
  const getTotalScoringStatus = () => {
    return selected.total_score_classification || 'Inactive';
  };

  const getTotalScoringColor = () => {
    const status = getTotalScoringStatus();
    switch (status) {
      case 'Active': return '#059669';
      case 'Semi-active': return '#F59E0B';
      case 'Inactive': return '#DC2626';
      default: return '#6B7280';
    }
  };

  return (
    <div style={{
      width: 280,
      borderRadius: 14,
      backgroundColor: '#FFFFFF',
      boxShadow: '0 20px 56px rgba(0,0,0,0.42)',
      filter: 'drop-shadow(0 26px 64px rgba(0,0,0,0.52))',
      overflow: 'hidden'
    }}>
      {/* Photo de la finca - AU DESSUS du titre */}
      <div style={{ width: '100%', height: 120 }}>
        <img 
          src={`/cache/${selected.id}.jpg`}
          alt={`Photo de ${selected.id}`}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
          onError={(e) => {
            // Fallback vers Mapbox direct si l'image cache n'existe pas
            const mapboxToken = process.env.REACT_APP_MAPBOX_TOKEN;
            if (mapboxToken) {
              e.currentTarget.src = `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${selected.lon},${selected.lat},18.5,0/280x200?access_token=${mapboxToken}`;
            } else {
              e.currentTarget.style.display = 'none';
            }
          }}
        />
      </div>

      {/* Contenu */}
      <div style={{ padding: '12px 14px' }}>
        {/* Header avec titre et badge statut */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1A202C' }}>
            {selected.id}
          </div>
          <span style={{
            padding: '2px 8px',
            borderRadius: 999,
            fontSize: 11,
            fontWeight: 800,
            color: '#FFFFFF',
                            backgroundColor: getTotalScoringColor()
          }}>
                          {getTotalScoringStatus()}
          </span>
        </div>

        {/* Localisation */}
        <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 4 }}>
          Sant Josep de Talaia
        </div>

        {/* Détails de la finca */}
        <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 12 }}>
          {selected.distance_plus_proche_voisin_m}m from neighbour
        </div>

        {/* Section Cadastre - Toujours affichée pour toutes les fincas */}
        <div style={{ height: 1, backgroundColor: '#E5E7EB', marginBottom: 12 }} />
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12 }}>
          {/* Surface cadastrale */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#6B7280' }}>Surface cadastrale</span>
            <span style={{ color: '#374151', fontWeight: 500 }}>
              {selected.surface_estimee_m2 ? 
                (selected.surface_estimee_m2 >= 10000 ? 
                  `${(selected.surface_estimee_m2 / 10000).toFixed(1)} ha` : 
                  `${selected.surface_estimee_m2.toFixed(0)} m²`
                ) : 
                (cadastreData && cadastreData.wfs_surface_m2 ? 
                  (cadastreData.wfs_surface_m2 >= 10000 ? 
                    `${(cadastreData.wfs_surface_m2 / 10000).toFixed(1)} ha` : 
                    `${cadastreData.wfs_surface_m2.toFixed(0)} m²`
                  ) : 
                  'Non disponible'
                )
              }
            </span>
          </div>

          {/* Date de création */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#6B7280' }}>Création cadastrale</span>
            <span style={{ color: '#374151', fontWeight: 500 }}>
              {selected.creation_date ? 
                new Date(selected.creation_date).toLocaleDateString('fr-FR', {
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric'
                }).replace(/^(\d+)/, (match) => match + ' ') : 
                (cadastreData && cadastreData.creation_date ? 
                  new Date(cadastreData.creation_date).toLocaleDateString('fr-FR', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric'
                  }).replace(/^(\d+)/, (match) => match + ' ') : 
                  'Non disponible'
                )
              }
            </span>
          </div>
        </div>

        {cadastreLoading && (
          <div style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic', marginBottom: 12 }}>
            🔍 Chargement données cadastrales...
          </div>
        )}

        {/* Ligne de séparation */}
        <div style={{ height: 1, backgroundColor: '#E5E7EB', marginBottom: 12 }} />

        {/* Section Scoring Simplifié */}
        <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
          Score simplifié
        </div>

        {selected.total_score_criteria ? (
          <div>
            {/* Critères individuels */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {/* NOUVEAU: Score total sur 20 points avec tous les critères - ORDRE D'IMPORTANCE */}
              {selected.total_score_criteria && (
                <>
                  {/* 1. Présence de voitures (5 points) - CRITÈRE PRINCIPAL */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 14 }}>🚗</span>
                      <span style={{ color: '#6B7280' }}>Présence voitures</span>
                    </div>
                    <span style={{ color: '#6B7280' }}>
                      {selected.total_score_criteria.car_presence ? `${selected.total_score_criteria.car_presence.level} • ${selected.total_score_criteria.car_presence.points}/5` : 'N/A'}
                    </span>
                  </div>

                  {/* 2. Date de création (5 points) */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 14 }}>📅</span>
                      <span style={{ color: '#6B7280' }}>Date création</span>
                    </div>
                    <span style={{ color: '#6B7280' }}>
                      {selected.total_score_criteria.creation_date ? `${selected.total_score_criteria.creation_date.level} • ${selected.total_score_criteria.creation_date.points}/5` : 'N/A'}
                    </span>
                  </div>

                  {/* 3. Entretien végétation (4 points) */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 14 }}>🌿</span>
                      <span style={{ color: '#6B7280' }}>Entretien végétation</span>
                    </div>
                    <span style={{ color: '#6B7280' }}>
                      {selected.total_score_criteria.vegetation ? `${selected.total_score_criteria.vegetation.level} • ${selected.total_score_criteria.vegetation.points}/4` : 'N/A'}
                    </span>
                  </div>

                  {/* 4. Activité radar (3 points) */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 14 }}>📡</span>
                      <span style={{ color: '#6B7280' }}>Activité radar</span>
                    </div>
                    <span style={{ color: '#6B7280' }}>
                      {selected.total_score_criteria.radar ? `${selected.total_score_criteria.radar.level} • ${selected.total_score_criteria.radar.points}/3` : 'N/A'}
                    </span>
                  </div>

                  {/* 5. Luminosité nocturne (3 points) */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ fontSize: 14 }}>🌙</span>
                      <span style={{ color: '#6B7280' }}>Luminosité nocturne</span>
                    </div>
                    <span style={{ color: '#6B7280' }}>
                      {selected.total_score_criteria.luminosite ? `${selected.total_score_criteria.luminosite.level} • ${selected.total_score_criteria.luminosite.points}/3` : 'N/A'}
                    </span>
                  </div>

                  {/* Total */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, marginTop: 4 }}>
                    <span style={{ fontWeight: 600, color: '#374151' }}>Total</span>
                    <span style={{ 
                      fontWeight: 600, 
                      color: (selected.total_score_20 || 0) > 10 ? '#059669' : (selected.total_score_20 || 0) >= 7 ? '#F59E0B' : '#DC2626'
                    }}>
                      {selected.total_score_20 || 0}/20 pts
                    </span>
                  </div>
                  
                  {/* Version du scoring */}
                  <div style={{ fontSize: 10, color: '#9CA3AF', textAlign: 'center', marginTop: 4 }}>
                    Scoring Total (5 critères sur 20 points)
                  </div>
                </>
              )}
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' }}>
            🔍 Score non disponible
          </div>
        )}
      </div>
    </div>
  );
};

export default NewPopup;
