import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert, Box, Button, Card, CardContent, CircularProgress, IconButton, MenuItem,
  Stack, TextField, Tooltip, Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { achievementsApi } from '../services/achievements';
import { teamsApi } from '../services/teams';
import { ResponsiveTable } from '../components/ResponsiveTable';
import { FilterBar } from '../components/FilterBar';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { AchievementFormDialog } from '../components/AchievementFormDialog';
import { Can } from '../components/Can';

function cleanFilters({ team_id, month, from, to }) {
  return {
    ...(team_id ? { team_id } : {}),
    ...(month ? { month: `${month}-01` } : {}),
    ...(from ? { from: `${from}-01` } : {}),
    ...(to ? { to: `${to}-01` } : {}),
  };
}

export function AchievementsPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ team_id: '', month: '', from: '', to: '' });
  const [form, setForm] = useState({ open: false, achievement: null });
  const [toDelete, setToDelete] = useState(null);
  const [formError, setFormError] = useState('');

  const setFilter = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }));

  const teamsQuery = useQuery({ queryKey: ['teams-options'], queryFn: () => teamsApi.list({ limit: 200 }) });
  const teams = teamsQuery.data?.data || [];
  const teamName = Object.fromEntries(teams.map((t) => [t.id, t.name]));

  const list = useQuery({
    queryKey: ['achievements', filters],
    queryFn: () => achievementsApi.list(cleanFilters(filters)),
  });

  const afterWrite = () => {
    queryClient.invalidateQueries({ queryKey: ['achievements'] });
    setForm({ open: false, achievement: null });
    setToDelete(null);
    setFormError('');
  };

  const save = useMutation({
    mutationFn: ({ id, body }) => (id ? achievementsApi.update(id, body) : achievementsApi.create(body)),
    onSuccess: afterWrite,
    onError: (err) => setFormError(err?.message || 'Could not save this achievement.'),
  });
  const remove = useMutation({ mutationFn: (id) => achievementsApi.remove(id), onSuccess: afterWrite });

  const openCreate = () => { setFormError(''); setForm({ open: true, achievement: null }); };
  const openEdit = (achievement) => { setFormError(''); setForm({ open: true, achievement }); };

  const columns = [
    { key: 'month', label: 'Month', render: (r) => (r.month || '').slice(0, 7) },
    { key: 'team_id', label: 'Team', render: (r) => teamName[r.team_id] || '—' },
    { key: 'title', label: 'Title' },
  ];

  const rowActions = (a) => (
    <>
      <Can action="update">
        <Tooltip title="Edit">
          <IconButton size="small" onClick={() => openEdit(a)}><EditIcon fontSize="small" /></IconButton>
        </Tooltip>
      </Can>
      <Can action="delete">
        <Tooltip title="Delete">
          <IconButton size="small" color="error" onClick={() => setToDelete(a)}><DeleteIcon fontSize="small" /></IconButton>
        </Tooltip>
      </Can>
    </>
  );

  const renderCard = (a) => (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="subtitle1">{a.title}</Typography>
            <Typography variant="body2" color="text.secondary">
              {(a.month || '').slice(0, 7)} · {teamName[a.team_id] || '—'}
            </Typography>
          </Box>
          <Box>{rowActions(a)}</Box>
        </Stack>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">Achievements</Typography>
        <Can action="create">
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>Add achievement</Button>
        </Can>
      </Stack>

      <FilterBar>
        <TextField label="Team" size="small" select value={filters.team_id} onChange={setFilter('team_id')} sx={{ minWidth: 180 }}>
          <MenuItem value="">All teams</MenuItem>
          {teams.map((t) => <MenuItem key={t.id} value={t.id}>{t.name}</MenuItem>)}
        </TextField>
        <TextField label="Month" type="month" size="small" InputLabelProps={{ shrink: true }} value={filters.month} onChange={setFilter('month')} />
        <TextField label="From" type="month" size="small" InputLabelProps={{ shrink: true }} value={filters.from} onChange={setFilter('from')} />
        <TextField label="To" type="month" size="small" InputLabelProps={{ shrink: true }} value={filters.to} onChange={setFilter('to')} />
      </FilterBar>

      {list.isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}><CircularProgress /></Box>
      ) : list.isError ? (
        <Alert severity="error">Could not load achievements. Please try again.</Alert>
      ) : (
        <ResponsiveTable
          columns={columns}
          rows={list.data?.data || []}
          getRowKey={(r) => r.id}
          renderActions={rowActions}
          renderCard={renderCard}
          emptyText="No achievements match your filters."
        />
      )}

      <AchievementFormDialog
        open={form.open}
        achievement={form.achievement}
        teams={teams}
        onClose={() => setForm({ open: false, achievement: null })}
        onSubmit={(body) => save.mutate({ id: form.achievement?.id, body })}
        submitting={save.isPending}
        serverError={formError}
      />

      <ConfirmDialog
        open={!!toDelete}
        title="Delete achievement"
        message={`Delete “${toDelete?.title}”? This cannot be undone.`}
        onConfirm={() => remove.mutate(toDelete.id)}
        onClose={() => setToDelete(null)}
        busy={remove.isPending}
      />
    </Box>
  );
}
