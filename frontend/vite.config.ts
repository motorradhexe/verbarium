import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Inside Docker Compose this points at the backend service; locally it
  // defaults to the backend dev server on the host.
  const apiTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      // 0.0.0.0 so the dev server is reachable from outside the container.
      host: true,
      port: Number(env.VITE_PORT) || 5173,
      strictPort: true,
      watch: {
        // Bind mounts on macOS/Windows do not deliver inotify events.
        usePolling: env.VITE_USE_POLLING === 'true',
      },
      proxy: {
        '/api': { target: apiTarget, changeOrigin: true },
        '/health': { target: apiTarget, changeOrigin: true },
      },
    },
    preview: {
      host: true,
      port: Number(env.VITE_PORT) || 5173,
    },
  }
})
