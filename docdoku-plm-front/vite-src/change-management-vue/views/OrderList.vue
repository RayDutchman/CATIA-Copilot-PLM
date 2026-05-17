<template>
  <!-- 订单列表：复用 ChangeItemList 通用组件，type="orders" -->
  <div>
    <h2>{{ t('ORDERS') }}</h2>
    <ChangeItemList type="orders" />
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import ChangeItemList from '../components/ChangeItemList.vue'
const { t } = useI18n()
</script>
