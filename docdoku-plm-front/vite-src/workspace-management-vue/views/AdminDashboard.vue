<template>
  <!-- 超级管理员仪表盘，对应原 admin-dashboard.html + views/admin-dashboard.js -->
  <div class="actions well">
    <router-link to="/" class="btn btn-default">{{ t('BACK') }}</router-link>
  </div>

  <div class="margin">
    <h3>{{ t('DASHBOARD') }}</h3>
    <p>{{ t('ROOT_ADMIN_MESSAGE') }}</p>

    <div v-if="loading">Loading…</div>
    <div v-else class="charts workspace-chart-container">
      <!-- 磁盘用量 -->
      <div class="chart well-large well workspace-chart">
        <h3>{{ t('DISK_USAGE') }}</h3>
        <p v-if="diskUsage">
          {{ t('DISK_USAGE_TOTAL') }}: <strong>{{ formatBytes(totalDiskUsage) }}</strong>
        </p>
        <table v-if="diskUsageItems.length" class="table table-condensed">
          <tbody>
            <tr v-for="item in diskUsageItems" :key="item.key">
              <td>{{ item.key }}</td>
              <td>{{ formatBytes(item.value) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else>{{ t('NO_DATA') }}</p>
      </div>

      <!-- 实体统计 -->
      <div class="chart well-large well workspace-chart">
        <h3>{{ t('ENTITIES') }}</h3>
        <table v-if="stats" class="table table-condensed">
          <tbody>
            <tr><td>{{ t('USERS') }}</td><td>{{ stats.users }}</td></tr>
            <tr><td>{{ t('DOCUMENTS') }}</td><td>{{ stats.documents }}</td></tr>
            <tr><td>{{ t('PARTS') }}</td><td>{{ stats.parts }}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'

const { t } = useI18n()
const api   = useApi()

const loading      = ref(true)
const diskUsage    = ref(null)
const stats        = ref(null)

const diskUsageItems = computed(() => {
  if (!diskUsage.value) return []
  return Object.entries(diskUsage.value)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ key: k, value: v }))
})

const totalDiskUsage = computed(() =>
  diskUsageItems.value.reduce((s, i) => s + i.value, 0)
)

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0, n = bytes
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++ }
  return n.toFixed(1) + ' ' + units[i]
}

onMounted(async () => {
  try {
    const [du, st] = await Promise.allSettled([
      api.get('/admin/disk-usage-stats'),
      api.get('/admin/stats')
    ])
    if (du.status === 'fulfilled') diskUsage.value = du.value
    if (st.status === 'fulfilled') stats.value     = st.value
  } finally {
    loading.value = false
  }
})
</script>
