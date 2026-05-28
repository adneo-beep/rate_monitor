import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/fss': {
        target: 'https://finlife.fss.or.kr',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/fss/, '/finlifeapi'),
      },
    },
  },
})
