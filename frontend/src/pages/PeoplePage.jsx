import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, IconButton,
  MenuItem, Stack, TextField, Tooltip, Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { peopleApi } from '../services/people';
import { ResponsiveTable } from '../components/ResponsiveTable';
import { FilterBar } from '../components/FilterBar';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { PersonFormDialog } from '../components/PersonFormDialog';
import { Can } from '../components/Can';

const staffLabel = (t) => (t === 'DIRECT' ? 'Direct' : 'Non-direct');

function cleanFilters({ q, staff_type, location, is_org_leader }) {
  return {
    ...(q ? { q } : {}),
    ...(staff_type ? { staff_type } : {}),
    ...(location ? { location } : {}),
    ...(is_org_leader ? { is_org_leader } : {}),
  };
}

export function PeoplePage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ q: '', staff_type: '', location: '', is_org_leader: '' });
  const [form, setForm] = useState({ open: false, person: null });
  const [toDelete, setToDelete] = useState(null);
  const [formError, setFormError] = useState('');

  const setFilter = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }));

  const list = useQuery({
    queryKey: ['people', filters],
    queryFn: () => peopleApi.list(cleanFilters(filters)),
  });

  const afterWrite = () => {
    queryClient.invalidateQueries({ queryKey: ['people'] });
    setForm({ open: false, person: null });
    setToDelete(null);
    setFormError('');
  };

  const save = useMutation({
    mutationFn: ({ id, body }) => (id ? peopleApi.update(id, body) : peopleApi.create(body)),
    onSuccess: afterWrite,
    onError: (err) => setFormError(err?.message || 'Could not save this person.'),
  });

  const remove = useMutation({
    mutationFn: (id) => peopleApi.remove(id),
    onSuccess: afterWrite,
  });

  const openCreate = () => { setFormError(''); setForm({ open: true, person: null }); };
  const openEdit = (person) => { setFormError(''); setForm({ open: true, person }); };

  const columns = [
    { key: 'name', label: 'Name' },
    { key: 'location', label: 'Location', render: (r) => r.location || '—' },
    { key: 'title', label: 'Title', render: (r) => r.title || '—' },
    { key: 'staff_type', label: 'Staff', render: (r) => <Chip size="small" label={staffLabel(r.staff_type)} /> },
    {
      key: 'is_org_leader', label: 'Org leader', align: 'center',
      render: (r) => (r.is_org_leader ? <Chip size="small" color="primary" label="Yes" /> : '—'),
    },
  ];

  const rowActions = (person) => (
    <>
      <Can action="update">
        <Tooltip title="Edit">
          <IconButton size="small" onClick={() => openEdit(person)}><EditIcon fontSize="small" /></IconButton>
        </Tooltip>
      </Can>
      <Can action="delete">
        <Tooltip title="Delete">
          <IconButton size="small" color="error" onClick={() => setToDelete(person)}><DeleteIcon fontSize="small" /></IconButton>
        </Tooltip>
      </Can>
    </>
  );

  const renderCard = (person) => (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="subtitle1">{person.name}</Typography>
            <Typography variant="body2" color="text.secondary">
              {(person.title || '—')} · {(person.location || '—')}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              <Chip size="small" label={staffLabel(person.staff_type)} />
              {person.is_org_leader && <Chip size="small" color="primary" label="Org leader" />}
            </Stack>
          </Box>
          <Box>{rowActions(person)}</Box>
        </Stack>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">People</Typography>
        <Can action="create">
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>Add person</Button>
        </Can>
      </Stack>

      <FilterBar>
        <TextField label="Search" size="small" value={filters.q} onChange={setFilter('q')} sx={{ minWidth: 200 }} />
        <TextField label="Location" size="small" value={filters.location} onChange={setFilter('location')} />
        <TextField label="Staff type" size="small" select value={filters.staff_type} onChange={setFilter('staff_type')} sx={{ minWidth: 150 }}>
          <MenuItem value="">All</MenuItem>
          <MenuItem value="DIRECT">Direct</MenuItem>
          <MenuItem value="NON_DIRECT">Non-direct</MenuItem>
        </TextField>
        <TextField label="Org leader" size="small" select value={filters.is_org_leader} onChange={setFilter('is_org_leader')} sx={{ minWidth: 150 }}>
          <MenuItem value="">All</MenuItem>
          <MenuItem value="true">Yes</MenuItem>
          <MenuItem value="false">No</MenuItem>
        </TextField>
      </FilterBar>

      {list.isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}><CircularProgress /></Box>
      ) : list.isError ? (
        <Alert severity="error">Could not load people. Please try again.</Alert>
      ) : (
        <ResponsiveTable
          columns={columns}
          rows={list.data?.data || []}
          getRowKey={(r) => r.id}
          renderActions={rowActions}
          renderCard={renderCard}
          emptyText="No people match your filters."
        />
      )}

      <PersonFormDialog
        open={form.open}
        person={form.person}
        onClose={() => setForm({ open: false, person: null })}
        onSubmit={(body) => save.mutate({ id: form.person?.id, body })}
        submitting={save.isPending}
        serverError={formError}
      />

      <ConfirmDialog
        open={!!toDelete}
        title="Delete person"
        message={`Delete ${toDelete?.name}? This cannot be undone.`}
        onConfirm={() => remove.mutate(toDelete.id)}
        onClose={() => setToDelete(null)}
        busy={remove.isPending}
      />
    </Box>
  );
}
