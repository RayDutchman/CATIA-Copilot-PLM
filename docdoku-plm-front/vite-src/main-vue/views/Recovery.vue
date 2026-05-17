<template>
  <form id="recovery_form" @submit.prevent="onSubmit">
    <h3><i class="fa fa-lock"></i>{{ t('RECOVERY') }} <small class="vue-badge">Vue</small></h3>
    <div class="notifications">
      <div v-for="(n, i) in notifications" :key="i" :class="['alert', `alert-${n.type}`]">{{ n.message }}</div>
    </div>
    <hr />
    <h4>{{ t('ENTER_ID') }}</h4>
    <p>
      <label for="recovery_form-login">{{ t('USER') }} :</label>
      <input id="recovery_form-login" v-model="loginInput" type="text" maxlength="50" :disabled="submitting" required />
    </p>
    <p class="form_button_container" v-show="!submitted">
      <input type="submit" :value="t('SEND')" class="btn btn-custom" :disabled="submitting" />
    </p>
    <p><RouterLink to="/">{{ t('BACK') }}</RouterLink></p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../../vue-common/store/app.js'

const { t } = useI18n()
const appStore = useAppStore()
const loginInput = ref('')
const notifications = ref([])
const submitting = ref(false)
const submitted = ref(false)

async function onSubmit() {
  notifications.value = []
  submitting.value = true
  delete localStorage.jwt
  try {
    const res = await fetch(appStore.apiEndPoint + '/auth/recovery', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ login: loginInput.value }),
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || 'recovery failed')
    }
    notifications.value.push({ type: 'success', message: t('RECOVERY_REQUEST_SENT') })
    submitted.value = true
  } catch (err) {
    notifications.value.push({ type: 'error', message: err.message || t('FAILED_LOGIN') })
    submitting.value = false
  }
}
</script>

<style scoped>
.vue-badge { display: inline-block; background: #42b883; color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 3px; margin-left: 8px; vertical-align: middle; }
.alert { padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; }
.alert-success { background: #dff0d8; color: #3c763d; border: 1px solid #d6e9c6; }
.alert-error   { background: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
</style>
