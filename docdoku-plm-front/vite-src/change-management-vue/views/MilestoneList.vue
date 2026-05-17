<template>
  <!-- 里程碑列表
       API: GET/POST/PUT/DELETE /workspaces/:ws/changes/milestones[/:id]
       字段：id, title, dueDate, description, workspaceId,
             numberOfRequests, numberOfOrders, acl, writable -->
  <div>
    <h2>{{ t('MILESTONES') }}</h2>

    <div class="actions well">
      <button class="btn btn-primary" @click="openCreate">
        <i class="fa fa-plus"></i>
      </button>
      <button class="btn btn-danger" :disabled="selected.length === 0" @click="deleteSelected">
        <i class="fa fa-times"></i>
      </button>
    </div>

    <p v-if="error" class="alert alert-error">{{ error }}</p>

    <table class="table table-striped table-condensed">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
          <th>{{ t('MILESTONE_TITLE') }}</th>
          <th>{{ t('MILESTONE_DUE_DATE') }}</th>
          <th>{{ t('MILESTONE_REQUESTS') }}</th>
          <th>{{ t('MILESTONE_ORDERS') }}</th>
          <th>{{ t('DESCRIPTION') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading"><td colspan="6">…</td></tr>
        <tr v-else-if="items.length === 0"><td colspan="6">{{ t('NO_DATA') }}</td></tr>
        <tr
          v-for="item in items"
          :key="item.id"
          style="cursor:pointer"
          @click="openEdit(item)"
        >
          <td @click.stop>
            <input type="checkbox" :value="item.id" v-model="selected" />
          </td>
          <td><i class="fa fa-calendar-check-o"></i> {{ item.title }}</td>
          <td>{{ formatDate(item.dueDate) }}</td>
          <td>{{ item.numberOfRequests }}</td>
          <td>{{ item.numberOfOrders }}</td>
          <td>{{ item.description }}</td>
        </tr>
      </tbody>
    </table>

    <!-- 创建/编辑弹窗 -->
    <div v-if="showModal" class="modal-backdrop" style="position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:1040;" @click.self="closeModal">
      <div class="modal-dialog" style="position:relative;margin:60px auto;max-width:500px;background:#fff;border-radius:4px;padding:20px;z-index:1050;">
        <div class="modal-header">
          <button type="button" class="close" style="float:right;font-size:20px;cursor:pointer" @click="closeModal">×</button>
          <h3 style="margin:0">{{ editItem ? t('EDIT_MILESTONE') : t('NEW_MILESTONE') }}</h3>
        </div>

        <div class="modal-body">
          <p v-if="modalError" class="alert alert-error">{{ modalError }}</p>
          <form class="form-horizontal" @submit.prevent="submitForm">
            <div class="control-group">
              <label class="control-label">{{ t('MILESTONE_TITLE') }}</label>
              <div class="controls">
                <input type="text" v-model="form.title" required :placeholder="t('MILESTONE_TITLE')" :readonly="editItem && !editItem.writable" />
              </div>
            </div>
            <div class="control-group">
              <label class="control-label">{{ t('MILESTONE_DUE_DATE') }}</label>
              <div class="controls">
                <input type="date" v-model="form.dueDate" :readonly="editItem && !editItem.writable" />
              </div>
            </div>
            <div class="control-group">
              <label class="control-label">{{ t('DESCRIPTION') }}</label>
              <div class="controls">
                <textarea v-model="form.description" rows="3" :readonly="editItem && !editItem.writable"></textarea>
              </div>
            </div>
          </form>
        </div>

        <div class="modal-footer">
          <template v-if="!editItem || editItem.writable">
            <button class="btn btn-default" @click="closeModal">{{ t('CANCEL') }}</button>
            <button class="btn btn-primary" :disabled="saving" @click="submitForm">
              {{ editItem ? t('SAVE') : t('CREATE') }}
            </button>
          </template>
          <button v-else class="btn btn-default" @click="closeModal">{{ t('CLOSE') }}</button>
        </div>
      </div>
    </div>
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

const showModal  = ref(false)
const editItem   = ref(null)
const saving     = ref(false)
const modalError = ref('')
const form = ref({ title: '', dueDate: '', description: '' })

function formatDate(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleDateString()
}

async function load() {
  loading.value = true
  error.value   = ''
  try {
    const data = await api.get(`/workspaces/${workspaceId.value}/changes/milestones`)
    items.value = Array.isArray(data) ? data : []
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => workspaceId.value, load)

function openCreate() {
  editItem.value = null
  form.value = { title: '', dueDate: '', description: '' }
  modalError.value = ''
  showModal.value  = true
}
function openEdit(item) {
  editItem.value = item
  form.value = {
    title: item.title || '',
    dueDate: item.dueDate ? new Date(item.dueDate).toISOString().slice(0, 10) : '',
    description: item.description || ''
  }
  modalError.value = ''
  showModal.value  = true
}
function closeModal() { showModal.value = false }

async function submitForm() {
  saving.value     = true
  modalError.value = ''
  try {
    const body = {
      title:       form.value.title,
      dueDate:     form.value.dueDate ? new Date(form.value.dueDate).getTime() : null,
      description: form.value.description || null
    }
    if (editItem.value) {
      await api.put(`/workspaces/${workspaceId.value}/changes/milestones/${editItem.value.id}`, body)
    } else {
      await api.post(`/workspaces/${workspaceId.value}/changes/milestones`, body)
    }
    closeModal()
    await load()
  } catch (e) {
    modalError.value = e.message || String(e)
  } finally {
    saving.value = false
  }
}

async function deleteSelected() {
  if (!window.confirm(t('CONFIRM_DELETE_MILESTONE'))) return
  error.value = ''
  try {
    await Promise.all(
      selected.value.map(id =>
        api.del(`/workspaces/${workspaceId.value}/changes/milestones/${id}`)
      )
    )
    selected.value = []
    await load()
  } catch (e) {
    error.value = e.message || String(e)
  }
}
</script>
