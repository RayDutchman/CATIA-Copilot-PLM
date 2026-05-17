<template>
  <!-- 工作流模型列表（只读，不重建拖拽编辑器）
       API: GET /workspaces/:ws/workflow-models
            DELETE /workspaces/:ws/workflow-models/:id
       字段：id, finalLifeCycleState, author.name, creationDate, acl -->
  <div>
    <h2>{{ t('WORKFLOWS') }}</h2>

    <div class="actions well">
      <button class="btn btn-danger" :disabled="selected.length === 0" @click="deleteSelected">
        <i class="fa fa-times"></i>
      </button>
    </div>

    <p v-if="error" class="alert alert-error">{{ error }}</p>

    <table class="table table-striped table-condensed">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
          <th>{{ t('WORKFLOW_REFERENCE') }}</th>
          <th>{{ t('WORKFLOW_FINAL_LIFECYCLE_STATE') }}</th>
          <th>{{ t('AUTHOR') }}</th>
          <th>{{ t('CREATION_DATE') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading"><td colspan="5">…</td></tr>
        <tr v-else-if="items.length === 0"><td colspan="5">{{ t('NO_DATA') }}</td></tr>
        <tr v-for="item in items" :key="item.id">
          <td>
            <input type="checkbox" :value="item.id" v-model="selected" />
          </td>
          <td><i class="fa fa-tasks"></i> {{ item.id }}</td>
          <td>{{ item.finalLifeCycleState }}</td>
          <td>{{ item.author && item.author.name }}</td>
          <td>{{ formatDate(item.creationDate) }}</td>
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

const { t } = useI18n()
const route = useRoute()
const api   = useApi()

const workspaceId = computed(() => route.params.workspaceId)
const items    = ref([])
const loading  = ref(false)
const error    = ref('')
const selected = ref([])
const allChecked = computed(() =>
  items.value.length > 0 && selected.value.length === items.value.length
)
function toggleAll(e) {
  selected.value = e.target.checked ? items.value.map(i => i.id) : []
}

function formatDate(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString()
}

async function load() {
  loading.value = true
  error.value   = ''
  try {
    const data = await api.get(`/workspaces/${workspaceId.value}/workflow-models`)
    items.value = Array.isArray(data) ? data : []
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => workspaceId.value, load)

async function deleteSelected() {
  if (!window.confirm(t('CONFIRM_DELETE_WORKFLOW'))) return
  error.value = ''
  try {
    await Promise.all(
      selected.value.map(id =>
        api.del(`/workspaces/${workspaceId.value}/workflow-models/${id}`)
      )
    )
    selected.value = []
    await load()
  } catch (e) {
    error.value = e.message || String(e)
  }
}
</script>
