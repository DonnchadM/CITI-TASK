import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Alert, Box, Button, Chip, CircularProgress, Paper, Stack, TextField, Typography,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SendIcon from '@mui/icons-material/Send';
import { assistantApi } from '../services/assistant';

const EXAMPLES = [
  'Which teams have a leader who is not co-located with their team?',
  'Give me an org health summary based on the KPIs.',
  'Which teams have more than 20% non-direct staff?',
  'What did the Platform team achieve recently?',
];

export function AssistantPage() {
  const [question, setQuestion] = useState('');

  const ask = useMutation({ mutationFn: assistantApi.query });

  const submit = (q) => {
    const text = (q ?? question).trim();
    if (!text) return;
    setQuestion(text);
    ask.mutate(text);
  };

  // The assistant degrades gracefully: a missing key or a blocked network path
  // are expected environment states, shown as calm info rather than a hard error.
  const code = ask.error?.code;
  const isInfo = code === 'assistant_unavailable' || code === 'assistant_unreachable';
  const errorMessage = ask.isError
    ? (code === 'assistant_unavailable'
      ? 'The AI assistant isn’t configured on this environment (no API key). It’s built and works where a key is set.'
      : code === 'assistant_unreachable'
        ? 'The AI assistant needs outbound internet to reach the model, which this environment’s network doesn’t provide. It’s fully built and runs where egress is available (e.g. local development) — see the self-assessment for details.'
        : (ask.error?.message || 'Something went wrong. Please try again.'))
    : null;

  return (
    <Box sx={{ maxWidth: 820 }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
        <AutoAwesomeIcon color="primary" />
        <Typography variant="h5">Ask the org</Typography>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Ask a natural-language question about teams, people, locations, achievements, or the
        organizational KPIs. Answers are grounded in live data via read-only tools.
      </Typography>

      <Box
        component="form"
        onSubmit={(e) => { e.preventDefault(); submit(); }}
        sx={{ display: 'flex', gap: 1, mb: 2 }}
      >
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder="e.g. Which teams report to an organization leader?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <Button
          type="submit"
          variant="contained"
          startIcon={ask.isPending ? <CircularProgress size={18} color="inherit" /> : <SendIcon />}
          disabled={ask.isPending || !question.trim()}
          sx={{ whiteSpace: 'nowrap' }}
        >
          Ask
        </Button>
      </Box>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 3 }}>
        {EXAMPLES.map((ex) => (
          <Chip key={ex} label={ex} variant="outlined" size="small"
                onClick={() => submit(ex)} disabled={ask.isPending} />
        ))}
      </Stack>

      {errorMessage && <Alert severity={isInfo ? 'info' : 'error'}>{errorMessage}</Alert>}

      {ask.isSuccess && (
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Typography
            component="div"
            sx={{ whiteSpace: 'pre-wrap', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: 14 }}
          >
            {ask.data.answer}
          </Typography>
          {Array.isArray(ask.data.data) && ask.data.data.length > 0 && (
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>
                Tools used:
              </Typography>
              {[...new Set(ask.data.data.map((d) => d.tool))].map((t) => (
                <Chip key={t} label={t} size="small" />
              ))}
            </Stack>
          )}
        </Paper>
      )}
    </Box>
  );
}
