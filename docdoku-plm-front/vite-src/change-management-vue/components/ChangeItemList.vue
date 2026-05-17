<template>
  <!-- 变更项目列表（issues / requests / orders 通用）
       对应原 change_issue_content.html + change_issue_list.js + change_issue_list_item.html -->
  <div class="actions well">
    <button class="btn btn-primary" @click="openCreate">
      <i class="fa fa-plus"></i>
    </button>
    <button class="btn btn-danger" :disabled="selected.length === 0" @click="deleteSelected">
      <i class="fa fa-times"></i>
    </button>
  </div>

  <AlertBanner :message="error" type="error" v-if="error" />

  <table class="table table-striped table-condensed">
    <thead>
      <tr>
        <th><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
        <th>{{ t('NAME') }}</th>
        <th>{{ t('CHANGE_ITEM_ASSIGNEE') }}</th>
        <th>{{ t('CHANGE_ITEM_PRIORITY') }}</th>
        <th>{{ t('CHANGE_ITEM_CATEGORY') }}</th>
        <th>{{ t('AUTHOR') }}</th>
        <th>{{ t('CREATION_DATE') }}</th>
        <th>{{ t('ACL') }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-if="loading"><td colspan="8">…</td></tr>
      <tr v-else-if="items.length === 0"><td colspan="8">{{ t('NO_DATA') }}</td></tr>
      <tr
        v-for="item in items"
        :key="item.id"
        @click="openEdit(item)"
        style="cursor:pointer"
      >
        <td @click.stop>
          <input type="checkbox" :value="item.id" v-model="selected" />
        </td>
        <td>
          <i :class="iconClass"></i> {{ item.name }}
        </td>
        <td>{{ item.assigneeName }}</td>
        <td>{{ item.priority }}</td>
        <td>{{ item.category }}</td>
        <td>{{ item.authorName }}</td>
        <td>{{ formatDate(item.creationDate) }}</td>
        <td>
          <i v-if="item.acl && isReadOnly(item)" class="fa fa-key" style="color:#aaa" :title="t('READ_ONLY')"></i>
          <i v-else-if="item.acl && isFullAccess(item)" class="fa fa-key" style="color:green" :title="t('FULL_ACCESS')"></i>
        </td>
      </tr>
    </tbody>
  </table>

  <!-- 创建 / 编辑弹窗 -->
  <div v-if="showModal" class="modal-backdrop" style="position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:1040;" @click.self="closeModal">
    <div class="modal-dialog" style="position:relative;margin:60px auto;max-width:600px;background:#fff;border-radius:4px;padding:20px;z-index:1050;">
      <div class="modal-header">
        <i :class="iconClass"></i>
        <i v-if="editItem" class="fa fa-pencil" style="margin-left:4px"></i>
        <button type="button" class="close" style="float:right;font-size:20px;cursor:pointer" @click="closeModal">×</button>
        <h3 style="margin:0 0 0 8px;display:inline">
          {{ editItem ? t(editTitle) : t(createTitle) }}
          <span v-if="editItem"> : {{ editItem.name }}</span>
        </h3>
      </div>

      <div class="modal-body">
        <AlertBanner :message="modalError" type="error" v-if="modalError" />

        <ul class="nav nav-tabs" style="margin-bottom:10px">
          <li :class="{ active: activeTab === 'main' }">
            <a href="#" @click.prevent="activeTab = 'main'">{{ t('GENERAL') }}</a>
          </li>
        </ul>

        <form class="form-horizontal" @submit.prevent="submitForm">
          <!-- 名称 -->
          <div class="control-group">
            <label class="control-label">{{ t('NAME') }}</label>
            <div class="controls">
              <span v-if="editItem">{{ editItem.name }}</span>
              <input v-else type="text" v-model="form.name" required :placeholder="t('NAME')" />
            </div>
          </div>

          <!-- 发起人（仅 issues） -->
          <div v-if="type === 'issues'" class="control-group">
            <label class="control-label">{{ t('INITIATOR') }}</label>
            <div class="controls">
              <input type="text" v-model="form.initiator" :placeholder="t('INITIATOR')" :disabled="editItem && !editItem.writable" />
            </div>
          </div>

          <!-- 优先级 -->
          <div class="control-group">
            <label class="control-label">{{ t('CHANGE_ITEM_PRIORITY') }}</label>
            <div class="controls">
              <select v-model="form.priority" :disabled="editItem && !editItem.writable">
                <option value="">—</option>
                <option v-for="p in priorities" :key="p" :value="p">{{ t('CHANGE_ITEM_PRIORITY_' + p) }}</option>
              </select>
            </div>
          </div>

          <!-- 描述 -->
          <div class="control-group">
            <label class="control-label">{{ t('DESCRIPTION') }}</label>
            <div class="controls">
              <textarea v-model="form.description" rows="3" :placeholder="t('DESCRIPTION')" :readonly="editItem && !editItem.writable"></textarea>
            </div>
          </div>

          <!-- 负责人 -->
          <div class="control-group">
            <label class="control-label">{{ t('CHANGE_ITEM_ASSIGNEE') }}</label>
            <div class="controls">
              <select v-model="form.assigneeLogin" :disabled="editItem && !editItem.writable">
                <option value="">—</option>
                <option v-for="u in workspaceUsers" :key="u.login" :value="u.login">{{ u.name }} ({{ u.login }})</option>
              </select>
            </div>
          </div>

          <!-- 类别 -->
          <div class="control-group">
            <label class="control-label">{{ t('CHANGE_ITEM_CATEGORY') }}</label>
            <div class="controls">
              <select v-model="form.category" :disabled="editItem && !editItem.writable">
                <option value="">—</option>
                <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
              </select>
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
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'

const props = defineProps({
  /** 'issues' | 'requests' | 'orders' */
  type: { type: String, required: true }
})

const { t } = useI18n()
const route = useRoute()
const api   = useApi()

// ── 配置（根据 type 派生）
const iconMap = { issues: 'fa fa-bug', requests: 'fa fa-ticket', orders: 'fa fa-archive' }
const iconClass = computed(() => iconMap[props.type] || 'fa fa-circle')

const createTitleMap = { issues: 'NEW_ISSUE', requests: 'NEW_REQUEST', orders: 'NEW_ORDER' }
const editTitleMap   = { issues: 'EDIT_ISSUE', requests: 'EDIT_REQUEST', orders: 'EDIT_ORDER' }
const confirmDeleteMap = {
  issues: 'CONFIRM_DELETE_ISSUE',
  requests: 'CONFIRM_DELETE_REQUEST',
  orders: 'CONFIRM_DELETE_ORDER'
}
const createTitle = computed(() => createTitleMap[props.type])
const editTitle   = computed(() => editTitleMap[props.type])

const priorities = ['LOW', 'MEDIUM', 'HIGH', 'EMERGENCY']
const categories = ['ADAPTIVE', 'CORRECTIVE', 'PERFECTIVE', 'PREVENTIVE', 'OTHER']

// ── 数据
const workspaceId   = computed(() => route.params.workspaceId)
const items         = ref([])
const workspaceUsers = ref([])
const loading       = ref(false)
const error         = ref('')

// ── 选择
const selected  = ref([])
const allChecked = computed(() =>
  items.value.length > 0 && selected.value.length === items.value.length
)
function toggleAll(e) {
  selected.value = e.target.checked ? items.value.map(i => i.id) : []
}

// ── 弹窗
const showModal  = ref(false)
const activeTab  = ref('main')
const editItem   = ref(null)
const saving     = ref(false)
const modalError = ref('')
const form = ref({
  name: '', initiator: '', priority: '', description: '', assigneeLogin: '', category: ''
})

// ── 工具
function formatDate(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleString()
}
function isReadOnly(item) {
  const acl = item.acl
  if (!acl) return false
  // DocDoku ACL 结构：{ userEntries:[{login,permission}], ... }
  return acl.__permission === 'READ_ONLY'
}
function isFullAccess(item) {
  if (!item.acl) return false
  return item.acl.__permission === 'FULL_ACCESS'
}

// ── 数据加载
async function load() {
  loading.value = true
  error.value   = ''
  try {
    const data = await api.get(`/workspaces/${workspaceId.value}/changes/${props.type}`)
    items.value = Array.isArray(data) ? data : []
  } catch (e) {
    error.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  try {
    const data = await api.get(`/workspaces/${workspaceId.value}/users`)
    workspaceUsers.value = Array.isArray(data) ? data : []
  } catch (_) {
    workspaceUsers.value = []
  }
}

onMounted(() => { load(); loadUsers() })
watch(() => [workspaceId.value, props.type], () => { load(); loadUsers() })

// ── 弹窗操作
function openCreate() {
  editItem.value = null
  form.value = { name: '', initiator: '', priority: '', description: '', assigneeLogin: '', category: '' }
  modalError.value = ''
  activeTab.value  = 'main'
  showModal.value  = true
}
function openEdit(item) {
  editItem.value = item
  form.value = {
    name:         item.name || '',
    initiator:    item.initiator || '',
    priority:     item.priority || '',
    description:  item.description || '',
    assigneeLogin: item.assignee?.login || '',
    category:     item.category || ''
  }
  modalError.value = ''
  activeTab.value  = 'main'
  showModal.value  = true
}
function closeModal() {
  showModal.value = false
}

// ── 提交（创建或更新）
async function submitForm() {
  saving.value     = true
  modalError.value = ''
  try {
    const body = {
      name:         form.value.name,
      priority:     form.value.priority || null,
      description:  form.value.description || null,
      category:     form.value.category || null,
      assigneeLogin: form.value.assigneeLogin || null
    }
    if (props.type === 'issues') {
      body.initiator = form.value.initiator || null
    }

    if (editItem.value) {
      await api.put(
        `/workspaces/${workspaceId.value}/changes/${props.type}/${editItem.value.id}`,
        body
      )
    } else {
      await api.post(
        `/workspaces/${workspaceId.value}/changes/${props.type}`,
        body
      )
    }
    closeModal()
    await load()
  } catch (e) {
    modalError.value = e.message || String(e)
  } finally {
    saving.value = false
  }
}

// ── 删除
async function deleteSelected() {
  if (!window.confirm(t(confirmDeleteMap.value))) return
  error.value = ''
  try {
    await Promise.all(
      selected.value.map(id =>
        api.del(`/workspaces/${workspaceId.value}/changes/${props.type}/${id}`)
      )
    )
    selected.value = []
    await load()
  } catch (e) {
    error.value = e.message || String(e)
  }
}
</script>
