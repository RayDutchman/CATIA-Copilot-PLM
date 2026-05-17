<template>
  <!--
    CoWorkers 下拉菜单组件（非 admin 才渲染，由 AppHeader.vue v-if="!isAdmin" 控制）
    下拉状态由父组件 AppHeader 统一管理（openKey/toggle），
    以便点击其他下拉时能关闭本组件。
  -->
  <li
    class="HeaderMenu-item dropdown"
    id="coworkers_access_module"
    :class="{ open: openKey === 'coworkers' }"
    @click.stop="emit('toggle', 'coworkers')"
  >
    <a
      class="dropdown-toggle"
      id="coworkers_access_module_toggler"
      href="#"
      :title="t('COWORKERS')"
    >
      <i class="fa fa-users"></i>
      {{ t('COWORKERS') }}
      <span class="caret"></span>
    </a>
    <ul v-show="openKey === 'coworkers'" class="dropdown-menu" id="coworkers_access_module_entries">
      <!-- 加载中 -->
      <li v-if="loading">
        <i>&nbsp;<span class="fa fa-spinner fa-spin"></span></i>
      </li>
      <!-- 无协作者 -->
      <template v-else-if="coworkers.length === 0">
        <li><i>&nbsp;{{ t('NO_COWORKER') }}</i></li>
        <li>
          <a :href="appStore.contextPath + 'workspace-management/index.html'">
            <i class="fa fa-cog"></i> {{ t('WORKSPACES_ADMINISTRATION') }}
          </a>
        </li>
      </template>
      <!-- 协作者列表 -->
      <li v-for="user in coworkers" :key="user.login">
        <a>
          <i class="fa fa-user" :title="t('OFFLINE')"></i>
          <span>{{ user.login }}</span>
          <i
            class="fa fa-envelope corworker-action"
            title="Mail"
            @click.prevent.stop="sendMail(user)"
          ></i>
          <!-- 视频/聊天：结构保留，等 WebSocket 模块迁移后激活 -->
          <i class="fa fa-comments corworker-action" title="Chat" style="opacity:0.4;cursor:default"></i>
          <i class="fa fa-video-camera corworker-action" title="Video" style="opacity:0.4;cursor:default"></i>
        </a>
      </li>
    </ul>
  </li>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '../composables/useApi.js'
import { useAppStore } from '../store/app.js'
import { useAuthStore } from '../store/auth.js'

const props = defineProps({
  // 父组件当前打开的下拉 key（用于判断本组件是否展开）
  openKey: { type: String, default: null },
})
const emit = defineEmits(['toggle'])

const { t }    = useI18n()
const { get }  = useApi()
const appStore  = useAppStore()
const authStore = useAuthStore()

const coworkers = ref([])
const loading   = ref(true)

onMounted(async () => {
  try {
    const users = await get('/workspaces/reachable-users')
    const myLogin = authStore.login
    coworkers.value = (Array.isArray(users) ? users : []).filter(u => u.login !== myLogin)
  } catch (_) {
    coworkers.value = []
  } finally {
    loading.value = false
  }
})

function sendMail(user) {
  const subject = encodeURIComponent(appStore.currentWorkspace || '')
  window.location.href = `mailto:${user.email || user.login}?subject=${subject}`
}
</script>
