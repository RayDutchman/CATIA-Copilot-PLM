<template>
  <!-- 编辑工作区，对应原 workspace-edit.html + views/workspace-edit.js -->

  <!-- 正在删除中提示 -->
  <div v-if="deleting" class="margin">
    <h4>{{ t('WORKSPACE_DELETING_TITLE') }}</h4>
    <p>{{ t('WORKSPACE_DELETING_TEXT') }}</p>
  </div>

  <template v-else>
    <div class="actions well">
      <button class="btn btn-default" @click="$router.push('/')">{{ t('CANCEL') }}</button>
      <button class="btn btn-custom" @click="deleteWorkspace">{{ t('DELETE') }}</button>
      <button class="btn btn-primary pull-right" @click="goSetNewAdmin">{{ t('SET_NEW_ADMIN') }}</button>
    </div>

    <div class="notifications">
      <AlertBanner v-if="error" type="error" :message="error" @close="error = null" />
      <AlertBanner v-if="saved" type="success" :message="t('SAVED')" @close="saved = false" />
    </div>

    <div class="margin">
      <h3>{{ t('EDIT_WORKSPACE_SUBTITLE') }}</h3>

      <form id="workspace_update_form" class="form-horizontal" @submit.prevent="onSubmit">
        <div class="control-group">
          <label class="control-label">{{ t('WORKSPACE') }}</label>
          <div class="controls">{{ workspaceId }}</div>
        </div>

        <div class="control-group">
          <label class="control-label" for="description">{{ t('DESCRIPTION') }}</label>
          <div class="controls">
            <textarea
              id="description"
              v-model="form.description"
              placeholder="Description"
              rows="3"
            ></textarea>
          </div>
        </div>

        <div class="control-group" id="inputPartNumberWrapper">
          <label class="control-label">{{ t('OPTIONS') }}</label>
          <div class="controls">
            <label class="checkbox" for="folderLocked">
              <input
                id="folderLocked"
                v-model="form.folderLocked"
                type="checkbox"
                name="folderLocked"
              />
              {{ t('FOLDER_LOCKED') }}
            </label>
          </div>
        </div>

        <div class="actions-btn">
          <div class="controls">
            <button type="submit" class="btn btn-primary" :disabled="loading">
              {{ loading ? '…' : t('SAVE') }}
            </button>
          </div>
        </div>
      </form>
    </div>
  </template>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import { useAuthStore } from '../../vue-common/store/auth.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'

const { t }     = useI18n()
const route     = useRoute()
const router    = useRouter()
const api       = useApi()
const authStore = useAuthStore()

const workspaceId = computed(() => route.params.workspaceId)

// 从 store 中找到当前工作区数据
const workspace = computed(() =>
  authStore.workspaces.administratedWorkspaces.find(w => w.id === workspaceId.value)
)

const error   = ref(null)
const saved   = ref(false)
const loading = ref(false)
const deleting = ref(false)

const form = ref({
  description: '',
  folderLocked: false
})

onMounted(() => {
  if (workspace.value) {
    form.value.description  = workspace.value.description || ''
    form.value.folderLocked = !!workspace.value.folderLocked
  }
})

async function onSubmit() {
  loading.value = true
  error.value   = null
  saved.value   = false

  try {
    await api.put(`/workspaces/${workspaceId.value}`, {
      id: workspaceId.value,
      description: form.value.description,
      folderLocked: form.value.folderLocked
    })
    // 更新 store 中的本地缓存
    if (workspace.value) {
      workspace.value.description  = form.value.description
      workspace.value.folderLocked = form.value.folderLocked
    }
    saved.value = true
  } catch (err) {
    error.value = err.responseText || err.message || 'Failed to save workspace'
  } finally {
    loading.value = false
  }
}

async function deleteWorkspace() {
  if (!confirm(t('DELETE_WORKSPACE_QUESTION'))) return

  try {
    await api.del(`/workspaces/${workspaceId.value}`)
    // 从 store 中移除
    const idx = authStore.workspaces.administratedWorkspaces.findIndex(w => w.id === workspaceId.value)
    if (idx !== -1) authStore.workspaces.administratedWorkspaces.splice(idx, 1)
    deleting.value = true
  } catch (err) {
    error.value = err.responseText || err.message || 'Failed to delete workspace'
  }
}

function goSetNewAdmin() {
  router.push(`/workspace/${workspaceId.value}/admin/new`)
}
</script>
