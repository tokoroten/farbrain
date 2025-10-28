import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all addresses
    allowedHosts: [
      'farbrain.easyrec.app',
      '.easyrec.app', // Allow all subdomains
    ],
  },
})
