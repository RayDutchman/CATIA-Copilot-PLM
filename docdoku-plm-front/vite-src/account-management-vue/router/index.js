/**
 * account-management-vue 路由配置
 * 原：vite-src/account-management/js/router.js（单路由 '' → EditAccount）
 */
import { createRouter, createWebHashHistory } from 'vue-router'
import EditAccount from '../views/EditAccount.vue'

const routes = [
  { path: '/', component: EditAccount },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
