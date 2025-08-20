import React from 'react';
import { Finca } from '../utils/types';

interface Props {
  selected: Finca;
  onClose: () => void;
}

// Cache global pour les vérifications Street View (exporté pour utilisation dans MapView)
export const streetViewCache = new Map<string, 'available' | 'unavailable'>();

const NewPopup: React.FC<Props> = ({ selected, onClose }) => {
  // Fonctions helper pour le scoring simple
  const getSimpleScoringStatus = () => {
    return selected.simple_classification || 'Inactive';
  };

  const getSimpleScoringColor = () => {
    const status = getSimpleScoringStatus();
    switch (status) {
      case 'Active': return '#059669';
      case 'Moderate': return '#F59E0B';
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
            backgroundColor: getSimpleScoringColor()
          }}>
            {getSimpleScoringStatus()}
          </span>
        </div>

        {/* Localisation */}
        <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 4 }}>
          Sant Josep de Talaia
        </div>

        {/* Détails de la finca */}
        <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 12 }}>
          {selected.surface_estimee_m2} m² • {selected.distance_plus_proche_voisin_m}m from neighbour
        </div>

        {/* Ligne de séparation */}
        <div style={{ height: 1, backgroundColor: '#E5E7EB', marginBottom: 12 }} />

        {/* Section Scoring Simplifié */}
        <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
          Score simplifié
        </div>

        {selected.simple_score ? (
          <div>
            {/* Critères individuels */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {/* Activité radar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 14 }}>📡</span>
                  <span style={{ color: '#6B7280' }}>Activité radar</span>
                </div>
                <span style={{ color: '#6B7280' }}>
                  {selected.radar_score ? `${selected.radar_score >= 4 ? 'Fort' : selected.radar_score >= 2 ? 'Moyen' : 'Faible'} • ${selected.radar_score}/5` : 'N/A'}
                </span>
              </div>

              {/* Lumière nocturne */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 14 }}>💡</span>
                  <span style={{ color: '#6B7280' }}>Lumière nocturne</span>
                </div>
                <span style={{ color: '#6B7280' }}>
                  {selected.luminosite_score ? `${selected.luminosite_score >= 4 ? 'Fort' : selected.luminosite_score >= 2 ? 'Moyen' : 'Faible'} • ${selected.luminosite_score}/5` : 'N/A'}
                </span>
              </div>

              {/* Entretien végétation */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 14 }}>🌿</span>
                  <span style={{ color: '#6B7280' }}>Entretien végétation</span>
                </div>
                <span style={{ color: '#6B7280' }}>
                  {selected.vegetation_score ? `${selected.vegetation_score >= 4 ? 'Fort' : selected.vegetation_score >= 2 ? 'Moyen' : 'Faible'} • ${selected.vegetation_score}/5` : 'N/A'}
                </span>
              </div>

              {/* Total */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, marginTop: 4 }}>
                <span style={{ fontWeight: 600, color: '#374151' }}>Total</span>
                <span style={{ 
                  fontWeight: 600, 
                  color: selected.simple_score >= 10 ? '#059669' : selected.simple_score >= 5 ? '#F59E0B' : '#DC2626'
                }}>
                  {selected.simple_score}/15 pts
                </span>
              </div>
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
