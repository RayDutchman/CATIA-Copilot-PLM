<template>
  <div>
    <!-- 搜索表单 -->
    <div class="well" style="margin-bottom:12px">
      <h5 style="margin:0 0 8px"><i class="fa fa-search"></i> {{ $t('QUICK_SEARCH') }}</h5>
      <form @submit.prevent="doSearch" class="form-inline">
        <input
          v-model="query"
          class="input-large"
          :placeholder="$t('SEARCH') + '...'"
          style="margin-right:8px"
        />
        <button type="submit" class="btn btn-primary">
          <i class="fa fa-search"></i> {{ $t('SEARCH') }}
        </button>
      </form>
      <!-- 高级搜索展开 -->
      <a href="#" style="font-size:11px; margin-top:4px; display:inline-block" @click.prevent="showAdvanced = !showAdvanced">
        {{ $t('ADVANCED_SEARCH') }} <i :class="showAdvanced ? 'fa fa-chevron-up' : 'fa fa-chevron-down'"></i>
      </a>
      <div v-if="showAdvanced" style="margin-top:8px; padding:8px; border:1px solid #ddd; border-radius:4px">
        <div class="row-fluid">
          <div class="span6">
            <label>{{ $t('DOCUMENT_S_REFERENCE') }}</label>
            <input v-model="advanced.docMId" class="input-block-level" :placeholder="$t('DOCUMENT_S_REFERENCE')" />
          </div>
          <div class="span6">
            <label>{{ $t('DOCUMENT_S_TITLE') }}</label>
            <input v-model="advanced.title" class="input-block-level" :placeholder="$t('DOCUMENT_S_TITLE')" />
          </div>
        </div>
        <div class="row-fluid" style="margin-top:4px">
          <div class="span6">
            <label>{{ $t('VERSION') }}</label>
            <input v-model="advanced.version" class="input-block-level" :placeholder="$t('VERSION')" />
          </div>
          <div class="span6">
            <label>{{ $t('AUTHOR') }}</label>
            <input v-model="advanced.author" class="input-block-level" :placeholder="$t('AUTHOR')" />
          </div>
        </div>
        <button class="btn btn-small btn-primary" style="margin-top:8px" @click="doAdvancedSearch">
          <i class="fa fa-search"></i> {{ $t('SEARCH') }}
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">
      <button class="close" @click="error = ''">×</button>
      {{ error }}
    </div>

    <!-- 搜索结果 -->
    <div v-if="searched">
      <p class="muted" style="font-size:12px">
        {{ $t('RESULTS') }}: {{ documents.length }}
      </p>
      <DocumentList
        :documents="documents"
        :loading="loading"
        :showActions="false"
        @checkout="doCheckout"
        @undo-checkout="doUndoCheckout"
        @checkin="doCheckin"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useApi } from '../../vue-common/composables/useApi.js';
import DocumentList from '../components/DocumentList.vue';

const route = useRoute();
const router = useRouter();
const { get, post } = useApi();

const workspaceId = computed(() => route.params.workspaceId || '');

const query = ref('');
const showAdvanced = ref(false);
const advanced = ref({ docMId: '', title: '', version: '', author: '' });
const documents = ref([]);
const loading = ref(false);
const error = ref('');
const searched = ref(false);

async function doSearch() {
    if (!query.value.trim()) return;
    loading.value = true;
    error.value = '';
    searched.value = true;
    try {
        const q = encodeURIComponent(query.value.trim());
        const data = await get(`/workspaces/${workspaceId.value}/documents/search?q=${q}`);
        documents.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '搜索失败';
        documents.value = [];
    } finally {
        loading.value = false;
    }
}

async function doAdvancedSearch() {
    loading.value = true;
    error.value = '';
    searched.value = true;
    try {
        const params = new URLSearchParams();
        if (advanced.value.docMId) params.append('docMId', advanced.value.docMId);
        if (advanced.value.title) params.append('title', advanced.value.title);
        if (advanced.value.version) params.append('version', advanced.value.version);
        if (advanced.value.author) params.append('author', advanced.value.author);
        const data = await get(`/workspaces/${workspaceId.value}/documents/search?${params.toString()}`);
        documents.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '搜索失败';
        documents.value = [];
    } finally {
        loading.value = false;
    }
}

async function doCheckout(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/checkout`, null);
        // 重新搜索刷新结果
        if (query.value) await doSearch();
    } catch (e) { error.value = e.message; }
}
async function doUndoCheckout(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/undocheckout`, null);
        if (query.value) await doSearch();
    } catch (e) { error.value = e.message; }
}
async function doCheckin(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/checkin`, null);
        if (query.value) await doSearch();
    } catch (e) { error.value = e.message; }
}
</script>
