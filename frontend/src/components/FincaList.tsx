import React from 'react';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  Typography,
  Paper,
  Button,
} from '@mui/material';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import SquareFootIcon from '@mui/icons-material/SquareFoot';
import SocialDistanceIcon from '@mui/icons-material/SocialDistance';
import { Finca } from '../utils/types';

type Props = {
  fincas: Finca[];
  selectedId: string | null;
  onSelect: (id: string) => void;
};

const FincaList: React.FC<Props> = ({ fincas, selectedId, onSelect }) => {
  const listRef = React.useRef<HTMLUListElement | null>(null);
  const itemRefs = React.useRef<Record<string, HTMLLIElement | null>>({});

  React.useEffect(() => {
    if (selectedId && itemRefs.current[selectedId]) {
      itemRefs.current[selectedId]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [selectedId]);

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" sx={{ mb: 3 }}>
        Fincas Détectées
      </Typography>
      
      <List ref={listRef}>
        {fincas.map((finca) => (
          <Paper
            key={finca.id}
            elevation={1}
            sx={{ mb: 2, overflow: 'hidden', border: finca.id === selectedId ? '2px solid #2B6CB0' : undefined }}
          >
            <ListItem
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-start',
                p: 2,
              }}
              onClick={() => onSelect(finca.id)}
              ref={(el: HTMLLIElement | null) => { itemRefs.current[finca.id] = el; }}
            >
              <ListItemText
                primary={
                  <Typography variant="h6">
                    {finca.id}
                  </Typography>
                }
              />
              
              <Box sx={{ mt: 1, width: '100%' }}>
                {/* Thumbnail image */}
                <Box sx={{
                  width: '100%',
                  height: 120,
                  mb: 1.5,
                  borderRadius: 1,
                  overflow: 'hidden',
                  backgroundColor: '#E2E8F0'
                }}>
                  <img
                    src={`https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${finca.lon},${finca.lat},19,0/600x360?access_token=${process.env.REACT_APP_MAPBOX_TOKEN}`}
                    alt={finca.id}
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    loading="lazy"
                  />
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <LocationOnIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography>
                    {finca.neighborhood ?? '—'}
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <SquareFootIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography>
                    {finca.surface_estimee_m2} m²
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <SocialDistanceIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography>
                    {finca.distance_plus_proche_voisin_m}m du voisin le plus proche
                  </Typography>
                </Box>
                
                <Button
                  variant="contained"
                  color="primary"
                  fullWidth
                  onClick={() => {
                    onSelect(finca.id);
                  }}
                >
                  Voir Image Satellite
                </Button>
              </Box>
            </ListItem>
          </Paper>
        ))}
      </List>
    </Box>
  );
};

export default FincaList;