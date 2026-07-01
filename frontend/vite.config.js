import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ command }) => {
  const config = {
    plugins: [
      vue(), 
      tailwindcss()
    ],
    server: {
      host: true,  
      port: 5173,
      watch: {
        usePolling: true,
      },
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    }
  }

  // Der Proxy wird NUR im lokalen Entwicklungsmodus aktiviert
  if (command === 'serve') {
    config.server.proxy = {
      '/api': {
        // 'backend' ist der Service-Name aus deiner docker-compose.yml
        target: 'http://backend:8000', 
        changeOrigin: true,
      }
    }
  }

  return config
})