<template>
  <!-- 工作区管理首页：对应原 workspace-management-home.html + views/workspace-management-home.js -->
  <div class="notifications">
    <AlertBanner v-if="alert" :type="alert.type" :message="alert.message" @close="alert = null" />
  </div>

  <div class="margin">
    <h3>{{ t('WORKSPACES_ADMINISTRATION') }}</h3>
    <p><i class="fa fa-graduation-cap"></i> <em>{{ t('WORKSPACES_ADMINISTRATION_TEXT') }}</em></p>

    <!-- 管理员工作区列表 -->
    <div class="home-workspace-list-container administrated-workspaces">
      <WorkspaceItem
        v-for="ws in administratedWorkspaces"
        :key="ws.id"
        :workspace="ws"
        :administrated="true"
        :is-root-admin="isAdmin"
        @info="onInfo"
        @error="onError"
      />
    </div>

    <!-- 非管理员工作区列表 -->
    <div class="home-workspace-list-container non-administrated-workspaces">
      <WorkspaceItem
        v-for="ws in nonAdministratedWorkspaces"
        :key="ws.id"
        :workspace="ws"
        :administrated="false"
        :is-root-admin="false"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../vue-common/store/auth.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'
import WorkspaceItem from '../components/WorkspaceItem.vue'

const { t } = useI18n()
const authStore = useAuthStore()

const alert = ref(null)

const administratedWorkspaces    = computed(() => authStore.workspaces.administratedWorkspaces)
const nonAdministratedWorkspaces = computed(() => authStore.workspaces.nonAdministratedWorkspaces)
const isAdmin                    = computed(() => authStore.isAdmin)

function onInfo(message) {
  alert.value = { type: 'info', message }
}

function onError(message) {
  alert.value = { type: 'error', message }
}
</script>
