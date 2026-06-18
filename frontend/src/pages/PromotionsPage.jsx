import { useQuery } from '@tanstack/react-query';
import {
  Alert, Box, Chip, CircularProgress, LinearProgress, Paper, Stack,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from '@mui/material';
import { analyticsApi } from '../services/analytics';

const BAND_COLOR = { 'Ready for review': 'success', 'On track': 'info', Early: 'default' };

export function PromotionsPage() {
  const q = useQuery({ queryKey: ['analytics', 'promotions'], queryFn: analyticsApi.promotions });

  if (q.isLoading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}><CircularProgress /></Box>;
  }
  if (q.isError) {
    return <Alert severity="error">Could not load promotion readiness. Please try again.</Alert>;
  }

  const rows = q.data?.data || [];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Promotion readiness</Typography>
      <Alert severity="info" sx={{ mb: 3 }}>
        An <strong>illustrative</strong> readiness score, not a real HR signal: it combines each
        person&apos;s tenure (earliest team membership) with the achievement activity of the teams
        they belong to. Useful as a quick overview of who may be due for a review.
      </Alert>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" aria-label="Promotion readiness">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Title</TableCell>
              <TableCell align="right">Tenure (months)</TableCell>
              <TableCell align="right">Team achievements</TableCell>
              <TableCell sx={{ width: 200 }}>Readiness</TableCell>
              <TableCell>Band</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.person_id} hover>
                <TableCell>{r.name}</TableCell>
                <TableCell>{r.title || '—'}</TableCell>
                <TableCell align="right">{r.tenure_months}</TableCell>
                <TableCell align="right">{r.team_achievements}</TableCell>
                <TableCell>
                  <Stack direction="row" alignItems="center" spacing={1}>
                    <LinearProgress
                      variant="determinate"
                      value={r.readiness_score}
                      sx={{ flexGrow: 1, height: 8, borderRadius: 1 }}
                    />
                    <Typography variant="body2" sx={{ width: 32, textAlign: 'right' }}>{r.readiness_score}</Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Chip size="small" label={r.band} color={BAND_COLOR[r.band] || 'default'} variant={r.band === 'Early' ? 'outlined' : 'filled'} />
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && (
              <TableRow><TableCell colSpan={6}><Typography color="text.secondary">No people yet.</Typography></TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
