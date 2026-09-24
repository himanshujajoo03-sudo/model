import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

// Resolve the monorepo root (D:\SIH\SIH26069) from services/frontend/
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '../../')

export default defineConfig({
  plugins: [react()],
  // Load .env from the project root rather than from services/frontend/
  // Root .env lives at: D:\SIH\SIH26069\.env
  envDir: repoRoot,
  server: {
  host: '0.0.0.0',
  port: 5173,
  allowedHosts: true,
  watch: {
    usePolling: true,
  },
},
})
