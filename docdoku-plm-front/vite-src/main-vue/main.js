/**
 * main-vue 模块入口（Vue 3 版登录页 + 登录后模块卡片菜单）
 *
 * 行为约定：
 *   - 路由 ''            → 登录表单
 *   - 路由 'create-account' → 注册表单
 *   - 路由 'recovery'    → 找回密码
 *   - 路由 'recover/:uuid' → 重置密码
 *   - 路由 'login-with'  → OIDC 选 provider
 *   - 路由 'menu'        → 登录后的模块卡片菜单页（含 [Vue版] [原版] 双链接）
 *
 * 默认对比模式：菜单页始终显示双按钮（用户已要求"保留原版链接便于人工对比测试"）。
 * 未 vue 化的 6 个模块（product-management, product-structure, organization-management,
 * parts, visualization, documents）只显示 [原版] 按钮。
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import i18n, { mergeModuleStrings } from '../vue-common/i18n.js'
import mainStrings from '../localization/main-vue.js'
import { useAppStore } from '../vue-common/store/app.js'
import App from './App.vue'
import router from './router/index.js'

// 复用原 main 模块样式（保留原版视觉效果，新版组件可叠加 scoped 样式）
import '../../app/less/main/style.less'

async function bootstrap() {
  mergeModuleStrings(mainStrings)

  const pinia = createPinia()

  // 临时挂载 pinia 以便在挂载主 App 前调用 store
  const tmpApp = createApp({ render: () => null })
  tmpApp.use(pinia)
  tmpApp.mount(document.createElement('div'))

  const appStore = useAppStore()

  try {
    // 加载服务器配置（webapp.properties.json 在根路径，相对 /main-vue/ 用 '..'）
    await appStore.resolveServerProperties('..')
  } catch (err) {
    console.error('[main-vue] resolveServerProperties failed:', err)
    // 即便配置加载失败也继续挂载登录表单，提示用户后端不可达
  }

  const app = createApp(App)
  app.use(pinia)
  app.use(router)
  app.use(i18n)
  app.mount('#app')
}

bootstrap()
