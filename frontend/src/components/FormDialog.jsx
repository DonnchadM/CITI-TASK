import {
  Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack,
} from '@mui/material';

// Generic dialog wrapper for create/edit forms: title, server-error alert,
// the form fields (children), and Cancel/Save actions with a busy state.
export function FormDialog({
  open, title, onClose, onSubmit, submitting = false, serverError, submitLabel = 'Save', children,
}) {
  return (
    <Dialog open={open} onClose={submitting ? undefined : onClose} fullWidth maxWidth="sm">
      <form onSubmit={onSubmit} noValidate>
        <DialogTitle>{title}</DialogTitle>
        <DialogContent>
          {serverError && <Alert severity="error" sx={{ mb: 2 }}>{serverError}</Alert>}
          <Stack spacing={2} sx={{ mt: 1 }}>{children}</Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={submitting}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={submitting}>
            {submitting ? 'Saving…' : submitLabel}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
