import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  Alert, Box, Button, Card, CardContent, Chip, Divider, Stack, TextField, Typography,
} from '@mui/material';
import { useAuth } from '../hooks/useAuth';
import { authApi } from '../services/auth';

const schema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'At least 8 characters'),
    confirm: z.string(),
  })
  .refine((d) => d.new_password === d.confirm, {
    message: 'Passwords do not match',
    path: ['confirm'],
  });

export function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [changed, setChanged] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { current_password: '', new_password: '', confirm: '' },
  });

  const change = useMutation({
    mutationFn: (v) => authApi.changePassword(v.current_password, v.new_password),
    onSuccess: () => { setError(''); setChanged(true); },
    onError: (err) => setError(
      err?.status === 400 ? 'Your current password is incorrect.' : (err?.message || 'Could not change password.'),
    ),
  });

  const signInAgain = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <Box sx={{ maxWidth: 560 }}>
      <Typography variant="h5" gutterBottom>Profile</Typography>

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle2" color="text.secondary">Email</Typography>
          <Typography sx={{ mb: 1 }}>{user?.email}</Typography>
          <Stack direction="row" spacing={1}>
            <Chip size="small" label={user?.role} />
            {user?.is_active && <Chip size="small" color="success" label="Active" />}
          </Stack>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h6" gutterBottom>Change password</Typography>
          <Divider sx={{ mb: 2 }} />

          {changed ? (
            <Box>
              <Alert severity="success" sx={{ mb: 2 }}>
                Password changed. For security, all sessions have been signed out — please log in again.
              </Alert>
              <Button variant="contained" onClick={signInAgain}>Sign in again</Button>
            </Box>
          ) : (
            <Box component="form" onSubmit={handleSubmit((v) => change.mutate(v))} noValidate>
              {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
              <Stack spacing={2}>
                <TextField
                  label="Current password" type="password" fullWidth
                  error={!!errors.current_password} helperText={errors.current_password?.message}
                  {...register('current_password')}
                />
                <TextField
                  label="New password" type="password" fullWidth
                  error={!!errors.new_password} helperText={errors.new_password?.message}
                  {...register('new_password')}
                />
                <TextField
                  label="Confirm new password" type="password" fullWidth
                  error={!!errors.confirm} helperText={errors.confirm?.message}
                  {...register('confirm')}
                />
                <Box>
                  <Button type="submit" variant="contained" disabled={change.isPending}>
                    {change.isPending ? 'Updating…' : 'Update password'}
                  </Button>
                </Box>
              </Stack>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
