/**
 * main-vue 路由
 * 严格对应旧版 app/main/js/router.js
 * 新增 menu 路由：登录后的模块卡片菜单页（含双按钮对比）
 */
import { createRouter, createWebHashHistory } from 'vue-router'

const LoginForm        = () => import('../views/LoginForm.vue')
const Recovery         = () => import('../views/Recovery.vue')
const Recover          = () => import('../views/Recover.vue')
const LoginWith        = () => import('../views/LoginWith.vue')
const AccountCreation  = () => import('../views/AccountCreation.vue')
const MenuCards        = () => import('../views/MenuCards.vue')

const routes = [
  { path: '/',                name: 'login',           component: LoginForm        },
  { path: '/create-account',  name: 'create-account',  component: AccountCreation  },
  { path: '/recovery',        name: 'recovery',        component: Recovery         },
  { path: '/recover/:uuid',   name: 'recover',         component: Recover          },
  { path: '/login-with',      name: 'login-with',      component: LoginWith        },
  { path: '/menu',            name: 'menu',            component: MenuCards        },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
