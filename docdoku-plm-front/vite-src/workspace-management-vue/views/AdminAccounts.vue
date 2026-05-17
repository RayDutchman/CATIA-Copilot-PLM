<template>
  <!-- 超级管理员账户管理，对应原 admin-accounts.html + views/admin-accounts.js -->
  <div class="actions well">
    <router-link to="/" class="btn btn-default">{{ t('BACK') }}</router-link>
    <button class="btn btn-primary" :disabled="!selectedAccounts.length" @click="enableSelected">
      {{ t('ENABLE_ACCOUNTS') }}
    </button>
    <button class="btn btn-custom" :disabled="!selectedAccounts.length" @click="disableSelected">
      {{ t('DISABLE_ACCOUNTS') }}
    </button>
  </div>

  <div class="notifications">
    <AlertBanner v-if="error" type="error" :message="error" @close="error = null" />
  </div>

  <div class="margin">
    <h3>{{ t('ACCOUNTS') }}</h3>

    <table class="accounts-table table table-striped table-condensed">
      <thead>
        <tr>
          <th><input type="checkbox" @change="toggleAll($event)" /></th>
          <th>{{ t('LOGIN') }}</th>
          <th>{{ t('NAME') }}</th>
          <th>{{ t('EMAIL') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="account in accounts"
          :key="account.login"
          :class="account.enabled ? 'account-enabled' : ''"
        >
          <td>
            <input type="checkbox" :value="account.login" v-model="selectedAccounts" />
          </td>
          <td>{{ account.login }}</td>
          <td>{{ account.name }}</td>
          <td>{{ account.email }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'

const { t } = useI18n()
const api   = useApi()

const accounts         = ref([])
const selectedAccounts = ref([])
const error            = ref(null)

onMounted(() => loadAccounts())

async function loadAccounts() {
  try {
    accounts.value = await api.get('/admin/accounts') || []
  } catch (err) {
    error.value = err.message || 'Failed to load accounts'
  }
}

async function enableSelected() {
  try {
    await Promise.all(
      selectedAccounts.value.map(login => api.put(`/admin/accounts/${login}`, { enabled: true }))
    )
    selectedAccounts.value = []
    await loadAccounts()
  } catch (err) {
    error.value = err.message || 'Failed to enable accounts'
  }
}

async function disableSelected() {
  try {
    await Promise.all(
      selectedAccounts.value.map(login => api.put(`/admin/accounts/${login}`, { enabled: false }))
    )
    selectedAccounts.value = []
    await loadAccounts()
  } catch (err) {
    error.value = err.message || 'Failed to disable accounts'
  }
}

function toggleAll(e) {
  selectedAccounts.value = e.target.checked ? accounts.value.map(a => a.login) : []
}
</script>
