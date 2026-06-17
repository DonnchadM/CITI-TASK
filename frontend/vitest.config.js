import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// Separate from vite.config.js so the PWA plugin doesn't run under tests.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    css: false,
    // Give the API client an absolute base so fetch/MSW resolve URLs in jsdom.
    env: { VITE_API_URL: 'http://localhost' },
    // Inline MUI + react-transition-group so Vite resolves their ESM directory
    // imports (Node's ESM resolver rejects them otherwise).
    server: { deps: { inline: [/@mui\//, 'react-transition-group'] } },
  },
});
