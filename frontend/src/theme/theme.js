import { createTheme } from '@mui/material/styles';

// Central MUI theme. Light, professional palette; mobile-first defaults.
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#1565c0' },
    secondary: { main: '#00897b' },
    background: { default: '#f5f7fa' },
  },
  shape: { borderRadius: 10 },
  typography: {
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
});

export default theme;
