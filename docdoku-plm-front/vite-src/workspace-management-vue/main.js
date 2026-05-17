/**
 * workspace-management-vue 模块入口
 *
 * 启动流程（对应原 AMD main.js → contextResolver → buildView）：
 *   1. resolveServerProperties  ── 加载 webapp.properties.json，初始化 apiEndPoint
 *   2. resolveAccount           ── 加载当前用户，同步 locale（如 locale 变更则 reload）
 *   3. resolveWorkspaces        ── 加载工作区列表，供页面和 Header 下拉使用
 *   4. createApp + mount        ── 挂载 Vue 3 应用
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import i18n, { mergeModuleStrings } from '../vue-common/i18n.js'
import workspaceStrings from '../localization/workspace-management.js'
import { useAppStore } from '../vue-common/store/app.js'
import { useAuthStore } from '../vue-common/store/auth.js'
import App from './App.vue'
import router from './router/index.js'

// Less 样式（沿用原有 app/less/，不复制）
import '../../app/less/workspace-management/style.less'

async function bootstrap() {
  // 追加模块级翻译
  mergeModuleStrings(workspaceStrings)

  // 初始化 Pinia
  const pinia = createPinia()

  // 临时挂载 pinia 以便在挂载前使用 store
  const tmpApp = createApp({ render: () => null })
  tmpApp.use(pinia)
  tmpApp.mount(document.createElement('div'))

  const appStore  = useAppStore()
  const authStore = useAuthStore()

  try {
    // 步骤 1：加载服务器配置
    await appStore.resolveServerProperties('..')

    // 步骤 2：加载账户信息（若 locale 不一致会自动 reload）
    await authStore.resolveAccount()

    // 步骤 3：加载工作区列表（页面核心数据）
    await authStore.resolveWorkspaces()
  } catch (err) {
    console.error('[workspace-management] bootstrap failed:', err)
    window.location.href = '../index.html?denied=true'
    return
  }

  // 步骤 4：挂载 Vue 应用
  const app = createApp(App)
  app.use(pinia)
  app.use(router)
  app.use(i18n)
  app.mount('#app')
}

bootstrap()
