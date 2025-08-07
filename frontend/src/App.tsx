import React, { useEffect, useState } from 'react';
import { Box, CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import MapView from './components/MapView';
import FincaList from './components/FincaList';
import { loadFincas } from './utils/data';
import { Finca } from './utils/types';

const theme = createTheme({
  palette: {
    primary: {
      main: '#2B6CB0',
    },
    secondary: {
      main: '#38B2AC',
    },
    background: {
      default: '#F7FAFC',
    },
  },
  typography: {
    fontFamily: 'Manrope, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    h5: { fontWeight: 700 },
    h6: { fontWeight: 700 },
    body1: { fontWeight: 500 },
  },
});

const App: React.FC = () => {
  const [fincas, setFincas] = useState<Finca[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const SHOW_LIST = false;

  useEffect(() => {
    loadFincas().then(setFincas).catch(console.error);
  }, []);

  const selected = fincas.find((f) => f.id === selectedId) || null;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh' }}>
        {SHOW_LIST && (
          <Box
            sx={{
              width: '400px',
              height: '100%',
              overflow: 'auto',
              borderRight: '1px solid #E2E8F0',
            }}
          >
            <FincaList fincas={fincas} selectedId={selectedId} onSelect={setSelectedId} />
          </Box>
        )}

        {/* Right side map view */}
        <Box sx={{ flex: 1, height: '100%' }}>
          <MapView fincas={fincas} selected={selected} onSelect={setSelectedId} />
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default App;