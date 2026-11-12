/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// O front chama /api/... e o Vite repassa para o Django (runserver em 8000).
// Assim o código não guarda endereço de servidor nem depende do CORS.
// LUCRAFOOD_BACKEND troca o alvo (ex.: um Django de teste em outra porta, com outro banco).
const backend = process.env.LUCRAFOOD_BACKEND ?? 'http://localhost:8000'

// Endereço público do site para as meta tags de prévia (LinkedIn/WhatsApp exigem URL absoluta).
// Na Vercel vem do domínio de produção; VITE_SITE_URL troca. Local: vazio (caminho relativo).
const siteUrl = (
  process.env.VITE_SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : '')
).replace(/\/$/, '')

export default defineConfig({
  plugins: [react(), { name: 'site-url', transformIndexHtml: (html) => html.replaceAll('__SITE_URL__', siteUrl) }],
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
