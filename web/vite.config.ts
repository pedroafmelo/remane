import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Em desenvolvimento, a API do FastAPI roda na porta 8000 (mesmo origin em produção).
const api = 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': api,
      '/auth': api,
      '/health': api,
    },
  },
})
