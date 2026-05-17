<template>
  <!-- 顶部导航栏挂载到 #header（teleport 对应原 Backbone HeaderView el:'#header'）-->
  <Teleport to="#header">
    <AppHeader :workspaceId="workspaceId" />
  </Teleport>

  <!-- 页面主体：复现原 content.html 的两列布局 -->
  <div id="content">
    <!-- 左侧导航面板（对应原 content.html 的 .module-menu） -->
    <div class="module-menu" id="workspace-management-menu">
      <ul class="nav well">
        <li class="nav-header">{{ t('WORKSPACES_ADMINISTRATION') }}</li>

        <!-- 工作区子页模式：有 workspaceId 时显示子导航 -->
        <template v-if="workspaceId">
          <li class="header nav-list-entry">
            <router-link to="/">{{ t('BACK') }}</router-link>
          </li>
          <li :class="['header', 'nav-list-entry', { active: route.name === 'WorkspaceEdit' }]">
            <router-link :to="`/workspace/${workspaceId}/edit`">{{ t('EDIT') }}</router-link>
          </li>
          <li :class="['header', 'nav-list-entry', { active: route.name === 'WorkspaceUsers' }]">
            <router-link :to="`/workspace/${workspaceId}/users`">{{ t('USERS') }}</router-link>
          </li>
          <!-- 非超级管理员才显示自定义和通知 -->
          <template v-if="!isAdmin">
            <li :class="['header', 'nav-list-entry', { active: route.name === 'WorkspaceCustomizations' }]">
              <router-link :to="`/workspace/${workspaceId}/customizations`">{{ t('CUSTOMIZATIONS') }}</router-link>
            </li>
            <li :class="['header', 'nav-list-entry', { active: route.name === 'WorkspaceNotifications' }]">
              <router-link :to="`/workspace/${workspaceId}/notifications`">{{ t('NOTIFICATIONS') }}</router-link>
            </li>
          </template>
          <li :class="['header', 'nav-list-entry', { active: route.name === 'WorkspaceDashboard' }]">
            <router-link :to="`/workspace/${workspaceId}/dashboard`">{{ t('DASHBOARD') }}</router-link>
          </li>
        </template>

        <!-- 首页模式：无 workspaceId 时显示工作区列表 -->
        <template v-else>
          <!-- 非超级管理员显示"+ 创建工作区" -->
          <li v-if="!isAdmin" :class="['header', 'nav-list-entry', { active: route.name === 'WorkspaceCreate' }]">
            <router-link class="new-workspace" to="/create">
              <i class="fa fa-plus"></i> {{ t('CREATE_WORKSPACE') }}
            </router-link>
          </li>

          <!-- 超级管理员专属链接 -->
          <template v-if="isAdmin">
            <li :class="['header', 'nav-list-entry', { active: route.name === 'AdminDashboard' }]">
              <router-link to="/admin/dashboard">{{ t('ADMIN_DASHBOARD') }}</router-link>
            </li>
            <li :class="['header', 'nav-list-entry', { active: route.name === 'AdminAccounts' }]">
              <router-link to="/admin/accounts">{{ t('ACCOUNTS') }}</router-link>
            </li>
          </template>

          <li class="nav-header">{{ t('WORKSPACES') }}</li>

          <!-- 管理员工作区列表 -->
          <li
            v-for="ws in administratedWorkspaces"
            :key="ws.id"
            class="header nav-list-entry"
          >
            <router-link :to="`/workspace/${ws.id}/edit`">{{ ws.id }}</router-link>
          </li>

          <li class="sep"></li>
        </template>
      </ul>
    </div>

    <!-- 主内容区 -->
    <div id="workspace-management-content">
      <RouterView />
    </div>
  </div>
</template>

<script setup>
import { RouterView, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { useAuthStore } from '../vue-common/store/auth.js'
import AppHeader from '../vue-common/components/AppHeader.vue'

const { t }      = useI18n()
const route      = useRoute()
const authStore  = useAuthStore()

// 当前路由是否处于工作区子页（含 workspaceId 参数）
const workspaceId = computed(() => route.params.workspaceId || '')

// 是否超级管理员（全局 admin，非工作区管理员）
const isAdmin = computed(() => authStore.isAdmin)

// 管理员工作区列表（用于首页侧边栏）
const administratedWorkspaces = computed(
  () => authStore.workspaces.administratedWorkspaces || []
)
</script>
