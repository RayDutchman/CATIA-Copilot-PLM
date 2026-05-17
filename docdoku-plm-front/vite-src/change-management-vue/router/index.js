/**
 * change-management-vue 路由
 * 原 Backbone Router 路由结构：
 *   :workspaceId/workflows  → WorkflowList
 *   :workspaceId/milestones → MilestoneList
 *   :workspaceId/issues     → IssueList
 *   :workspaceId/requests   → RequestList
 *   :workspaceId/orders     → OrderList
 *   :workspaceId/tasks      → TaskList
 *   :workspaceId            → 重定向到 workflows
 */
import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../../vue-common/store/auth.js'

// 懒加载各视图，减小首屏包体积
const WorkflowList  = () => import('../views/WorkflowList.vue')
const MilestoneList = () => import('../views/MilestoneList.vue')
const IssueList     = () => import('../views/IssueList.vue')
const RequestList   = () => import('../views/RequestList.vue')
const OrderList     = () => import('../views/OrderList.vue')
const TaskList      = () => import('../views/TaskList.vue')

const routes = [
  // 带 workspaceId 的路由
  { path: '/:workspaceId/workflows',  name: 'workflows',  component: WorkflowList },
  { path: '/:workspaceId/milestones', name: 'milestones', component: MilestoneList },
  { path: '/:workspaceId/issues',     name: 'issues',     component: IssueList },
  { path: '/:workspaceId/requests',   name: 'requests',   component: RequestList },
  { path: '/:workspaceId/orders',     name: 'orders',     component: OrderList },
  { path: '/:workspaceId/tasks/:taskId?', name: 'tasks',  component: TaskList },
  // 仅 workspaceId → 默认跳转到 workflows
  { path: '/:workspaceId', redirect: to => ({ name: 'workflows', params: { workspaceId: to.params.workspaceId } }) },
  // 根路径 → 跳转到 workspace-management-vue 选择工作区
  { path: '/', redirect: '/Workspace_0/workflows' }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 导航守卫：未认证则跳回登录
router.beforeEach(() => {
  const auth = useAuthStore()
  if (!auth.account) {
    // 账户尚未加载时放行（main.js 会处理）
    return true
  }
  return true
})

export default router
