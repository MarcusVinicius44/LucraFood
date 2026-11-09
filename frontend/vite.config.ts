/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// O front chama /api/... e o Vite repassa para o Django (runserver em 8000).
// Assim o código não guarda endereço de servidor nem depende do CORS.
// LUCRAFOOD_BACKEND troca o alvo (ex.: um Django de teste em outra porta, com outro banco).
const backend = process.env.LUCRAFOOD_BACKEND ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': backend,
    },
  },
  test: {
    environment: 'node',
  },
})
