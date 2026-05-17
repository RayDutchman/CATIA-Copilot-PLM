<template>
  <!-- 创建工作区表单，对应原 workspace-creation.html + views/workspace-creation.js -->
  <div class="actions well">
    <router-link to="/" class="btn btn-default">{{ t('CANCEL') }}</router-link>
  </div>

  <div class="notifications">
    <AlertBanner v-if="error" type="error" :message="error" @close="error = null" />
  </div>

  <div class="margin">
    <h3>{{ t('CREATE_WORKSPACE_SUBTITLE') }}</h3>
    <h3>{{ t('ADMIN') }}</h3>
    <p>{{ t('CREATE_WORKSPACE_SIDE_TEXT') }}</p>

    <form id="workspace_creation_form" class="form-horizontal" @submit.prevent="onSubmit">
      <div class="control-group">
        <label class="control-label" for="workspace-id">{{ t('NAME') }}</label>
        <div class="controls">
          <input
            id="workspace-id"
            v-model="form.id"
            type="text"
            name="workspace-id"
            maxlength="50"
            size="20"
            required
          />
        </div>
      </div>

      <div class="control-group">
        <label class="control-label" for="description">{{ t('DESCRIPTION') }}</label>
        <div class="controls">
          <textarea
            id="description"
            v-model="form.description"
            :placeholder="t('DESCRIPTION')"
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
            {{ loading ? '…' : t('CREATE') }}
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import { useAuthStore } from '../../vue-common/store/auth.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'

const { t }    = useI18n()
const router   = useRouter()
const api      = useApi()
const authStore = useAuthStore()

const error   = ref(null)
const loading = ref(false)

const form = ref({
  id: '',
  description: '',
  folderLocked: false
})

async function onSubmit() {
  if (!form.value.id.trim()) return
  loading.value = true
  error.value   = null

  try {
    const workspace = await api.post('/workspaces', {
      id: form.value.id.trim(),
      description: form.value.description,
      folderLocked: form.value.folderLocked
    })

    // 将新工作区加入本地 store（对应原 App.config.workspaces 更新）
    if (workspace.enabled) {
      authStore.workspaces.administratedWorkspaces.push(workspace)
      authStore.workspaces.allWorkspaces.push(workspace)
    }
    router.push('/')
  } catch (err) {
    error.value = err.responseText || err.message || 'Failed to create workspace'
  } finally {
    loading.value = false
  }
}
</script>
