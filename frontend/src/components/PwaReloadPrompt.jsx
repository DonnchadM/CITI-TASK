import { useRegisterSW } from 'virtual:pwa-register/react';
import { Alert, Button, Snackbar } from '@mui/material';

// Surfaces PWA lifecycle: a one-off "ready offline" toast, and a prompt to
// reload when a new version of the app has been deployed.
export function PwaReloadPrompt() {
  const {
    offlineReady: [offlineReady, setOfflineReady],
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW();

  const close = () => { setOfflineReady(false); setNeedRefresh(false); };

  if (needRefresh) {
    return (
      <Snackbar open anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert
          severity="info"
          action={<Button color="inherit" size="small" onClick={() => updateServiceWorker(true)}>Reload</Button>}
        >
          A new version is available.
        </Alert>
      </Snackbar>
    );
  }

  if (offlineReady) {
    return (
      <Snackbar open autoHideDuration={4000} onClose={close} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="success" onClose={close}>Ready to work offline.</Alert>
      </Snackbar>
    );
  }

  return null;
}
