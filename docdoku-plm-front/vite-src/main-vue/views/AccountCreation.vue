<template>
  <form id="account_creation_form" @submit.prevent="onSubmit">
    <h3><i class="fa fa-lock"></i>{{ t('REGISTRATION') }} <small class="vue-badge">Vue</small></h3>
    <div class="terms-of-service well">
      <h4>{{ t('TERMS_OF_SERVICES') }}</h4>
      <em>{{ t('TERMS_OF_SERVICES_TEXT') }}</em>
    </div>
    <h4>{{ t('CREATE_ID') }}</h4>
    <div class="notifications">
      <div v-for="(n, i) in notifications" :key="i" :class="['alert', `alert-${n.type}`]">{{ n.message }}</div>
    </div>
    <div class="form-inputs">
      <p>
        <label>{{ t('USER_ID') }} :</label>
        <input v-model="form.login" type="text" maxlength="50" required />
      </p>
      <p>
        <label>{{ t('FIRSTNAME_NAME') }} :</label>
        <input v-model="form.name" type="text" maxlength="50" required />
      </p>
      <p>
        <label>{{ t('EMAIL') }} :</label>
        <input v-model="form.email" type="email" maxlength="50" required />
      </p>
      <p>
        <label>{{ t('LANGUAGE') }} :</label>
        <select v-model="form.language" required>
          <option v-for="lng in languages" :key="lng" :value="lng">{{ lng }}</option>
        </select>
      </p>
      <p>
        <label>{{ t('TIMEZONE') }} :</label>
        <select v-model="form.timeZone">
          <option v-for="tz in timeZones" :key="tz" :value="tz">{{ tz }}</option>
        </select>
      </p>
    </div>
    <div class="form-inputs">
      <p>
        <label>{{ t('PASSWORD') }} :</label>
        <input v-model="form.password" type="password" maxlength="50" required />
      </p>
      <p>
        <label>{{ t('CONFIRM_PASSWORD') }} :</label>
        <input v-model="form.confirmPassword" type="password" maxlength="50" required />
      </p>
      <p class="account-form-buttons">
        <RouterLink to="/" class="btn btn-default">{{ t('CANCEL') }}</RouterLink>
        <input type="submit" :value="t('SAVE')" class="btn btn-custom" />
      </p>
    </div>
  </form>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../../vue-common/store/app.js'

const { t } = useI18n()
const appStore = useAppStore()
const notifications = ref([])
const languages = ref(['en', 'fr', 'zh', 'ru'])
const timeZones = ref([])

const form = reactive({
  login: '', name: '', email: '',
  language: 'en', timeZone: 'CET',
  password: '', confirmPassword: '',
})

onMounted(async () => {
  delete localStorage.jwt
  try {
    const res = await fetch(appStore.apiEndPoint + '/timezones')
    if (res.ok) timeZones.value = await res.json()
  } catch (_) { /* 时区接口失败保留 CET 缺省 */ }
  try {
    const res = await fetch(appStore.apiEndPoint + '/languages')
    if (res.ok) languages.value = await res.json()
  } catch (_) { /* 语言接口失败保留四语缺省 */ }
})

async function onSubmit() {
  notifications.value = []
  if (form.password !== form.confirmPassword) {
    notifications.value.push({ type: 'error', message: t('PASSWORD_NOT_CONFIRMED') })
    return
  }
  try {
    const res = await fetch(appStore.apiEndPoint + '/accounts/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({
        login: form.login, name: form.name, email: form.email,
        language: form.language, timeZone: form.timeZone,
        newPassword: form.password,
      }),
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || 'create failed')
    }
    const account = await res.json()
    const jwt = res.headers.get('jwt')
    if (jwt) localStorage.jwt = jwt
    if (account.enabled) {
      window.location.hash = '#/menu'
    } else {
      notifications.value.push({ type: 'success', message: t('ACCOUNT_NOT_ENABLED_YET') })
    }
  } catch (err) {
    notifications.value.push({ type: 'error', message: err.message })
  }
}
</script>

<style scoped>
.vue-badge { display: inline-block; background: #42b883; color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 3px; margin-left: 8px; vertical-align: middle; }
.alert { padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; }
.alert-success { background: #dff0d8; color: #3c763d; border: 1px solid #d6e9c6; }
.alert-error   { background: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
</style>
