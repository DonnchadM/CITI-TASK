import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControl, IconButton, InputLabel, List, ListItem, ListItemText, MenuItem,
  Select, Stack, TextField, Typography,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { teamsApi } from '../services/teams';
import { Can } from './Can';

// Manage a team's membership: list current members, add a person (with optional
// role), remove a member. Mutations are gated by create/delete permissions.
export function TeamMembersDialog({ open, team, people = [], onClose }) {
  const queryClient = useQueryClient();
  const [personId, setPersonId] = useState('');
  const [role, setRole] = useState('');
  const [error, setError] = useState('');

  const membersQuery = useQuery({
    queryKey: ['team-members', team?.id],
    queryFn: () => teamsApi.members(team.id),
    enabled: open && !!team,
  });
  const members = membersQuery.data?.data || [];
  const memberIds = new Set(members.map((m) => m.person_id));
  const candidates = people.filter((p) => !memberIds.has(p.id));

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['team-members', team.id] });

  const add = useMutation({
    mutationFn: () => teamsApi.addMember(team.id, { person_id: personId, role_in_team: role || null }),
    onSuccess: () => { invalidate(); setPersonId(''); setRole(''); setError(''); },
    onError: (err) => setError(err?.message || 'Could not add member.'),
  });
  const remove = useMutation({
    mutationFn: (pid) => teamsApi.removeMember(team.id, pid),
    onSuccess: invalidate,
  });

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Members{team ? ` · ${team.name}` : ''}</DialogTitle>
      <DialogContent>
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {membersQuery.isLoading ? (
          <Typography color="text.secondary">Loading…</Typography>
        ) : (
          <List dense>
            {members.map((m) => (
              <ListItem
                key={m.person_id}
                secondaryAction={(
                  <Can action="delete">
                    <IconButton edge="end" color="error" onClick={() => remove.mutate(m.person_id)} disabled={remove.isPending}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Can>
                )}
              >
                <ListItemText
                  primary={m.name}
                  secondary={`${m.location || '—'} · ${m.staff_type === 'DIRECT' ? 'Direct' : 'Non-direct'}`}
                />
                {m.role_in_team && <Chip size="small" label={m.role_in_team} sx={{ mr: 6 }} />}
              </ListItem>
            ))}
            {members.length === 0 && <Typography color="text.secondary">No members yet.</Typography>}
          </List>
        )}

        <Can action="create">
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mt: 2 }}>
            <FormControl fullWidth size="small">
              <InputLabel id="add-member-label">Add person</InputLabel>
              <Select
                labelId="add-member-label"
                label="Add person"
                value={personId}
                onChange={(e) => setPersonId(e.target.value)}
              >
                {candidates.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
              </Select>
            </FormControl>
            <TextField label="Role" size="small" value={role} onChange={(e) => setRole(e.target.value)} />
            <Button
              variant="contained"
              onClick={() => add.mutate()}
              disabled={!personId || add.isPending}
            >
              Add
            </Button>
          </Stack>
        </Can>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
