import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'prompt',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'Team Management',
        short_name: 'TeamMgmt',
        description: 'Centralized team management and organizational analytics',
        theme_color: '#1565c0',
        background_color: '#f5f7fa',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'maskable-icon-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        // Read GETs: serve from network, fall back to cache when offline.
        // Mutations (POST/PUT/DELETE) are network-only (not matched here).
        runtimeCaching: [
          {
            urlPattern: ({ url, request }) => request.method === 'GET' && url.pathname.startsWith('/api/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
      // Keep the service worker out of `npm run dev` to avoid caching during
      // active development; it is built and active in production.
      devOptions: { enabled: false },
    }),
  ],
  server: {
    port: 3000,
  },
});
