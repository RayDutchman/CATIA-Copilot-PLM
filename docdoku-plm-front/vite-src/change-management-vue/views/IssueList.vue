<template>
  <!-- 问题列表：复用 ChangeItemList 通用组件，type="issues" -->
  <div>
    <h2>{{ t('ISSUES') }}</h2>
    <ChangeItemList type="issues" />
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import ChangeItemList from '../components/ChangeItemList.vue'
const { t } = useI18n()
</script>
