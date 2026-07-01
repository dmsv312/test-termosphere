import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// В dev фронт крутится на :5173 и проксирует /api на локальный uvicorn (:8010).
// В проде статику отдаёт nginx, он же проксирует /api на контейнер api — тот же origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8010', changeOrigin: true },
    },
  },
})
