import { Card, CardContent, Box, Typography } from '@mui/material';

// A single dashboard KPI tile: big number, label, and an icon.
export function KpiCard({ label, value, icon, color = 'primary.main' }) {
  return (
    <Card elevation={2} sx={{ height: '100%' }}>
      <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box
          sx={{
            bgcolor: color,
            color: 'common.white',
            borderRadius: 2,
            p: 1.5,
            display: 'flex',
          }}
        >
          {icon}
        </Box>
        <Box>
          <Typography variant="h4" component="div">
            {value}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {label}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}
