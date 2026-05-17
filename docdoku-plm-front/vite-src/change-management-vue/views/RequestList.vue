<template>
  <!-- 请求列表：复用 ChangeItemList 通用组件，type="requests" -->
  <div>
    <h2>{{ t('REQUESTS') }}</h2>
    <ChangeItemList type="requests" />
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import ChangeItemList from '../components/ChangeItemList.vue'
const { t } = useI18n()
</script>
