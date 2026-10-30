import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 开发时把 /api 转到本机 FastAPI，页面本身不处理跨域。
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
