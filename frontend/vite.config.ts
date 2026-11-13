import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/members': 'http://127.0.0.1:8000',
      '/plans': 'http://127.0.0.1:8000',
      '/memberships': 'http://127.0.0.1:8000',
      '/invoices': 'http://127.0.0.1:8000',
      '/payments': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
});
