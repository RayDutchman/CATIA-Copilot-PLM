<template>
  <div>
    <div class="row-fluid">
      <!-- 左侧标签列表 -->
      <div class="span3" style="border-right:1px solid #ddd; padding-right:8px; min-height:400px">
        <h5 style="margin:8px 0"><i class="fa fa-tags"></i> {{ $t('TAGS') }}</h5>
        <div v-if="loadingTags" class="muted"><i class="fa fa-spinner fa-spin"></i></div>
        <ul v-else class="nav nav-list">
          <li v-for="tag in tags" :key="tag.id" :class="{ active: activeTagId === tag.id }">
            <a href="#" class="nav-list-entry" @click.prevent="selectTag(tag)">
              <i class="fa fa-tag"></i> {{ tag.label }}
            </a>
          </li>
          <li v-if="tags.length === 0" class="muted" style="padding:4px 15px">{{ $t('NO_TAGS') }}</li>
        </ul>
      </div>

      <!-- 右侧文档列表 -->
      <div class="span9">
        <div v-if="activeTag">
          <h5 style="margin:8px 0">
            <i class="fa fa-tag"></i> {{ activeTag.label }}
          </h5>
        </div>
        <div v-else class="muted" style="padding:20px">{{ $t('SELECT_TAG') }}</div>

        <div v-if="error" class="alert alert-error">
          <button class="close" @click="error = ''">×</button>
          {{ error }}
        </div>

        <DocumentList
          v-if="activeTag"
          :documents="documents"
          :loading="loadingDocs"
          :showActions="false"
          @checkout="doCheckout"
          @undo-checkout="doUndoCheckout"
          @checkin="doCheckin"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../vue-common/store/auth.js';
import { useApi } from '../../vue-common/composables/useApi.js';
import DocumentList from '../components/DocumentList.vue';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { get, post } = useApi();

const workspaceId = computed(() => route.params.workspaceId || '');
const routeTagId = computed(() => route.params.tagId || null);

const tags = ref([]);
const loadingTags = ref(false);
const activeTagId = ref('');
const activeTag = ref(null);
const documents = ref([]);
const loadingDocs = ref(false);
const error = ref('');

async function loadTags() {
    loadingTags.value = true;
    try {
        const data = await get(`/workspaces/${workspaceId.value}/tags`);
        tags.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '加载标签失败';
    } finally {
        loadingTags.value = false;
    }
}

async function selectTag(tag) {
    activeTagId.value = tag.id;
    activeTag.value = tag;
    documents.value = [];
    error.value = '';
    loadingDocs.value = true;
    try {
        const data = await get(`/workspaces/${workspaceId.value}/tags/${encodeURIComponent(tag.label)}/documents`);
        documents.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '加载标签文档失败';
    } finally {
        loadingDocs.value = false;
    }
    router.push(`/${workspaceId.value}/tags/${encodeURIComponent(tag.id)}`);
}

async function doCheckout(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/checkout`, null);
        if (activeTag.value) await selectTag(activeTag.value);
    } catch (e) { error.value = e.message; }
}
async function doUndoCheckout(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/undocheckout`, null);
        if (activeTag.value) await selectTag(activeTag.value);
    } catch (e) { error.value = e.message; }
}
async function doCheckin(doc) {
    try {
        await post(`/workspaces/${workspaceId.value}/documents/${encodeURIComponent(doc.id)}/checkin`, null);
        if (activeTag.value) await selectTag(activeTag.value);
    } catch (e) { error.value = e.message; }
}

watch(workspaceId, async (ws) => {
    if (!ws) return;
    await loadTags();
    // 如果路由带了 tagId，自动激活
    if (routeTagId.value) {
        const found = tags.value.find(t => String(t.id) === String(routeTagId.value));
        if (found) await selectTag(found);
    }
}, { immediate: true });
</script>
