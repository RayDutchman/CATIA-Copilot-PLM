<template>
  <div>
    <div class="well well-small" style="margin-bottom:8px">
      <strong><i class="fa fa-lock"></i> {{ $t('CHECKOUTS') }}</strong>
    </div>

    <div v-if="error" class="alert alert-error">
      <button class="close" @click="error = ''">×</button>
      {{ error }}
    </div>

    <DocumentList
      :documents="documents"
      :loading="loading"
      :showActions="false"
      @undo-checkout="doUndoCheckout"
      @checkin="doCheckin"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useApi } from '../../vue-common/composables/useApi.js';
import DocumentList from '../components/DocumentList.vue';

const route = useRoute();
const { get, post } = useApi();

const workspaceId = computed(() => route.params.workspaceId || '');
const documents = ref([]);
const loading = ref(false);
const error = ref('');

async function loadCheckedOut() {
    loading.value = true;
    try {
        const data = await get(`/workspaces/${workspaceId.value}/documents/checkedout`);
        documents.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '加载已签出文档失败';
    } finally {
        loading.value = false;
    }
}

async function doUndoCheckout(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/undocheckout`, null);
        await loadCheckedOut();
    } catch (e) { error.value = e.message; }
}

async function doCheckin(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/checkin`, null);
        await loadCheckedOut();
    } catch (e) { error.value = e.message; }
}

watch(workspaceId, (ws) => { if (ws) loadCheckedOut(); }, { immediate: true });
</script>
