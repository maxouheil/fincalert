import React, { useState, useEffect } from 'react';
import { Finca, VisualAnalysisResult } from '../utils/types';

interface Props {
  selected: Finca;
  onClose: () => void;
}

// Cache global pour les vérifications Street View (exporté pour utilisation dans d'autres composants)
export const streetViewCache = new Map<string, 'available' | 'unavailable'>();

const NewPopup: React.FC<Props> = ({ selected, onClose }) => {
  const [hoverScore, setHoverScore] = useState(false);
  const [hasStreetView, setHasStreetView] = useState<'loading' | 'available' | 'unavailable'>('loading');
  const [visualAnalysis, setVisualAnalysis] = useState<VisualAnalysisResult | null>(null);
  const [loadingVisual, setLoadingVisual] = useState(false);

  // Vérification de la disponibilité Street View avec cache
  useEffect(() => {
    const fincaKey = `${selected.lat}-${selected.lon}`;
    
    // Vérifier le cache d'abord
    const cachedResult = streetViewCache.get(fincaKey);
    if (cachedResult) {
      setHasStreetView(cachedResult);
      return;
    }

    const checkStreetView = async () => {
      setHasStreetView('loading');
      
      try {
        // Vérification OFFICIELLE avec l'API Google Street View Metadata
        const metadataUrl = `https://maps.googleapis.com/maps/api/streetview/metadata?location=${selected.lat},${selected.lon}&key=AIzaSyDXkjUWbqx23PD0L_IKrF5K8xzO0N3ASLY`;
        
        console.log('🔍 Checking Street View API for:', selected.lat, selected.lon);
        console.log('📡 API URL:', metadataUrl);
        
        const response = await fetch(metadataUrl);
        const data = await response.json();
        
        console.log('📄 API Response:', data);
        
        // Google retourne status: "OK" si Street View est disponible
        const result = data.status === 'OK' ? 'available' : 'unavailable';
        
        console.log('✅ Result:', result);
        
        setHasStreetView(result);
        // Sauvegarder en cache
        streetViewCache.set(fincaKey, result);
        
      } catch (error) {
        console.error('❌ Erreur vérification Street View API:', error);
        // En cas d'erreur API, on considère comme indisponible
        setHasStreetView('unavailable');
        streetViewCache.set(fincaKey, 'unavailable');
      }
    };

    checkStreetView();
  }, [selected.lat, selected.lon]);

  // Chargement analyse visuelle YOLO
  useEffect(() => {
    const loadVisualAnalysis = async () => {
      setLoadingVisual(true);
      try {
        const response = await fetch(`http://localhost:8000/api/detection/visual-analysis/${selected.id}`);
        if (response.ok) {
          const result = await response.json();
          setVisualAnalysis(result);
          console.log('🎯 Visual analysis loaded:', result);
        } else {
          console.warn('⚠️ Visual analysis unavailable:', response.status);
        }
      } catch (error) {
        console.warn('⚠️ Visual analysis failed:', error);
      } finally {
        setLoadingVisual(false);
      }
    };

    loadVisualAnalysis();
  }, [selected.id]);

  // Calcul de la variation en pourcentage
  const variationPercent = selected.std_deviation && selected.median_ndvi && selected.median_ndvi > 0 
    ? Math.round((selected.std_deviation / selected.median_ndvi) * 100)
    : 23; // Valeur par défaut du screenshot

  // Données NDVI mensuelles (12 mois) - utilise les vraies données si disponibles
  const ndviData = selected.ndvi_timeseries && selected.ndvi_timeseries.length > 0
    ? (() => {
        // Prendre les 12 dernières périodes ou toutes si moins de 12
        const data = selected.ndvi_timeseries.slice(-12);
        return data.map((ts: any, i: number) => {
          // Extraire le mois depuis la date start_date
          const startDate = new Date(ts.start_date || ts.start);
          const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
          const month = monthNames[startDate.getMonth()];
          return {
            month,
            ndvi: ts.ndvi_value || ts.ndvi || 0.4,
            date: ts.start_date || ts.start
          };
        });
      })()
    : [
        { month: 'Jul', ndvi: 0.45, date: '2023-07-01' },
        { month: 'Aug', ndvi: 0.52, date: '2023-08-01' },
        { month: 'Sep', ndvi: 0.48, date: '2023-09-01' },
        { month: 'Oct', ndvi: 0.62, date: '2023-10-01' },
        { month: 'Nov', ndvi: 0.58, date: '2023-11-01' },
        { month: 'Dec', ndvi: 0.55, date: '2023-12-01' },
        { month: 'Jan', ndvi: 0.51, date: '2024-01-01' },
        { month: 'Feb', ndvi: 0.48, date: '2024-02-01' },
        { month: 'Mar', ndvi: 0.45, date: '2024-03-01' },
        { month: 'Apr', ndvi: 0.42, date: '2024-04-01' },
        { month: 'May', ndvi: 0.38, date: '2024-05-01' },
        { month: 'Jun', ndvi: 0.35, date: '2024-06-01' }
      ];

  const getActivityStatus = () => {
    return selected.activity_status || 'active';
  };

  const getActivityLabel = () => {
    const status = getActivityStatus();
    switch (status) {
      case 'active': return 'Active';
      case 'potential': return 'Semi-active';
      case 'inactive': return 'Inactive';
      default: return 'Unknown';
    }
  };

  const getActivityColor = () => {
    const status = getActivityStatus();
    switch (status) {
      case 'active': return { bg: 'rgba(34,197,94,0.15)', text: '#166534' };
      case 'potential': return { bg: 'rgba(251,146,60,0.2)', text: '#FB923C' };
      case 'inactive': return { bg: 'rgba(239,68,68,0.15)', text: '#DC2626' };
      default: return { bg: 'rgba(100,116,139,0.10)', text: '#64748B' };
    }
  };

  const getRiskInfo = () => {
    const score = selected.abandon_score || 50;
    if (score >= 70) return { level: 'Risque élevé', desc: 'Très probablement inactive', icon: '🔴' };
    if (score >= 40) return { level: 'Risque moyen', desc: 'Semi-active', icon: '🟡' };
    return { level: 'Risque faible', desc: 'Active - cultivation récente', icon: '🟢' };
  };

  return (
    <div style={{
      width: 280,
      borderRadius: 14,
      backgroundColor: '#FFFFFF',
      boxShadow: '0 20px 56px rgba(0,0,0,0.32)',
      filter: 'drop-shadow(0 26px 64px rgba(0,0,0,0.42))',
      overflow: 'hidden'
    }}>
      {/* Image avec label Streetview */}
      <div style={{ position: 'relative', height: 200, backgroundColor: '#F3F4F6' }}>
        <img
          src={`http://localhost:8000/api/thumbnail/${encodeURIComponent(selected.id)}?lon=${selected.lon}&lat=${selected.lat}&width=280&height=200&scale=2`}
          alt={selected.id}
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          onError={(e) => {
            const fallback = `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${selected.lon},${selected.lat},18.5,0/280x200@2x?access_token=pk.eyJ1IjoiYWxleGlzLWNyZWF0aXZlIiwiYSI6ImNsemF2MXFpcjA2OXEyaXF6aWVhaTV1cGsifQ.1hGKYC8Yr1nI4dPgG_1K7Q`;
            (e.target as HTMLImageElement).src = fallback;
          }}
        />
        {/* Bouton Streetview unifié */}
        <div style={{ position: 'absolute', top: 8, right: 8 }}>
          {hasStreetView === 'loading' ? (
            <div style={{ 
              padding: '6px 10px',
              backgroundColor: 'rgba(0,0,0,0.7)',
              color: '#FFFFFF',
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'default'
            }}>
              Streetview...
            </div>
          ) : hasStreetView === 'available' ? (
            <a
              href={`https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${selected.lat},${selected.lon}&heading=0&pitch=0`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ 
                display: 'block',
                padding: '6px 10px',
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                color: '#0F172A',
                border: '1.4px solid #0F172A',
                borderRadius: 6,
                fontSize: 11,
                fontWeight: 600,
                textDecoration: 'none',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#0F172A';
                e.currentTarget.style.color = '#FFFFFF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
                e.currentTarget.style.color = '#0F172A';
              }}
            >
              Streetview
            </a>
          ) : (
            <div style={{ 
              padding: '6px 10px',
              backgroundColor: 'rgba(0,0,0,0.7)',
              color: '#FFFFFF',
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'default'
            }}>
              Streetview unavailable
            </div>
          )}
        </div>
      </div>

      {/* Contenu */}
      <div style={{ padding: '12px 14px' }}>
        {/* Header avec titre et badge activité */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1A202C' }}>
            {selected.id}
          </div>
          <div
            style={{ position: 'relative' }}
            onMouseEnter={() => setHoverScore(true)}
            onMouseLeave={() => setHoverScore(false)}
          >
            <span style={{
              padding: '2px 8px',
              borderRadius: 999,
              fontSize: 11,
              fontWeight: 800,
              cursor: 'help',
              color: getActivityColor().text,
              backgroundColor: getActivityColor().bg
            }}>
              {getActivityLabel()}
            </span>
            {/* Tooltip hover avec score détaillé */}
            {hoverScore && selected.abandon_score && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: 4,
                backgroundColor: '#1F2937',
                color: '#FFFFFF',
                padding: '6px 8px',
                borderRadius: 6,
                fontSize: 11,
                whiteSpace: 'nowrap',
                zIndex: 1000,
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
              }}>
                {getRiskInfo().icon} {getRiskInfo().level}: {Math.round(selected.abandon_score)}/100
                <div style={{ fontSize: 10, opacity: 0.8, marginTop: 2 }}>
                  {getRiskInfo().desc}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Localisation */}
        <div style={{ fontSize: 14, color: '#4A5568', marginBottom: 6 }}>
          Sant Josep de Talaia
        </div>

        {/* Attributs */}
        <div style={{ fontSize: 12, color: '#718096', marginBottom: 12 }}>
          {Math.round(selected.surface_estimee_m2)} m² • {selected.distance_plus_proche_voisin_m}m from neighbour
        </div>

        {/* Section NDVI */}
        <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#374151' }}>
              Ndvi variation
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#1F2937' }}>
              {variationPercent}%
            </div>
          </div>

          {/* Chart NDVI full width */}
          <div style={{ marginLeft: -14, marginRight: -14, marginBottom: 8 }}>
            <svg width={280} height={60} viewBox="0 0 280 60" style={{ borderRadius: 4, display: 'block' }}>
              {(() => {
                const chartWidth = 240;
                const chartHeight = 40;
                const marginLeft = 20;
                const marginTop = 5;
                
                const points = ndviData.map((d, i) => {
                  const x = marginLeft + (i / Math.max(ndviData.length - 1, 1)) * chartWidth;
                  const y = marginTop + chartHeight - (d.ndvi - 0.2) * (chartHeight / 0.6); // Normalize 0.2-0.8 range
                  return { x, y, ndvi: d.ndvi, month: d.month, date: d.date };
                });

                // Créer un path avec courbes lisses (spline)
                const createSmoothPath = (points: any[]) => {
                  if (points.length < 2) return '';
                  
                  let path = `M ${points[0].x} ${points[0].y}`;
                  
                  for (let i = 1; i < points.length; i++) {
                    const current = points[i];
                    const previous = points[i - 1];
                    
                    // Calcul des points de contrôle pour des courbes douces
                    const cp1x = previous.x + (current.x - previous.x) * 0.3;
                    const cp1y = previous.y;
                    const cp2x = current.x - (current.x - previous.x) * 0.3;
                    const cp2y = current.y;
                    
                    path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${current.x} ${current.y}`;
                  }
                  
                  return path;
                };

                const smoothPath = createSmoothPath(points);

                return (
                  <g>
                    {/* Ligne NDVI avec courbes lisses */}
                    <path
                      d={smoothPath}
                      stroke="#22C55E"
                      strokeWidth="2"
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />

                    {/* Points interactifs */}
                    {points.map((p, i) => (
                      <circle
                        key={i}
                        cx={p.x}
                        cy={p.y}
                        r="3"
                        fill="#22C55E"
                        stroke="#FFFFFF"
                        strokeWidth="1.5"
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={(e) => {
                          const tooltip = document.createElement('div');
                          tooltip.id = 'ndvi-tooltip';
                          tooltip.style.cssText = `
                            position: absolute;
                            background: #1F2937;
                            color: white;
                            padding: 4px 6px;
                            border-radius: 4px;
                            font-size: 10px;
                            pointer-events: none;
                            z-index: 1000;
                            white-space: nowrap;
                          `;
                          tooltip.textContent = `${p.month}: ${p.ndvi.toFixed(3)}${p.date ? ` (${p.date.split('-')[1]}/${p.date.split('-')[2]})` : ''}`;
                          document.body.appendChild(tooltip);

                          const rect = e.currentTarget.getBoundingClientRect();
                          tooltip.style.left = `${rect.left + window.scrollX}px`;
                          tooltip.style.top = `${rect.top + window.scrollY - 25}px`;
                        }}
                        onMouseLeave={() => {
                          const tooltip = document.getElementById('ndvi-tooltip');
                          if (tooltip) tooltip.remove();
                        }}
                      />
                    ))}

                    {/* Labels */}
                    <text x={marginLeft} y="58" fontSize="9" fill="#9CA3AF">
                      {ndviData.length > 0 ? ndviData[0].month : 'Start'}
                    </text>
                    <text x={marginLeft + chartWidth} y="58" fontSize="9" fill="#9CA3AF" textAnchor="end">
                      {ndviData.length > 0 ? ndviData[ndviData.length - 1].month : 'End'}
                    </text>
                  </g>
                );
              })()}
            </svg>
          </div>
        </div>

        {/* Section Activité Visuelle (YOLO) */}
        <div style={{ borderTop: '1px solid #E5E7EB', paddingTop: 12, marginTop: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#374151' }}>
              Activité visuelle
            </div>
            {loadingVisual && (
              <div style={{ fontSize: 10, color: '#6B7280' }}>
                Analyse...
              </div>
            )}
          </div>

          {visualAnalysis ? (
            <div>
              {/* Indicateurs piscine */}
              {visualAnalysis.pools?.detection_result?.pool_detected && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  marginBottom: 4,
                  fontSize: 12,
                  color: '#374151'
                }}>
                  {getPoolIcon(visualAnalysis.pools.detection_result.best_pool?.state || 'unknown')}
                  <span style={{ marginLeft: 6 }}>
                    {getPoolStateLabel(visualAnalysis.pools.detection_result.best_pool?.state || 'unknown')}
                  </span>
                  <span style={{ 
                    marginLeft: 'auto', 
                    fontSize: 10, 
                    color: '#6B7280' 
                  }}>
                    {Math.round((visualAnalysis.pools.detection_result.best_pool?.confidence || 0) * 100)}%
                  </span>
                </div>
              )}

              {/* Indicateurs mobilité */}
              {visualAnalysis.mobility?.detection_result && (
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  marginBottom: 4,
                  fontSize: 12,
                  color: '#374151'
                }}>
                  {getMobilityIcon(visualAnalysis.mobility.detection_result.mobility_level)}
                  <span style={{ marginLeft: 6 }}>
                    {getMobilityLabel(visualAnalysis.mobility.detection_result.mobility_level)}
                  </span>
                  <span style={{ 
                    marginLeft: 'auto', 
                    fontSize: 10, 
                    color: '#6B7280' 
                  }}>
                    Score: {Math.round(visualAnalysis.mobility.detection_result.mobility_score * 100)}%
                  </span>
                </div>
              )}

              {/* Résumé confiance */}
              {visualAnalysis.summary && (
                <div style={{ 
                  marginTop: 8,
                  padding: '6px 8px',
                  backgroundColor: getConfidenceColor(visualAnalysis.summary.confidence).bg,
                  color: getConfidenceColor(visualAnalysis.summary.confidence).text,
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600
                }}>
                  {getConfidenceIcon(visualAnalysis.summary.confidence)} {getConfidenceLabel(visualAnalysis.summary.confidence)}
                  <span style={{ fontWeight: 400, marginLeft: 4 }}>
                    (Score visuel: {Math.round(visualAnalysis.summary.visual_score * 100)}%)
                  </span>
                </div>
              )}
            </div>
          ) : !loadingVisual ? (
            <div style={{ fontSize: 11, color: '#9CA3AF', fontStyle: 'italic' }}>
              🔍 Analyse visuelle non disponible
            </div>
          ) : null}
        </div>

      </div>
    </div>
  );
};

// Fonctions helpers pour l'analyse visuelle
const getPoolIcon = (state: string) => {
  switch (state) {
    case 'blue': return '🏊';
    case 'green': return '🟢';
    case 'empty': return '⚫';
    case 'covered': return '🔲';
    default: return '❓';
  }
};

const getPoolStateLabel = (state: string) => {
  switch (state) {
    case 'blue': return 'Piscine entretenue';
    case 'green': return 'Piscine sale';
    case 'empty': return 'Piscine vide';
    case 'covered': return 'Piscine couverte';
    default: return 'Piscine détectée';
  }
};

const getMobilityIcon = (level: string) => {
  switch (level) {
    case 'high': return '🚗';
    case 'medium': return '🚙';
    case 'low': return '🚶';
    default: return '❓';
  }
};

const getMobilityLabel = (level: string) => {
  switch (level) {
    case 'high': return 'Activité élevée';
    case 'medium': return 'Activité modérée';
    case 'low': return 'Activité faible';
    default: return 'Activité inconnue';
  }
};

const getConfidenceIcon = (confidence: string) => {
  switch (confidence) {
    case 'high': return '✅';
    case 'medium': return '⚠️';
    case 'low': return '❌';
    default: return '❓';
  }
};

const getConfidenceLabel = (confidence: string) => {
  switch (confidence) {
    case 'high': return 'Confiance élevée';
    case 'medium': return 'Confiance modérée';
    case 'low': return 'Confiance faible';
    default: return 'Confiance inconnue';
  }
};

const getConfidenceColor = (confidence: string) => {
  switch (confidence) {
    case 'high': return { bg: '#D1FAE5', text: '#065F46' };
    case 'medium': return { bg: '#FEF3C7', text: '#92400E' };
    case 'low': return { bg: '#FEE2E2', text: '#991B1B' };
    default: return { bg: '#F3F4F6', text: '#374151' };
  }
};

export default NewPopup;
