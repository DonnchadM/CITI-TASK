import { Paper, Stack } from '@mui/material';

// Thin responsive container for a page's filter inputs: a row on desktop that
// wraps/stacks on small screens.
export function FilterBar({ children }) {
  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        useFlexGap
        flexWrap="wrap"
        alignItems={{ sm: 'center' }}
      >
        {children}
      </Stack>
    </Paper>
  );
}
