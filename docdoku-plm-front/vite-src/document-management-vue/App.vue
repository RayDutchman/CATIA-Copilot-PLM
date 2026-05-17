<template>
  <!-- 顶部导航栏（通过 Teleport 挂载到 #header） -->
  <Teleport to="#header">
    <AppHeader :workspaceId="workspaceId" />
  </Teleport>

  <!-- 主内容区：左侧导航 + 右侧内容 -->
  <div id="content" class="container-fluid">
    <div class="row-fluid">
      <!-- 左侧导航菜单 -->
      <div id="document-management-menu" class="span3">
        <ul class="nav nav-list module-menu">
          <li class="nav-header">{{ $t('DOCUMENT_MANAGEMENT') }}</li>

          <!-- 文件夹导航 -->
          <li :class="{ active: isRoute('folders') || isRoute('folder') }">
            <a @click.prevent="goFolders" href="#" class="nav-list-entry">
              <i class="fa fa-folder-open"></i> {{ $t('FOLDERS') }}
            </a>
          </li>

          <!-- 标签导航 -->
          <li :class="{ active: isRoute('tags') || isRoute('tag') }">
            <a @click.prevent="goTags" href="#" class="nav-list-entry">
              <i class="fa fa-tags"></i> {{ $t('TAGS') }}
            </a>
          </li>

          <!-- 文档模板 -->
          <li :class="{ active: isRoute('templates') }">
            <router-link :to="`/${workspaceId}/templates`" class="nav-list-entry">
              <i class="fa fa-file-text-o"></i> {{ $t('DOCUMENT_TEMPLATES') }}
            </router-link>
          </li>

          <!-- 基线/文档集合 -->
          <li :class="{ active: isRoute('baselines') }">
            <router-link :to="`/${workspaceId}/baselines`" class="nav-list-entry">
              <i class="fa fa-database"></i> {{ $t('BASELINES') }}
            </router-link>
          </li>

          <!-- 已签出文档 -->
          <li :class="{ active: isRoute('checkedouts') }">
            <router-link :to="`/${workspaceId}/checkedouts`" class="nav-list-entry">
              <i class="fa fa-lock"></i> {{ $t('CHECKOUTS') }}
            </router-link>
          </li>

          <!-- 我的任务 -->
          <li :class="{ active: isRoute('tasks') || isRoute('tasks-filter') }">
            <a @click.prevent="goTasks" href="#" class="nav-list-entry">
              <i class="fa fa-tasks"></i> {{ $t('TASKS') }}
            </a>
          </li>

          <!-- 搜索 -->
          <li :class="{ active: isRoute('search') }">
            <router-link :to="`/${workspaceId}/search`" class="nav-list-entry">
              <i class="fa fa-search"></i> {{ $t('SEARCH') }}
            </router-link>
          </li>
        </ul>
      </div>

      <!-- 右侧内容区 -->
      <div id="document-management-content" class="span9">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../vue-common/store/auth.js';
import AppHeader from '../vue-common/components/AppHeader.vue';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

// 当前工作区 ID
const workspaceId = computed(() => {
    return route.params.workspaceId ||
        authStore.workspaces?.administratedWorkspaces?.[0]?.id ||
        authStore.workspaces?.allWorkspaces?.[0]?.id || '';
});

// 判断当前路由名称
function isRoute(name) {
    return route.name === name;
}

// 跳转到文件夹根视图
function goFolders() {
    router.push(`/${workspaceId.value}/folders`);
}

// 跳转到标签视图
function goTags() {
    router.push(`/${workspaceId.value}/tags`);
}

// 跳转到任务视图
function goTasks() {
    router.push(`/${workspaceId.value}/tasks`);
}
</script>
