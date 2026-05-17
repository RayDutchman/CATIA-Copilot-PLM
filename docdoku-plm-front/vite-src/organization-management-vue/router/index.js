/**
 * organization-management-vue 路由配置
 * 对应原 app/organization-management/js/router.js 的 hash 路由
 */
import { createRouter, createWebHashHistory } from 'vue-router'
import OrgHome    from '../views/OrgHome.vue'
import OrgCreate  from '../views/OrgCreate.vue'
import OrgEdit    from '../views/OrgEdit.vue'
import OrgMembers from '../views/OrgMembers.vue'

const routes = [
  { path: '/',        name: 'OrgHome',    component: OrgHome },
  { path: '/create',  name: 'OrgCreate',  component: OrgCreate },
  { path: '/edit',    name: 'OrgEdit',    component: OrgEdit },
  { path: '/members', name: 'OrgMembers', component: OrgMembers },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
