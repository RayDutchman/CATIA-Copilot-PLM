<template>
  <!-- 设置新工作区管理员，对应原 views/workspace-admin-new.js -->
  <div class="actions well">
    <router-link :to="`/workspace/${workspaceId}/edit`" class="btn btn-default">{{ t('BACK') }}</router-link>
  </div>

  <div class="notifications">
    <AlertBanner v-if="error" type="error" :message="error" @close="error = null" />
    <AlertBanner v-if="success" type="success" :message="success" @close="success = null" />
  </div>

  <div class="margin">
    <h3>{{ t('SET_NEW_WORKSPACE_ADMIN_SUBTITLE') }}</h3>

    <form class="form-horizontal" @submit.prevent="onSubmit">
      <div class="control-group">
        <label class="control-label" for="new-admin-login">{{ t('LOGIN') }}</label>
        <div class="controls">
          <input
            id="new-admin-login"
            v-model="newAdminLogin"
            type="text"
            required
            :placeholder="t('LOGIN')"
          />
        </div>
      </div>
      <div class="actions-btn">
        <div class="controls">
          <button type="submit" class="btn btn-primary" :disabled="loading">
            {{ loading ? '…' : t('SET_NEW_ADMIN') }}
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'

const { t }   = useI18n()
const route   = useRoute()
const router  = useRouter()
const api     = useApi()

const workspaceId  = computed(() => route.params.workspaceId)
const newAdminLogin = ref('')
const error         = ref(null)
const success       = ref(null)
const loading       = ref(false)

async function onSubmit() {
  if (!newAdminLogin.value.trim()) return
  loading.value = true
  error.value   = null
  success.value = null
  try {
    await api.put(`/workspaces/${workspaceId.value}/admin`, { login: newAdminLogin.value.trim() })
    success.value = t('SAVED')
    setTimeout(() => router.push('/'), 1500)
  } catch (err) {
    error.value = err.responseText || err.message || 'Failed to set new admin'
  } finally {
    loading.value = false
  }
}
</script>
