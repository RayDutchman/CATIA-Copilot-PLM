<template>
  <!-- 顶部导航栏挂载到 #header（teleport 对应原 Backbone HeaderView el:'#header'）-->
  <Teleport to="#header">
    <AppHeader />
  </Teleport>

  <!-- 页面主体：复现原 content.html 的两列布局 -->
  <div id="content">
    <!-- 左侧导航面板（对应原 content.html 的 .module-menu） -->
    <div class="module-menu" id="organization-management-menu">
      <ul class="nav well">
        <li class="nav-header">{{ t('ORGANIZATION_ADMINISTRATION') }}</li>
        <li
          v-if="!hasOrg"
          :class="['header', 'nav-list-entry', { active: route.name === 'OrgCreate' }]"
        >
          <router-link to="/create">
            <i class="fa fa-plus"></i> {{ t('CREATE_ORGANIZATION_SUBTITLE') }}
          </router-link>
        </li>
        <template v-if="hasOrg">
          <li :class="['header', 'nav-list-entry', { active: route.name === 'OrgHome' }]">
            <router-link to="/">{{ t('ORGANIZATION_ADMINISTRATION') }}</router-link>
          </li>
          <li :class="['header', 'nav-list-entry', { active: route.name === 'OrgMembers' }]">
            <router-link to="/members">{{ t('MEMBERS') }}</router-link>
          </li>
          <li
            v-if="isOwner"
            :class="['header', 'nav-list-entry', { active: route.name === 'OrgEdit' }]"
          >
            <router-link to="/edit">{{ t('EDIT') }}</router-link>
          </li>
        </template>
      </ul>
    </div>

    <!-- 主内容区（对应原 #organization-management-content） -->
    <div id="organization-management-content">
      <RouterView />
    </div>
  </div>
</template>

<script setup>
import { RouterView, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { useAuthStore } from '../vue-common/store/auth.js'
import { useOrgStore }  from './store/org.js'
import AppHeader from '../vue-common/components/AppHeader.vue'

const { t }     = useI18n()
const route     = useRoute()
const authStore = useAuthStore()
const orgStore  = useOrgStore()

const hasOrg  = computed(() => orgStore.hasOrg)
// 是否为组织 owner（当前登录用户 == org.owner）
const isOwner = computed(() =>
  !!orgStore.organization && authStore.login === orgStore.organization.owner
)
</script>
