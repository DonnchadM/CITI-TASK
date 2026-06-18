import { useQuery } from '@tanstack/react-query';
import { useMediaQuery } from 'react-responsive';
import {
  Alert, Box, Card, CardContent, Chip, CircularProgress, Grid, Paper, Stack,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from '@mui/material';
import LocationOffIcon from '@mui/icons-material/LocationOff';
import BadgeIcon from '@mui/icons-material/Badge';
import PercentIcon from '@mui/icons-material/Percent';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import EmojiEventsIcon from '@mui/icons-material/EmojiEvents';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import { analyticsApi } from '../services/analytics';
import { KpiCard } from '../components/KpiCard';

const pct = (ratio) => `${Math.round((ratio || 0) * 100)}%`;

const KPIS = [
  { key: 'teams_leader_not_colocated', label: 'Leader not co-located', icon: <LocationOffIcon />, color: 'warning.main' },
  { key: 'teams_leader_non_direct', label: 'Leader is non-direct staff', icon: <BadgeIcon />, color: 'secondary.main' },
  { key: 'teams_high_non_direct_ratio', label: 'Non-direct ratio > 20%', icon: <PercentIcon />, color: 'error.main' },
  { key: 'teams_under_org_leader', label: 'Reporting to an org leader', icon: <AccountTreeIcon />, color: 'primary.main' },
];

// Achievement activity — a quick performance read alongside the structural KPIs.
const ACHIEVEMENT_KPIS = [
  { key: 'total_achievements', label: 'Total achievements', icon: <EmojiEventsIcon />, color: 'success.main' },
  { key: 'achievements_this_month', label: 'Achievements this month', icon: <CalendarMonthIcon />, color: 'info.main' },
];

function YesNo({ value }) {
  return value ? <Chip size="small" color="warning" label="Yes" /> : <Chip size="small" label="No" variant="outlined" />;
}

export function DashboardPage() {
  const isMobile = useMediaQuery({ maxWidth: 600 });
  const summary = useQuery({ queryKey: ['analytics', 'summary'], queryFn: analyticsApi.summary });
  const teams = useQuery({ queryKey: ['analytics', 'teams'], queryFn: analyticsApi.teams });

  if (summary.isLoading || teams.isLoading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}><CircularProgress /></Box>;
  }
  if (summary.isError || teams.isError) {
    return <Alert severity="error">Could not load analytics. Please try again.</Alert>;
  }

  const teamRows = teams.data?.data || [];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>Organization dashboard</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {summary.data.total_teams} team{summary.data.total_teams === 1 ? '' : 's'} tracked
      </Typography>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        {KPIS.map((kpi) => (
          <Grid key={kpi.key} size={{ xs: 12, sm: 6, md: 3 }}>
            <KpiCard label={kpi.label} value={summary.data[kpi.key]} icon={kpi.icon} color={kpi.color} />
          </Grid>
        ))}
      </Grid>

      <Typography variant="h6" gutterBottom>Achievement activity</Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {ACHIEVEMENT_KPIS.map((kpi) => (
          <Grid key={kpi.key} size={{ xs: 12, sm: 6, md: 3 }}>
            <KpiCard label={kpi.label} value={summary.data[kpi.key]} icon={kpi.icon} color={kpi.color} />
          </Grid>
        ))}
      </Grid>

      <Typography variant="h6" gutterBottom>Per-team breakdown</Typography>

      {isMobile ? (
        <Stack spacing={2}>
          {teamRows.map((t) => (
            <Card key={t.team_id} variant="outlined">
              <CardContent>
                <Typography variant="subtitle1">{t.team_name}</Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {t.team_location || '—'} · {t.member_count} members · {t.achievement_count} achievements · {pct(t.non_direct_ratio)} non-direct
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {t.leader_not_colocated && <Chip size="small" color="warning" label="Leader off-site" />}
                  {t.leader_is_non_direct && <Chip size="small" color="secondary" label="Non-direct lead" />}
                  {t.reports_to_org_leader && <Chip size="small" color="primary" label="Under org leader" />}
                </Stack>
              </CardContent>
            </Card>
          ))}
          {teamRows.length === 0 && <Typography color="text.secondary">No teams yet.</Typography>}
        </Stack>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" aria-label="Per-team analytics">
            <TableHead>
              <TableRow>
                <TableCell>Team</TableCell>
                <TableCell>Location</TableCell>
                <TableCell align="right">Members</TableCell>
                <TableCell align="right">Achievements</TableCell>
                <TableCell align="right">Non-direct</TableCell>
                <TableCell align="center">Leader off-site</TableCell>
                <TableCell align="center">Non-direct lead</TableCell>
                <TableCell align="center">Under org leader</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {teamRows.map((t) => (
                <TableRow key={t.team_id} hover>
                  <TableCell>{t.team_name}</TableCell>
                  <TableCell>{t.team_location || '—'}</TableCell>
                  <TableCell align="right">{t.member_count}</TableCell>
                  <TableCell align="right">{t.achievement_count}</TableCell>
                  <TableCell align="right">{pct(t.non_direct_ratio)}</TableCell>
                  <TableCell align="center"><YesNo value={t.leader_not_colocated} /></TableCell>
                  <TableCell align="center"><YesNo value={t.leader_is_non_direct} /></TableCell>
                  <TableCell align="center"><YesNo value={t.reports_to_org_leader} /></TableCell>
                </TableRow>
              ))}
              {teamRows.length === 0 && (
                <TableRow><TableCell colSpan={8}><Typography color="text.secondary">No teams yet.</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
