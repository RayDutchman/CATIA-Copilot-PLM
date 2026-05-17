<template>
  <!-- 顶部导航栏挂载到 #header（teleport 对应原 Backbone HeaderView el:'#header'）-->
  <Teleport to="#header">
    <AppHeader />
  </Teleport>

  <!-- 页面主体：复现原 content.html 的两列布局 -->
  <div id="content">
    <!-- 左侧导航面板（对应原 content.html 的 .module-menu） -->
    <div class="module-menu" id="account-management-menu">
      <ul class="nav well">
        <li class="nav-header">{{ t('ACCOUNT') }}</li>
      </ul>
    </div>

    <!-- 主内容区（对应原 #account-management-content） -->
    <div id="account-management-content">
      <RouterView />
    </div>
  </div>
</template>

<script setup>
import { RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppHeader from '../vue-common/components/AppHeader.vue'

const { t } = useI18n()
</script>
