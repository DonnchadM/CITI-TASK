import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  FormControl, FormControlLabel, InputLabel, MenuItem, Select, Switch, TextField,
} from '@mui/material';
import { FormDialog } from './FormDialog';

const schema = z.object({
  name: z.string().min(1, 'Name is required').max(200),
  location: z.string().max(200).optional(),
  title: z.string().max(200).optional(),
  staff_type: z.enum(['DIRECT', 'NON_DIRECT']),
  is_org_leader: z.boolean(),
  employee_id: z.string().max(100).optional(),
  department: z.string().max(100).optional(),
});

const EMPTY = {
  name: '', location: '', title: '', staff_type: 'DIRECT',
  is_org_leader: false, employee_id: '', department: '',
};

function toDefaults(person) {
  if (!person) return EMPTY;
  return {
    name: person.name || '',
    location: person.location || '',
    title: person.title || '',
    staff_type: person.staff_type || 'DIRECT',
    is_org_leader: !!person.is_org_leader,
    employee_id: person.metadata?.employee_id || '',
    department: person.metadata?.department || '',
  };
}

// Build the API body, sending null for cleared optional fields and folding the
// known metadata fields into the metadata object.
function toBody(values) {
  const metadata = {};
  if (values.employee_id) metadata.employee_id = values.employee_id;
  if (values.department) metadata.department = values.department;
  return {
    name: values.name,
    location: values.location || null,
    title: values.title || null,
    staff_type: values.staff_type,
    is_org_leader: values.is_org_leader,
    metadata,
  };
}

export function PersonFormDialog({ open, person, onClose, onSubmit, submitting, serverError }) {
  const { register, handleSubmit, control, reset, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: EMPTY,
  });

  useEffect(() => {
    if (open) reset(toDefaults(person));
  }, [open, person, reset]);

  return (
    <FormDialog
      open={open}
      title={person ? 'Edit person' : 'Add person'}
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
      <TextField label="Title" fullWidth {...register('title')} />
      <Controller
        name="staff_type"
        control={control}
        render={({ field }) => (
          <FormControl fullWidth>
            <InputLabel id="staff-type-label">Staff type</InputLabel>
            <Select labelId="staff-type-label" label="Staff type" {...field}>
              <MenuItem value="DIRECT">Direct</MenuItem>
              <MenuItem value="NON_DIRECT">Non-direct</MenuItem>
            </Select>
          </FormControl>
        )}
      />
      <Controller
        name="is_org_leader"
        control={control}
        render={({ field }) => (
          <FormControlLabel
            control={<Switch checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />}
            label="Organization leader"
          />
        )}
      />
      <TextField label="Employee ID" fullWidth {...register('employee_id')} />
      <TextField label="Department" fullWidth {...register('department')} />
    </FormDialog>
  );
}
