import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack,
} from '@mui/material';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

// Generic dialog wrapper for create/edit forms: title, server-error alert,
// the form fields (children), and Cancel/Save actions with a busy state.
// Saving is disabled while offline (mutations are network-only).
export function FormDialog({
  open, title, onClose, onSubmit, submitting = false, serverError, submitLabel = 'Save', children,
}) {
  const online = useOnlineStatus();
  return (
    <Dialog open={open} onClose={submitting ? undefined : onClose} fullWidth maxWidth="sm">
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          {serverError && <Alert severity="error" sx={{ mb: 2 }}>{serverError}</Alert>}
          {!online && <Alert severity="warning" sx={{ mb: 2 }}>You’re offline — changes can’t be saved.</Alert>}
          <Stack spacing={2} sx={{ mt: 1 }}>{children}</Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={submitting}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={submitting || !online}>
            {submitting ? 'Saving…' : submitLabel}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
