import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/morning-radio': 'http://127.0.0.1:8000',
      '/book-recommendation': 'http://127.0.0.1:8000',
      '/travel-planner': 'http://127.0.0.1:8000',
      '/morning-history': 'http://127.0.0.1:8000'
    }
  }
})
