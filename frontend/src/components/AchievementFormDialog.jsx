import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { FormControl, InputLabel, MenuItem, Select, TextField } from '@mui/material';
import { FormDialog } from './FormDialog';

const schema = z.object({
  team_id: z.string().min(1, 'Team is required'),
  month: z.string().min(1, 'Month is required'),
  title: z.string().min(1, 'Title is required').max(200),
  description: z.string().optional(),
});

const EMPTY = { team_id: '', month: '', title: '', description: '' };

function toDefaults(achievement) {
  if (!achievement) return EMPTY;
  return {
    team_id: achievement.team_id || '',
    // backend stores the first of the month (YYYY-MM-DD); the month input wants YYYY-MM
    month: (achievement.month || '').slice(0, 7),
    title: achievement.title || '',
    description: achievement.description || '',
  };
}

function toBody(values) {
  return {
    team_id: values.team_id,
    month: `${values.month}-01`, // normalize YYYY-MM to a full date for the API
    title: values.title,
    description: values.description || null,
  };
}

export function AchievementFormDialog({ open, achievement, teams = [], onClose, onSubmit, submitting, serverError }) {
  const { register, handleSubmit, control, reset, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  });

  useEffect(() => {
    if (open) reset(toDefaults(achievement));
  }, [open, achievement, reset]);

  return (
    <FormDialog
      open={open}
      title={achievement ? 'Edit achievement' : 'Add achievement'}
      onClose={onClose}
      onSubmit={handleSubmit((values) => onSubmit(toBody(values)))}
      submitting={submitting}
      serverError={serverError}
    >
      <Controller
        name="team_id"
        control={control}
        render={({ field }) => (
          <FormControl fullWidth required error={!!errors.team_id}>
            <InputLabel id="ach-team-label">Team</InputLabel>
            <Select labelId="ach-team-label" label="Team" {...field}>
              {teams.map((t) => <MenuItem key={t.id} value={t.id}>{t.name}</MenuItem>)}
            </Select>
          </FormControl>
        )}
      />
      <TextField
        label="Month" type="month" fullWidth required
        InputLabelProps={{ shrink: true }}
        error={!!errors.month} helperText={errors.month?.message}
        {...register('month')}
      />
      <TextField
        label="Title" fullWidth required
        error={!!errors.title} helperText={errors.title?.message}
        {...register('title')}
      />
      <TextField label="Description" fullWidth multiline minRows={2} {...register('description')} />
    </FormDialog>
  );
}
