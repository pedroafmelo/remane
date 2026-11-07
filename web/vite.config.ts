import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em desenvolvimento, a API do FastAPI roda na porta 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
