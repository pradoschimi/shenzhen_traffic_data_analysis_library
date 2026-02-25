import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Vite 构建配置
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // 开发的时候前端跑在 5173 端口，后端跑在 8000 端口
    // 这里把 /api 开头的请求代理到后端，避免跨域问题
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // 把大的第三方库拆成独立的 chunk，这样浏览器可以分别缓存
    // echarts 很大（~800KB），单独拆出来效果明显
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'echarts': ['echarts'],
          'element-plus': ['element-plus'],
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
        },
      },
    },
  },
})
