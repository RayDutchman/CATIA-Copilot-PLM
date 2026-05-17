<template>
  <div>
    <!-- 标题栏 + 过滤器 -->
    <div class="well well-small" style="display:flex; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:wrap">
      <strong><i class="fa fa-tasks"></i> {{ $t('TASKS') }}</strong>
      <div class="btn-group">
        <button
          class="btn btn-small"
          :class="{ 'btn-primary': !filterStatus }"
          @click="setFilter(null)"
        >{{ $t('ALL_TASKS') }}</button>
        <button
          class="btn btn-small"
          :class="{ 'btn-primary': filterStatus === 'in_progress' }"
          @click="setFilter('in_progress')"
        >{{ $t('IN_PROGRESS') }}</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">
      <button class="close" @click="error = ''">×</button>
      {{ error }}
    </div>

    <DocumentList
      :documents="documents"
      :loading="loading"
      :showActions="false"
      @checkout="doCheckout"
      @undo-checkout="doUndoCheckout"
      @checkin="doCheckin"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../vue-common/store/auth.js';
import { useApi } from '../../vue-common/composables/useApi.js';
import DocumentList from '../components/DocumentList.vue';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { get, post } = useApi();

const workspaceId = computed(() => route.params.workspaceId || '');
const filterStatus = ref(route.params.filter || null);

const documents = ref([]);
const loading = ref(false);
const error = ref('');

async function loadTasks() {
    loading.value = true;
    try {
        const login = authStore.account?.login || '';
        let url = `/workspaces/${workspaceId.value}/tasks/${login}/documents/`;
        if (filterStatus.value) url += `?filter=${filterStatus.value}`;
        const data = await get(url);
        documents.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '加载任务文档失败';
    } finally {
        loading.value = false;
    }
}

function setFilter(f) {
    filterStatus.value = f;
    const ws = workspaceId.value;
    router.push(f ? `/${ws}/tasks/${f}` : `/${ws}/tasks`);
}

async function doCheckout(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/checkout`, null);
        await loadTasks();
    } catch (e) { error.value = e.message; }
}
async function doUndoCheckout(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/undocheckout`, null);
        await loadTasks();
    } catch (e) { error.value = e.message; }
}
async function doCheckin(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/checkin`, null);
        await loadTasks();
    } catch (e) { error.value = e.message; }
}

watch([workspaceId, filterStatus], ([ws]) => {
    if (ws) loadTasks();
}, { immediate: true });
</script>
