// Vue Router 4 配置（hash 路由）
import { createRouter, createWebHashHistory } from 'vue-router';
import FolderView from '../views/FolderView.vue';
import TagsView from '../views/TagsView.vue';
import TemplatesView from '../views/TemplatesView.vue';
import BaselinesView from '../views/BaselinesView.vue';
import CheckedOutView from '../views/CheckedOutView.vue';
import TasksView from '../views/TasksView.vue';
import SearchView from '../views/SearchView.vue';

const routes = [
    // 文件夹视图（默认首页）
    { path: '/:workspaceId/folders',        name: 'folders',     component: FolderView },
    { path: '/:workspaceId/folders/:path+', name: 'folder',      component: FolderView },
    // 标签视图
    { path: '/:workspaceId/tags',           name: 'tags',        component: TagsView },
    { path: '/:workspaceId/tags/:tagId',    name: 'tag',         component: TagsView },
    // 模板视图
    { path: '/:workspaceId/templates',      name: 'templates',   component: TemplatesView },
    // 基线视图
    { path: '/:workspaceId/baselines',      name: 'baselines',   component: BaselinesView },
    // 已签出文档
    { path: '/:workspaceId/checkedouts',    name: 'checkedouts', component: CheckedOutView },
    // 任务文档
    { path: '/:workspaceId/tasks',          name: 'tasks',       component: TasksView },
    { path: '/:workspaceId/tasks/:filter',  name: 'tasks-filter',component: TasksView },
    // 搜索
    { path: '/:workspaceId/search',         name: 'search',      component: SearchView },
    // 默认重定向到文件夹
    { path: '/:workspaceId',                redirect: to => `/${to.params.workspaceId}/folders` },
    { path: '/',                            redirect: '/~/folders' }
];

const router = createRouter({
    history: createWebHashHistory(),
    routes
});

export default router;
