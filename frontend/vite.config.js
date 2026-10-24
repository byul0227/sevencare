import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api 요청은 FastAPI(8000)로 넘겨요 → 프론트 코드에서는 '/api/...'만 쓰면 됨
// eval.html = 성분표 인식 정확도 측정 페이지 (개발용, localhost:5173/eval.html)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL('./index.html', import.meta.url)),
        eval: fileURLToPath(new URL('./eval.html', import.meta.url)),
      },
    },
  },
})
