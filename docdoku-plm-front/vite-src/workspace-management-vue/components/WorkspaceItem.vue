<template>
  <!-- 单个工作区卡片，对应原 workspace-item.html + views/workspace-item.js -->
  <div class="well-large well home-workspace">
    <div>
      <h4>
        <i :class="administrated ? 'fa fa-graduation-cap' : 'fa fa-user'" style="margin-right:6px;"></i>
        <span>{{ workspace.id }}</span>
      </h4>
      <p v-if="workspace.description">{{ workspace.description }}</p>
    </div>

    <!-- 超级管理员：显示启用/禁用开关 -->
    <div v-if="isRootAdmin" class="controls">
      <label>{{ t('ENABLE_WORKSPACE') }}</label>
      <input
        type="checkbox"
        :checked="workspace.enabled"
        @change="toggleEnabled"
        class="workspace-enable-checkbox"
      />
    </div>

    <ul class="unstyled">
      <li>
        <router-link v-if="administrated" :to="`/workspace/${workspace.id}/users`">
          {{ t('USERS') }}
        </router-link>
        <span v-else>{{ t('USERS') }}</span>
        (<span>{{ stats.users ?? '…' }}</span>)
      </li>
      <li>
        <a v-if="!isRootAdmin" :href="`../document-management/index.html#${workspace.id}`">{{ t('DOCUMENTS') }}</a>
        <span v-else>{{ t('DOCUMENTS') }}</span>
        (<span>{{ stats.documents ?? '…' }}</span>)
      </li>
      <li>
        <a v-if="!isRootAdmin" :href="`../product-management/index.html#${workspace.id}/parts`">{{ t('PARTS') }}</a>
        <span v-else>{{ t('PARTS') }}</span>
        (<span>{{ stats.parts ?? '…' }}</span>)
      </li>
      <li>
        <a v-if="!isRootAdmin" :href="`../product-management/index.html#${workspace.id}/products`">{{ t('PRODUCTS') }}</a>
        <span v-else>{{ t('PRODUCTS') }}</span>
        (<span>{{ stats.products ?? '…' }}</span>)
      </li>
    </ul>

    <!-- 管理员操作链接 -->
    <div v-if="administrated" class="workspace-actions">
      <router-link :to="`/workspace/${workspace.id}/edit`">{{ t('EDIT') }}</router-link>
      |
      <router-link :to="`/workspace/${workspace.id}/dashboard`">{{ t('DASHBOARD') }}</router-link>
      <span v-if="isRootAdmin">
        |
        <a href="#" @click.prevent="indexWorkspace">{{ t('INDEX_WORKSPACE') }}</a>
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import { useAppStore } from '../../vue-common/store/app.js'

const props = defineProps({
  workspace:   { type: Object,  required: true },
  administrated: { type: Boolean, default: false },
  isRootAdmin: { type: Boolean, default: false }
})

const emit = defineEmits(['info', 'error'])

const { t } = useI18n()
const api      = useApi()
const appStore = useAppStore()

// 工作区统计数据
const stats = ref({ users: null, documents: null, parts: null, products: null })

onMounted(async () => {
  try {
    const data = await api.get(`/workspaces/${props.workspace.id}/stats-overview`)
    stats.value = data
  } catch (_) {
    // 统计加载失败静默降级，不影响页面显示
  }
})

/** 超级管理员：切换工作区启用状态 */
async function toggleEnabled() {
  const newState = !props.workspace.enabled
  try {
    await api.put(`/admin/workspaces/${props.workspace.id}/enabled`, { enabled: newState })
    props.workspace.enabled = newState
  } catch (err) {
    emit('error', err.message || 'Failed to toggle workspace')
  }
}

/** 超级管理员：触发工作区索引 */
async function indexWorkspace() {
  try {
    await api.put(`/admin/workspaces/${props.workspace.id}/index`, {})
    emit('info', t('WORKSPACE_INDEXING'))
  } catch (err) {
    emit('error', err.message || 'Failed to index workspace')
  }
}
</script>
