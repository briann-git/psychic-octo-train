import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8080'
    }
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main:   resolve(__dirname, 'index.html'),
        mobile: resolve(__dirname, 'mobile/index.html'),
      },
    },
  },
})
