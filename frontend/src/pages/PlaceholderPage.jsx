import { Box, Typography } from '@mui/material';

// Temporary stand-in for sections built in later slices (people, teams, etc.),
// so the nav and routing work end-to-end now.
export function PlaceholderPage({ title }) {
  return (
    <Box>
      <Typography variant="h5" gutterBottom>{title}</Typography>
      <Typography color="text.secondary">This section is coming soon.</Typography>
    </Box>
  );
}
