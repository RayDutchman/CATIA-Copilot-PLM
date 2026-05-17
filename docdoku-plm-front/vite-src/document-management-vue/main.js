/**
 * document-management-vue 入口：
 * resolveServerProperties → resolveAccount → resolveWorkspaces → mount
 */
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import i18n, { mergeModuleStrings } from '../vue-common/i18n.js';
import documentManagementStrings from '../localization/document-management.js';
import router from './router/index.js';
import App from './App.vue';
import '../../app/less/document-management/style.less';
import { useAppStore } from '../vue-common/store/app.js';
import { useAuthStore } from '../vue-common/store/auth.js';

// 追加 document-management 模块翻译
mergeModuleStrings(documentManagementStrings);

const pinia = createPinia();
const app = createApp(App);
app.use(pinia);
app.use(i18n);
app.use(router);

// bootstrap 流程：先读服务器配置，再加载账户和工作区，最后挂载
const appStore = useAppStore(pinia);
const authStore = useAuthStore(pinia);

appStore.resolveServerProperties()
    .then(() => authStore.resolveAccount())
    .then(() => authStore.resolveWorkspaces())
    .then(() => {
        app.mount('#app');
    })
    .catch((err) => {
        console.error('[document-management-vue] 初始化失败', err);
        // 重定向到登录页
        const base = window.location.pathname.replace(/document-management-vue.*/, '');
        window.location.href = base + 'login.html';
    });
