import { useEffect } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  FormControl, FormControlLabel, InputLabel, MenuItem, Select, Switch, TextField,
} from '@mui/material';
import { FormDialog } from './FormDialog';
import { ROLES } from '../services/users';

// Email/password are only set on create; edits change role/status/person link
// (mirrors the backend UserUpdate, which does not accept email/password).
const baseShape = {
  role: z.enum(ROLES),
  is_active: z.boolean(),
  person_id: z.string().optional(),
};
const createSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'At least 8 characters'),
  ...baseShape,
});
const editSchema = z.object(baseShape);

function defaults(user) {
  if (!user) return { email: '', password: '', role: 'VIEWER', is_active: true, person_id: '' };
  return {
    role: user.role || 'VIEWER',
    is_active: user.is_active ?? true,
    person_id: user.person_id || '',
  };
}

export function UserFormDialog({ open, user, people = [], onClose, onSubmit, submitting, serverError }) {
  const isEdit = !!user;
  const { register, handleSubmit, control, reset, formState: { errors } } = useForm({
    resolver: zodResolver(isEdit ? editSchema : createSchema),
    defaultValues: defaults(user),
  });

  useEffect(() => {
    if (open) reset(defaults(user));
  }, [open, user, reset]);

  const submit = (values) => {
    const body = { role: values.role, is_active: values.is_active, person_id: values.person_id || null };
    if (!isEdit) { body.email = values.email; body.password = values.password; }
    onSubmit(body);
  };

  return (
    <FormDialog
      open={open}
      title={isEdit ? `Edit user · ${user.email}` : 'Add user'}
      onClose={onClose}
      onSubmit={handleSubmit(submit)}
      submitting={submitting}
      serverError={serverError}
    >
      {!isEdit && (
        <>
          <TextField
            label="Email" type="email" fullWidth required
            error={!!errors.email} helperText={errors.email?.message}
            {...register('email')}
          />
          <TextField
            label="Password" type="password" fullWidth required
            error={!!errors.password} helperText={errors.password?.message}
            {...register('password')}
          />
        </>
      )}
      <Controller
        name="role"
        control={control}
        render={({ field }) => (
          <FormControl fullWidth>
            <InputLabel id="role-label">Role</InputLabel>
            <Select labelId="role-label" label="Role" {...field}>
              {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
            </Select>
          </FormControl>
        )}
      />
      <Controller
        name="person_id"
        control={control}
        render={({ field }) => (
          <FormControl fullWidth>
            <InputLabel id="person-label">Linked person (optional)</InputLabel>
            <Select labelId="person-label" label="Linked person (optional)" {...field}>
              <MenuItem value=""><em>None</em></MenuItem>
              {people.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
            </Select>
          </FormControl>
        )}
      />
      <Controller
        name="is_active"
        control={control}
        render={({ field }) => (
          <FormControlLabel
            control={<Switch checked={field.value} onChange={(e) => field.onChange(e.target.checked)} />}
            label="Active"
          />
        )}
      />
    </FormDialog>
  );
}
