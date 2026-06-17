import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { FormControl, InputLabel, MenuItem, Select, TextField } from '@mui/material';
import { FormDialog } from './FormDialog';

const schema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  location: z.string().max(200).optional(),
  description: z.string().optional(),
  leader_id: z.string().optional(),
  reports_to_id: z.string().optional(),
});

const EMPTY = { name: '', location: '', description: '', leader_id: '', reports_to_id: '' };

function toDefaults(team) {
  if (!team) return EMPTY;
  return {
    name: team.name || '',
    location: team.location || '',
    description: team.description || '',
    leader_id: team.leader_id || '',
    reports_to_id: team.reports_to_id || '',
  };
}

function toBody(values) {
  return {
    name: values.name,
    location: values.location || null,
    description: values.description || null,
    leader_id: values.leader_id || null,
    reports_to_id: values.reports_to_id || null,
    metadata: {},
  };
}

// `people` is the option list for the leader / reports-to selects.
export function TeamFormDialog({ open, team, people = [], onClose, onSubmit, submitting, serverError }) {
  const { register, handleSubmit, control, reset, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  });

  useEffect(() => {
    if (open) reset(toDefaults(team));
  }, [open, team, reset]);

  const personSelect = (name, label) => (
    <Controller
      name={name}
      control={control}
      render={({ field }) => (
        <FormControl fullWidth>
          <InputLabel id={`${name}-label`}>{label}</InputLabel>
          <Select labelId={`${name}-label`} label={label} {...field}>
            <MenuItem value=""><em>None</em></MenuItem>
            {people.map((p) => (
              <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
    />
  );

  return (
    <FormDialog
      open={open}
      title={team ? 'Edit team' : 'Add team'}
      onClose={onClose}
      onSubmit={handleSubmit((values) => onSubmit(toBody(values)))}
      submitting={submitting}
      serverError={serverError}
    >
      <TextField
        label="Name" fullWidth required
        error={!!errors.name} helperText={errors.name?.message}
        {...register('name')}
      />
      <TextField label="Location" fullWidth {...register('location')} />
      <TextField label="Description" fullWidth multiline minRows={2} {...register('description')} />
      {personSelect('leader_id', 'Team leader')}
      {personSelect('reports_to_id', 'Reports to')}
    </FormDialog>
  );
}
