import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiTarget = process.env.VITE_API_URL ?? 'https://po-educacional-production-5497.up.railway.app'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': apiTarget,
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 8080,
    allowedHosts: ['rare-adventure-production-e8d7.up.railway.app'],
  },
})
