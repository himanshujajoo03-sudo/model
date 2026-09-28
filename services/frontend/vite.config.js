import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

// Resolve the monorepo root from services/frontend/
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '../../')
const rootEnvExists = fs.existsSync(path.resolve(repoRoot, '.env'))

export default defineConfig({
  plugins: [react()],
  // Load .env from repo root if running locally outside Docker; inside Docker fallback to __dirname (/app)
  envDir: rootEnvExists ? repoRoot : __dirname,
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true,
    },
  },
})
