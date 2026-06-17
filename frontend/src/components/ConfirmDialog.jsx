import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle,
} from '@mui/material';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

// Generic confirmation dialog, used for destructive actions like delete.
// The confirm action is disabled while offline (mutations are network-only).
export function ConfirmDialog({
  open, title, message, confirmLabel = 'Delete', onConfirm, onClose, busy = false,
}) {
  const online = useOnlineStatus();
  return (
    <Dialog open={open} onClose={busy ? undefined : onClose}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
        {!online && <Alert severity="warning" sx={{ mt: 2 }}>You’re offline — this action can’t be completed.</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button color="error" variant="contained" onClick={onConfirm} disabled={busy || !online}>
          {confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
