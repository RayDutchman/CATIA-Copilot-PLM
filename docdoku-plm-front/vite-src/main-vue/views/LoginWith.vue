<template>
  <div id="login-with-wrapper">
    <h3><i class="fa fa-lock"></i>{{ t('CONNECTION') }} <small class="vue-badge">Vue</small></h3>
    <div class="notifications">
      <div v-for="(n, i) in notifications" :key="i" :class="['alert', `alert-${n.type}`]">{{ n.message }}</div>
    </div>
    <hr />
    <div class="form-zone" v-if="providers.length">
      <h4>{{ t('CHOOSE_PROVIDER') }}</h4>
      <p v-for="p in providers" :key="p.id">
        <button class="btn btn-custom oidc-provider" :data-id="p.id" @click="connect(p)">
          {{ t('LOGIN_WITH') }} {{ p.name }}
        </button>
      </p>
    </div>
    <p v-else><em>{{ t('NO_PROVIDERS', { default: 'No OIDC providers configured' }) }}</em></p>
    <p><RouterLink to="/">{{ t('LOGIN_AN_OTHER_WAY') }}</RouterLink></p>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../../vue-common/store/app.js'

const { t } = useI18n()
const appStore = useAppStore()
const notifications = ref([])
const providers = computed(() => appStore.providers || [])

function connect(provider) {
  notifications.value.push({
    type: 'info',
    message: `[Vue 版] OIDC ${provider.name} 流程暂未在 Vue 版完整实装，请使用原版 /index.html`,
  })
}
</script>

<style scoped>
.vue-badge { display: inline-block; background: #42b883; color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 3px; margin-left: 8px; vertical-align: middle; }
.alert { padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; }
.alert-info  { background: #d9edf7; color: #31708f; border: 1px solid #bce8f1; }
.alert-error { background: #f2dede; color: #a94442; border: 1px solid #ebccd1; }
</style>
