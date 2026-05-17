<template>
  <!-- 任务列表（当前用户被分配的任务）
       API: GET /workspaces/:ws/tasks/:login/assigned
       字段：workspaceId, workflowId, activityStep, num, title,
             holderReference, holderVersion, targetIteration, status -->
  <div>
    <h2>{{ t('TASKS') }}</h2>

    <p v-if="error" class="alert alert-error">{{ error }}</p>

    <table class="table table-striped table-condensed">
      <thead>
        <tr>
          <th>#</th>
          <th>{{ t('TASK_TITLE') }}</th>
          <th>{{ t('TASK_HOLDER') }}</th>
          <th>{{ t('TASK_STATUS') }}</th>
          <th>{{ t('TASK_ACTIVITY') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading"><td colspan="5">…</td></tr>
        <tr v-else-if="items.length === 0"><td colspan="5">{{ t('NO_DATA') }}</td></tr>
        <tr v-for="(item, idx) in items" :key="`${item.workflowId}-${item.num}`">
          <td>{{ idx + 1 }}</td>
          <td>{{ item.title }}</td>
          <td>{{ item.holderReference }} {{ item.holderVersion }}</td>
          <td>
            <span :class="statusClass(item.status)">{{ item.status }}</span>
          </td>
          <td>{{ item.activityStep }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import { useAuthStore } from '../../vue-common/store/auth.js'

const { t } = useI18n()
const route    = useRoute()
const api      = useApi()
const authStore = useAuthStore()

const workspaceId = computed(() => route.params.workspaceId)
// 当前登录用户的 login
const login = computed(() => authStore.account?.login || '')

const items   = ref([])
const loading = ref(false)
const error   = ref('')

function statusClass(status) {
  const map = {
    IN_PROGRESS: 'label label-info',
    COMPLETE:    'label label-success',
    REJECTED:    'label label-important',
    NOT_STARTED: 'label'
  }
  return map[status] || 'label'
}

async function load() {
  if (!login.value) return
  loading.value = true
  error.value   = ''
  try {
    const data = await api.get(`/workspaces/${workspaceId.value}/tasks/${login.value}/assigned`)
    items.value = Array.isArray(data) ? data : []
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => [workspaceId.value, login.value], load)
</script>
