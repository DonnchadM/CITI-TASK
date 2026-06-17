import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, IconButton,
  Stack, Tooltip, Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import { usersApi } from '../services/users';
import { peopleApi } from '../services/people';
import { ResponsiveTable } from '../components/ResponsiveTable';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { UserFormDialog } from '../components/UserFormDialog';
import { useAuth } from '../hooks/useAuth';

export function UsersPage() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();
  const [form, setForm] = useState({ open: false, user: null });
  const [toDelete, setToDelete] = useState(null);
  const [formError, setFormError] = useState('');

  const peopleQuery = useQuery({ queryKey: ['people-options'], queryFn: () => peopleApi.list({ limit: 200 }) });
  const people = peopleQuery.data?.data || [];
  const nameById = Object.fromEntries(people.map((p) => [p.id, p.name]));

  const list = useQuery({ queryKey: ['users'], queryFn: () => usersApi.list() });

  const afterWrite = () => {
    queryClient.invalidateQueries({ queryKey: ['users'] });
    setForm({ open: false, user: null });
    setToDelete(null);
    setFormError('');
  };

  const save = useMutation({
    mutationFn: ({ id, body }) => (id ? usersApi.update(id, body) : usersApi.create(body)),
    onSuccess: afterWrite,
    onError: (err) => setFormError(err?.message || 'Could not save this user.'),
  });
  const remove = useMutation({ mutationFn: (id) => usersApi.remove(id), onSuccess: afterWrite });

  const openCreate = () => { setFormError(''); setForm({ open: true, user: null }); };
  const openEdit = (user) => { setFormError(''); setForm({ open: true, user }); };

  const columns = [
    { key: 'email', label: 'Email' },
    { key: 'role', label: 'Role', render: (r) => <Chip size="small" label={r.role} /> },
    {
      key: 'is_active', label: 'Status', align: 'center',
      render: (r) => (r.is_active
        ? <Chip size="small" color="success" label="Active" />
        : <Chip size="small" label="Inactive" variant="outlined" />),
    },
    { key: 'person_id', label: 'Linked person', render: (r) => nameById[r.person_id] || '—' },
  ];

  const rowActions = (user) => {
    const isSelf = user.id === currentUser?.id;
    return (
      <>
        <Tooltip title="Edit">
          <IconButton size="small" onClick={() => openEdit(user)}><EditIcon fontSize="small" /></IconButton>
        </Tooltip>
        <Tooltip title={isSelf ? 'You cannot delete your own account' : 'Delete'}>
          <span>
            <IconButton size="small" color="error" disabled={isSelf} onClick={() => setToDelete(user)}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      </>
    );
  };

  const renderCard = (user) => (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="subtitle1">{user.email}</Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              <Chip size="small" label={user.role} />
              {user.is_active
                ? <Chip size="small" color="success" label="Active" />
                : <Chip size="small" label="Inactive" variant="outlined" />}
            </Stack>
          </Box>
          <Box>{rowActions(user)}</Box>
        </Stack>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">User administration</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>Add user</Button>
      </Stack>

      {list.isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}><CircularProgress /></Box>
      ) : list.isError ? (
        <Alert severity="error">Could not load users. Please try again.</Alert>
      ) : (
        <ResponsiveTable
          columns={columns}
          rows={list.data?.data || []}
          getRowKey={(r) => r.id}
          renderActions={rowActions}
          renderCard={renderCard}
          emptyText="No users found."
        />
      )}

      <UserFormDialog
        open={form.open}
        user={form.user}
        people={people}
        onClose={() => setForm({ open: false, user: null })}
        onSubmit={(body) => save.mutate({ id: form.user?.id, body })}
        submitting={save.isPending}
        serverError={formError}
      />

      <ConfirmDialog
        open={!!toDelete}
        title="Delete user"
        message={`Delete ${toDelete?.email}? This cannot be undone.`}
        onConfirm={() => remove.mutate(toDelete.id)}
        onClose={() => setToDelete(null)}
        busy={remove.isPending}
      />
    </Box>
  );
}
