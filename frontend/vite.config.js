import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        // Overridable so a second backend can be run alongside one already
        // holding 5001 — `VITE_API_PROXY=http://127.0.0.1:5002 npm run dev`.
        // The default is unchanged, so the usual workflow needs no env var.
        target: process.env.VITE_API_PROXY || 'http://127.0.0.1:5001',
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
