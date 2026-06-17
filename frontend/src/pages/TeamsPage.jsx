import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert, Box, Button, Card, CardContent, CircularProgress, IconButton, Stack,
  TextField, Tooltip, Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import GroupIcon from '@mui/icons-material/Group';
import { teamsApi } from '../services/teams';
import { peopleApi } from '../services/people';
import { ResponsiveTable } from '../components/ResponsiveTable';
import { FilterBar } from '../components/FilterBar';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { TeamFormDialog } from '../components/TeamFormDialog';
import { TeamMembersDialog } from '../components/TeamMembersDialog';
import { Can } from '../components/Can';

function cleanFilters({ q, location }) {
  return { ...(q ? { q } : {}), ...(location ? { location } : {}) };
}

export function TeamsPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ q: '', location: '' });
  const [form, setForm] = useState({ open: false, team: null });
  const [members, setMembers] = useState({ open: false, team: null });
  const [toDelete, setToDelete] = useState(null);
  const [formError, setFormError] = useState('');

  const setFilter = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }));

  // Option list for leader/reports-to selects and for resolving leader names.
  const peopleQuery = useQuery({ queryKey: ['people-options'], queryFn: () => peopleApi.list({ limit: 200 }) });
  const people = peopleQuery.data?.data || [];
  const nameById = Object.fromEntries(people.map((p) => [p.id, p.name]));

  const list = useQuery({ queryKey: ['teams', filters], queryFn: () => teamsApi.list(cleanFilters(filters)) });

  const afterWrite = () => {
    queryClient.invalidateQueries({ queryKey: ['teams'] });
    setForm({ open: false, team: null });
    setToDelete(null);
    setFormError('');
  };

  const save = useMutation({
    mutationFn: ({ id, body }) => (id ? teamsApi.update(id, body) : teamsApi.create(body)),
    onSuccess: afterWrite,
    onError: (err) => setFormError(err?.message || 'Could not save this team.'),
  });
  const remove = useMutation({ mutationFn: (id) => teamsApi.remove(id), onSuccess: afterWrite });

  const openCreate = () => { setFormError(''); setForm({ open: true, team: null }); };
  const openEdit = (team) => { setFormError(''); setForm({ open: true, team }); };

  const columns = [
    { key: 'name', label: 'Name' },
    { key: 'location', label: 'Location', render: (r) => r.location || '—' },
    { key: 'leader_id', label: 'Leader', render: (r) => nameById[r.leader_id] || '—' },
  ];

  const rowActions = (team) => (
    <>
      <Tooltip title="Members">
        <IconButton size="small" onClick={() => setMembers({ open: true, team })}><GroupIcon fontSize="small" /></IconButton>
      </Tooltip>
      <Can action="update">
        <Tooltip title="Edit">
          <IconButton size="small" onClick={() => openEdit(team)}><EditIcon fontSize="small" /></IconButton>
        </Tooltip>
      </Can>
      <Can action="delete">
        <Tooltip title="Delete">
          <IconButton size="small" color="error" onClick={() => setToDelete(team)}><DeleteIcon fontSize="small" /></IconButton>
        </Tooltip>
      </Can>
    </>
  );

  const renderCard = (team) => (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="subtitle1">{team.name}</Typography>
            <Typography variant="body2" color="text.secondary">
              {(team.location || '—')} · Leader: {nameById[team.leader_id] || '—'}
            </Typography>
          </Box>
          <Box>{rowActions(team)}</Box>
        </Stack>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">Teams</Typography>
        <Can action="create">
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>Add team</Button>
        </Can>
      </Stack>

      <FilterBar>
        <TextField label="Search" size="small" value={filters.q} onChange={setFilter('q')} sx={{ minWidth: 200 }} />
        <TextField label="Location" size="small" value={filters.location} onChange={setFilter('location')} />
      </FilterBar>

      {list.isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}><CircularProgress /></Box>
      ) : list.isError ? (
        <Alert severity="error">Could not load teams. Please try again.</Alert>
      ) : (
        <ResponsiveTable
          columns={columns}
          rows={list.data?.data || []}
          getRowKey={(r) => r.id}
          renderActions={rowActions}
          renderCard={renderCard}
          emptyText="No teams match your filters."
        />
      )}

      <TeamFormDialog
        open={form.open}
        team={form.team}
        people={people}
        onClose={() => setForm({ open: false, team: null })}
        onSubmit={(body) => save.mutate({ id: form.team?.id, body })}
        submitting={save.isPending}
        serverError={formError}
      />

      <TeamMembersDialog
        open={members.open}
        team={members.team}
        people={people}
        onClose={() => setMembers({ open: false, team: null })}
      />

      <ConfirmDialog
        open={!!toDelete}
        title="Delete team"
        message={`Delete ${toDelete?.name}? This also removes its memberships and achievements.`}
        onConfirm={() => remove.mutate(toDelete.id)}
        onClose={() => setToDelete(null)}
        busy={remove.isPending}
      />
    </Box>
  );
}
