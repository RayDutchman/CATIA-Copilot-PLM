/**
 * workspace-management-vue 路由配置
 * 使用 hash history（对应原版 Backbone Router hash 路由）
 * nginx 侧用 =404 fallback，无需 try_files SPA 重定向
 */
import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../../vue-common/store/auth.js'

// 懒加载各视图组件，减小初始包体积
const Home                  = () => import('../views/Home.vue')
const WorkspaceCreate       = () => import('../views/WorkspaceCreate.vue')
const WorkspaceEdit         = () => import('../views/WorkspaceEdit.vue')
const WorkspaceUsers        = () => import('../views/WorkspaceUsers.vue')
const WorkspaceDashboard    = () => import('../views/WorkspaceDashboard.vue')
const WorkspaceNotifications = () => import('../views/WorkspaceNotifications.vue')
const WorkspaceCustomizations = () => import('../views/WorkspaceCustomizations.vue')
const WorkspaceAdminNew     = () => import('../views/WorkspaceAdminNew.vue')
const AdminDashboard        = () => import('../views/AdminDashboard.vue')
const AdminAccounts         = () => import('../views/AdminAccounts.vue')

/** 检查当前用户是否为指定工作区的管理员 */
function isWorkspaceAdmin(workspaceId) {
  const authStore = useAuthStore()
  return authStore.workspaces.administratedWorkspaces.some(w => w.id === workspaceId)
}

/** 检查当前用户是否为平台超级管理员 */
function isRootAdmin() {
  const authStore = useAuthStore()
  return authStore.isAdmin
}

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/create',
    name: 'WorkspaceCreate',
    component: WorkspaceCreate
  },
  // 工作区子页面（需要工作区管理员权限）
  {
    path: '/workspace/:workspaceId/users',
    name: 'WorkspaceUsers',
    component: WorkspaceUsers,
    beforeEnter: (to) => {
      if (!isWorkspaceAdmin(to.params.workspaceId)) return '/'
    }
  },
  {
    path: '/workspace/:workspaceId/edit',
    name: 'WorkspaceEdit',
    component: WorkspaceEdit,
    beforeEnter: (to) => {
      if (!isWorkspaceAdmin(to.params.workspaceId)) return '/'
    }
  },
  {
    path: '/workspace/:workspaceId/dashboard',
    name: 'WorkspaceDashboard',
    component: WorkspaceDashboard,
    beforeEnter: (to) => {
      if (!isWorkspaceAdmin(to.params.workspaceId)) return '/'
    }
  },
  {
    path: '/workspace/:workspaceId/notifications',
    name: 'WorkspaceNotifications',
    component: WorkspaceNotifications,
    beforeEnter: (to) => {
      if (!isWorkspaceAdmin(to.params.workspaceId)) return '/'
    }
  },
  {
    path: '/workspace/:workspaceId/customizations',
    name: 'WorkspaceCustomizations',
    component: WorkspaceCustomizations,
    beforeEnter: (to) => {
      if (!isWorkspaceAdmin(to.params.workspaceId)) return '/'
    }
  },
  {
    path: '/workspace/:workspaceId/admin/new',
    name: 'WorkspaceAdminNew',
    component: WorkspaceAdminNew,
    beforeEnter: (to) => {
      if (!isWorkspaceAdmin(to.params.workspaceId)) return '/'
    }
  },
  // 超级管理员专属页面
  {
    path: '/admin/dashboard',
    name: 'AdminDashboard',
    component: AdminDashboard,
    beforeEnter: () => {
      if (!isRootAdmin()) return '/'
    }
  },
  {
    path: '/admin/accounts',
    name: 'AdminAccounts',
    component: AdminAccounts,
    beforeEnter: () => {
      if (!isRootAdmin()) return '/'
    }
  },
  // 未匹配路由重定向到首页
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
