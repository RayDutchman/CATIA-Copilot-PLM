<template>
  <!--
    原版结构：
      .actions.well   ← 在 .margin 之外，靠左靠上（全宽）
      .notifications  ← 通知区，同样在 .margin 之外
      .margin         ← 内容区
    Vue 3 fragment 支持多根节点，与原版结构对齐
  -->

  <!-- 退出按钮：始终在最顶部（对应原版 .actions.well 在 .margin 之外） -->
  <div class="actions well">
    <button class="btn btn-default" @click="authStore.logout()">{{ t('LOGOUT') }}</button>
  </div>

  <!-- 通知区（对应原版 .notifications div） -->
  <div class="notifications">
    <AlertBanner
      v-for="(alert, i) in alerts"
      :key="i"
      :type="alert.type"
      :title="alert.title"
      :message="alert.message"
      @dismiss="alerts.splice(i, 1)"
    />
  </div>

  <!-- 主内容区（对应原版 .margin 内的内容） -->
  <div class="margin">
    <!-- 认证步骤：未通过认证时先要求用户验证身份 -->
    <template v-if="!authenticated">
      <h3>{{ t('AUTH_REQUIRED') }}</h3>

      <!-- OIDC provider 认证 -->
      <template v-if="provider">
        <p>{{ t('AUTH_REQUIRED_PROVIDER_TEXT') }}</p>
        <button class="btn btn-primary" @click="authWithProvider">
          {{ t('LOGIN_WITH') }} {{ provider.name }}
        </button>
      </template>

      <!-- 密码认证 -->
      <template v-else>
        <p>{{ t('AUTH_REQUIRED_PASSWORD_TEXT') }}</p>
        <div class="control-group">
          <div class="controls">
            <input v-model="password" type="password" />
          </div>
        </div>
        <div class="control-group">
          <div class="controls">
            <button class="btn btn-primary" @click="authWithPassword">{{ t('CONFIRM') }}</button>
          </div>
        </div>
      </template>
    </template>

    <!-- 账户编辑表单：通过认证后显示 -->
    <template v-else>

      <h3>{{ t('ACCOUNT_EDITION') }}</h3>

      <form id="account_edition_form" class="form-horizontal" @submit.prevent="onSubmit">
        <!-- 登录名（只读） -->
        <div class="control-group">
          <label class="control-label">{{ t('LOGIN') }}</label>
          <div class="controls">{{ account?.login }}</div>
        </div>

        <!-- 姓名 -->
        <div class="control-group">
          <label class="control-label" for="account-name">{{ t('ACCOUNT_NAME') }}</label>
          <div class="controls">
            <input id="account-name" v-model="form.name" type="text" maxlength="50" size="20" required />
          </div>
        </div>

        <!-- 邮箱 -->
        <div class="control-group">
          <label class="control-label" for="account-email">{{ t('EMAIL') }}</label>
          <div class="controls">
            <input id="account-email" v-model="form.email" type="email" required />
          </div>
        </div>

        <!-- 语言 -->
        <div class="control-group">
          <label class="control-label" for="account-language">{{ t('LANG') }}</label>
          <div class="controls">
            <select id="account-language" v-model="form.language" required>
              <option v-for="lang in languages" :key="lang" :value="lang">
                {{ t('LANGUAGES.' + lang, lang) }}
              </option>
            </select>
          </div>
        </div>

        <!-- 时区 -->
        <div class="control-group">
          <label class="control-label" for="account-timezone">{{ t('TIMEZONE') }}</label>
          <div class="controls">
            <select id="account-timezone" v-model="form.timeZone">
              <option v-for="tz in timeZones" :key="tz" :value="tz">{{ tz }}</option>
            </select>
          </div>
        </div>

        <!-- 修改密码（无 provider 时显示） -->
        <template v-if="!provider">
          <div class="control-group">
            <label class="control-label">
              <a class="toggle-password-update" @click.prevent="enablePasswordUpdate = !enablePasswordUpdate" style="cursor:pointer">
                {{ t('CHANGE_PASSWORD') }}
              </a>
            </label>
          </div>

          <div v-if="enablePasswordUpdate" class="password-update">
            <div class="control-group">
              <label class="control-label" for="account-password">{{ t('NEW_PASSWORD') }}</label>
              <div class="controls">
                <input v-model="newPassword" type="password" id="account-password" :required="enablePasswordUpdate" />
              </div>
            </div>
            <div class="control-group">
              <label class="control-label" for="account-confirm-password">{{ t('CONFIRM_PASSWORD') }}</label>
              <div class="controls">
                <input v-model="confirmPassword" type="password" id="account-confirm-password" :required="enablePasswordUpdate" />
              </div>
            </div>
          </div>
        </template>

        <div class="actions-btn">
          <div class="controls">
            <input type="submit" :value="t('SAVE')" class="btn btn-primary" />
          </div>
        </div>
      </form>
    </template>
  </div>
</template>
<!-- 注：Vue 3 fragment 多根节点：.actions.well / .notifications / .margin 并列渲染 -->

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../vue-common/store/auth.js'
import { useAppStore }  from '../../vue-common/store/app.js'
import { useApi }       from '../../vue-common/composables/useApi.js'
import AlertBanner      from '../../vue-common/components/AlertBanner.vue'
import oidc             from '../../common-objects/oidc.js'
import jwtDecode        from 'jwt-decode'

const { t }     = useI18n()
const authStore = useAuthStore()
const appStore  = useAppStore()
const { get, put, post } = useApi()

// ── 状态 ──
const account           = ref(authStore.account)
const authenticated     = ref(false)       // 通过认证前显示认证步骤
const provider          = ref(null)        // OIDC provider（若有）
const password          = ref('')          // 密码认证输入
const enablePasswordUpdate = ref(false)
const newPassword       = ref('')
const confirmPassword   = ref('')
const languages         = ref([])
const timeZones         = ref([])
const alerts            = ref([])

// 表单数据（从 account 初始化）
const form = reactive({
  name:     account.value?.name     || '',
  email:    account.value?.email    || '',
  language: account.value?.language || 'en',
  timeZone: account.value?.timeZone || '',
})

// ── 初始化 ──
onMounted(async () => {
  // 加载语言和时区列表
  try {
    languages.value = await get('/languages')
    timeZones.value = await get('/timezones')
  } catch (e) {
    console.warn('Failed to load languages/timezones', e)
  }

  // 判断是否需要认证：账户若绑定了 provider，加载 provider 信息
  if (account.value?.providerId) {
    try {
      provider.value = await get('/auth/providers/' + account.value.providerId)
    } catch (_) {
      provider.value = null
    }
  } else {
    provider.value = null
  }
  // 无论如何，若已有 jwt 则视为已认证
  authenticated.value = !!localStorage.jwt
})

// ── 认证方法 ──
async function authWithProvider() {
  try {
    const user = await oidc.login(provider.value)
    const decoded = jwtDecode(user.id_token)
    await post('/auth/oauth', {
      idToken:    user.id_token,
      nonce:      decoded.nonce,
      providerId: provider.value.id,
    })
    authenticated.value = true
    pushAlert('success', '', t('ACCOUNT_UPDATED'))
  } catch (_) {
    pushAlert('error', '', t('AUTHENTICATION_FAILED'))
  }
}

async function authWithPassword() {
  try {
    const res = await post('/auth/login', {
      login:    account.value.login,
      password: password.value,
    })
    if (res?.jwt) localStorage.jwt = res.jwt
    authenticated.value = true
  } catch (_) {
    pushAlert('error', '', t('AUTHENTICATION_FAILED'))
  }
}

// ── 表单提交 ──
async function onSubmit() {
  // 密码校验
  if (enablePasswordUpdate.value) {
    if (newPassword.value !== confirmPassword.value) {
      pushAlert('error', '', t('PASSWORD_NOT_CONFIRMED'))
      return
    }
  }

  const payload = {
    name:     form.name,
    email:    form.email,
    language: form.language,
    timeZone: form.timeZone,
  }
  if (password.value)                          payload.password    = password.value
  if (enablePasswordUpdate.value && newPassword.value) payload.newPassword = newPassword.value

  try {
    const updated = await put('/accounts/me', payload)
    authStore.account = updated
    account.value     = updated

    if (enablePasswordUpdate.value && newPassword.value) {
      password.value = newPassword.value
    }

    // 语言变更：同步 localStorage 后 reload
    if (localStorage.locale !== updated.language) {
      localStorage.locale = updated.language
      window.location.reload()
    } else {
      pushAlert('success', t('ACCOUNT_UPDATED'), '')
    }
  } catch (err) {
    pushAlert('error', '', err.message || t('ERROR'))
  }
}

// ── 工具 ──
function pushAlert(type, title, message) {
  alerts.value.push({ type, title, message })
}
</script>
