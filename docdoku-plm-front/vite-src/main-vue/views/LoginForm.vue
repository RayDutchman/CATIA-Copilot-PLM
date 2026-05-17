<template>
  <form id="login_form" @submit.prevent="onSubmit">
    <h3><i class="fa fa-lock"></i>{{ t('CONNECTION') }} <small class="vue-badge">Vue</small></h3>
    <div class="notifications">
      <div v-for="(n, i) in notifications" :key="i" :class="['alert', `alert-${n.type}`]">
        {{ n.message }}
      </div>
    </div>
    <p>
      <label for="login_form-login">{{ t('USER') }} :</label>
      <input id="login_form-login" v-model="loginInput" type="text" maxlength="50" required />
    </p>
    <p>
      <label for="login_form-password">{{ t('PASSWORD') }} :</label>
      <input id="login_form-password" v-model="passwordInput" type="password" maxlength="50" required />
    </p>
    <ul>
      <li v-if="appStore.providers && appStore.providers.length">
        <RouterLink :to="{ name: 'login-with' }">{{ t('LOGIN_WITH') }}</RouterLink>
      </li>
      <li><RouterLink :to="{ name: 'recovery' }">{{ t('RECOVERY') }}</RouterLink></li>
      <li><RouterLink :to="{ name: 'create-account' }">{{ t('REGISTRATION') }}</RouterLink></li>
    </ul>
    <p class="form_button_container">
      <input
        id="login_form-login_button"
        type="submit"
        :value="submitting ? t('CONNECTING') : t('CONNECTION')"
        :disabled="submitting"
        class="btn btn-custom" />
    </p>
  </form>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../../vue-common/store/app.js'

const { t } = useI18n()
const appStore = useAppStore()

const loginInput    = ref('')
const passwordInput = ref('')
const submitting    = ref(false)
const notifications = ref([])

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  if (params.get('logout')) notifications.value.push({ type: 'info',  message: t('DISCONNECTED') })
  if (params.get('denied')) notifications.value.push({ type: 'error', message: t('FORBIDDEN_MESSAGE') })
})

async function ensureApiEndPoint() {
  if (!appStore.apiEndPoint) {
    await appStore.resolveServerProperties('..')
  }
  return appStore.apiEndPoint
}

async function onSubmit() {
  delete localStorage.jwt
  notifications.value = []
  submitting.value = true
  try {
    const apiEndPoint = await ensureApiEndPoint()
    const res = await fetch(apiEndPoint + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ login: loginInput.value, password: passwordInput.value }),
    })
    if (!res.ok) throw new Error('login failed')

    const account = await res.json()
    const jwt = res.headers.get('jwt')
    if (jwt) localStorage.jwt = jwt
    localStorage.locale = account && account.language ? account.language : (localStorage.locale || 'en')

    const params = new URLSearchParams(window.location.search)
    const originURL = params.get('originURL')
    if (originURL) {
      window.location.href = decodeURIComponent(originURL)
    } else {
      window.location.hash = '#/menu'
    }
  } catch (err) {
    notifications.value.push({ type: 'error', message: t('FAILED_LOGIN') })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.vue-badge {
  display: inline-block;
  background: #42b883;
  color: #fff;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  margin-left: 8px;
  vertical-align: middle;
}
.alert { padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; }
.alert-info  { background: #d9edf7; color: #31708f; border: 1px solid #bce8f1; }
.alert-error { background: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
.alert-success { background: #dff0d8; color: #3c763d; border: 1px solid #d6e9c6; }
</style>
