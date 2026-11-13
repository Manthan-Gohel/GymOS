import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/complaints': 'http://127.0.0.1:8000',
      '/dashboard': 'http://127.0.0.1:8000',
      '/equipment': 'http://127.0.0.1:8000',
      '/expenses': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/invoices': 'http://127.0.0.1:8000',
      '/leads': 'http://127.0.0.1:8000',
      '/maintenance': 'http://127.0.0.1:8000',
      '/members': 'http://127.0.0.1:8000',
      '/memberships': 'http://127.0.0.1:8000',
      '/message-templates': 'http://127.0.0.1:8000',
      '/messages': 'http://127.0.0.1:8000',
      '/payments': 'http://127.0.0.1:8000',
      '/payroll': 'http://127.0.0.1:8000',
      '/plans': 'http://127.0.0.1:8000',
      '/reminders': 'http://127.0.0.1:8000',
      '/sessions': 'http://127.0.0.1:8000',
      '/staff-attendance': 'http://127.0.0.1:8000',
      '/trainers': 'http://127.0.0.1:8000',
      '/users': 'http://127.0.0.1:8000',
      '/whatsapp': 'http://127.0.0.1:8000',
    },
  },
});

