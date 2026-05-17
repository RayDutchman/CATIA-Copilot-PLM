<template>
  <form id="recovery_form" @submit.prevent="onSubmit">
    <h3><i class="fa fa-lock"></i>{{ t('RECOVER') }} <small class="vue-badge">Vue</small></h3>
    <div class="notifications">
      <div v-for="(n, i) in notifications" :key="i" :class="['alert', `alert-${n.type}`]">{{ n.message }}</div>
    </div>
    <hr />
    <div class="form-zone" v-show="!done">
      <h4>{{ t('ENTER_NEW_PASSWORD') }}</h4>
      <p>
        <label for="recover_form-password">{{ t('PASSWORD') }} :</label>
        <input id="recover_form-password" v-model="pwd" type="password" maxlength="50" required />
      </p>
      <p>
        <label for="recover_form-confirmPassword">{{ t('CONFIRM_PASSWORD') }} :</label>
        <input id="recover_form-confirmPassword" v-model="pwd2" type="password" maxlength="50" required />
      </p>
      <p class="form_button_container">
        <input type="submit" :value="t('SAVE')" class="btn btn-custom" />
      </p>
    </div>
    <p v-if="done">{{ t('RECOVER_OK') }}</p>
    <p><RouterLink to="/">{{ t('BACK') }}</RouterLink></p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../../vue-common/store/app.js'

const { t } = useI18n()
const route = useRoute()
const appStore = useAppStore()
const pwd  = ref('')
const pwd2 = ref('')
const notifications = ref([])
const done = ref(false)

async function onSubmit() {
  notifications.value = []
  if (pwd.value !== pwd2.value) {
    notifications.value.push({ type: 'error', message: t('PASSWORD_NOT_CONFIRMED') })
    return
  }
  try {
    const res = await fetch(appStore.apiEndPoint + '/auth/recover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ uuid: route.params.uuid, newPassword: pwd.value }),
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(text || 'recover failed')
    }
    done.value = true
  } catch (err) {
    notifications.value.push({ type: 'error', message: err.message || t('FAILED_LOGIN') })
  }
}
</script>

<style scoped>
.vue-badge { display: inline-block; background: #42b883; color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 3px; margin-left: 8px; vertical-align: middle; }
.alert { padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; }
.alert-error { background: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
</style>
