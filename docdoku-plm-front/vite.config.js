import { defineConfig } from 'vite'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'

// Vite 配置 —— 以 vite-src/ 为根目录，逐模块迁移
export default defineConfig({
  plugins: [vue()],
  // 所有页面入口放在 vite-src/ 下
  root: resolve(__dirname, 'vite-src'),

  build: {
    outDir: resolve(__dirname, 'dist-vite'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        // 阶段 2 试点：download 模块（Backbone+ESM，已验收）
        download: resolve(__dirname, 'vite-src/download/index.html'),
        // 阶段 2：account-management 模块（Backbone+ESM，已验收）
        'account-management': resolve(__dirname, 'vite-src/account-management/index.html'),
        // 阶段 3：account-management-vue 模块（Vue 3 SFC 重写，验证中）
        'account-management-vue': resolve(__dirname, 'vite-src/account-management-vue/index.html'),
        // 阶段 4：workspace-management-vue 模块（Vue 3 SFC 重写）
        'workspace-management-vue': resolve(__dirname, 'vite-src/workspace-management-vue/index.html'),
        // 阶段 5：change-management-vue 模块（Vue 3 SFC 重写）
        'change-management-vue': resolve(__dirname, 'vite-src/change-management-vue/index.html'),
        // 阶段 6：document-management-vue 模块（Vue 3 SFC 重写）
        'document-management-vue': resolve(__dirname, 'vite-src/document-management-vue/index.html'),
        // 阶段 7：main-vue 模块（Vue 版登录 + 模块卡片菜单，含 [Vue版]/[原版] 双按钮）
        'main-vue': resolve(__dirname, 'vite-src/main-vue/index.html'),
      },
    },
  },

  server: {
    port: 9090,
    proxy: {
      // 代理后端 REST API（docker 暴露在 8001 端口）
      '/docdoku-plm-server-rest': 'http://localhost:8001',
      // 以下均由 nginx 前端容器（端口 8000）提供
      '/webapp.properties.json': 'http://localhost:8000',
      // HTML 模板中引用的运行时图片（如 /images/windows.gif）
      '/images': 'http://localhost:8000',
      // 下载文件（如 /download/dplm/*.zip）—— 注意：Vite 自身的 /download/ 页面优先
      // '/download': 'http://localhost:8000',  // 暂不代理，避免与 vite-src/download/ 冲突
    },
  },

  css: {
    preprocessorOptions: {
      less: {
        // Less 变量目录，与旧 Grunt 配置保持一致
        paths: [resolve(__dirname, 'app/less')],
      },
    },
  },

  resolve: {
    alias: {
      // 方便 vite-src 中引用旧的共享模块（逐步迁移）
      'common-objects': resolve(__dirname, 'vite-src/common-objects'),
      'localization':   resolve(__dirname, 'vite-src/localization'),
      'vue-common':     resolve(__dirname, 'vite-src/vue-common'),
    },
  },
})
