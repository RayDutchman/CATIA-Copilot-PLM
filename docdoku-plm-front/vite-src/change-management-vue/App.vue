<template>
  <!-- AppHeader teleport 到固定的 #header 挂载点 -->
  <Teleport to="#header">
    <AppHeader :workspaceId="workspaceId" />
  </Teleport>

  <!-- 主内容区：左侧导航 + 右侧内容（对应原 content.html 布局） -->
  <div id="content" class="container-fluid" style="display:flex;margin-top:40px;">
    <!-- 左侧导航，对应 #change-management-menu -->
    <div class="module-menu" id="change-management-menu" style="min-width:180px;margin-right:16px;">
      <ul class="nav well">
        <li class="nav-header">{{ t('WORKSPACE') }} : {{ workspaceId }}</li>

        <li :class="{ active: isRoute('workflows') }">
          <router-link :to="`/${workspaceId}/workflows`">
            <i class="fa fa-tasks"></i> {{ t('WORKFLOWS') }}
          </router-link>
        </li>

        <li :class="{ active: isRoute('milestones') }">
          <router-link :to="`/${workspaceId}/milestones`">
            <i class="fa fa-calendar-check-o"></i> {{ t('MILESTONES') }}
          </router-link>
        </li>

        <li :class="{ active: isRoute('issues') }">
          <router-link :to="`/${workspaceId}/issues`">
            <i class="fa fa-bug"></i> {{ t('ISSUES') }}
          </router-link>
        </li>

        <li :class="{ active: isRoute('requests') }">
          <router-link :to="`/${workspaceId}/requests`">
            <i class="fa fa-ticket"></i> {{ t('REQUESTS') }}
          </router-link>
        </li>

        <li :class="{ active: isRoute('orders') }">
          <router-link :to="`/${workspaceId}/orders`">
            <i class="fa fa-archive"></i> {{ t('ORDERS') }}
          </router-link>
        </li>
      </ul>
    </div>

    <!-- 右侧内容区，对应 #change-management-content -->
    <div id="change-management-content" style="flex:1;min-width:0;">
      <RouterView />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppHeader from '../vue-common/components/AppHeader.vue'

const { t } = useI18n()
const route = useRoute()

// 从路由参数取当前工作区 ID
const workspaceId = computed(() => route.params.workspaceId || '')

// 判断当前激活路由名称
function isRoute(name) {
  return route.name === name
}
</script>
