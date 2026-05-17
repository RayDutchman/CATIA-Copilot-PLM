<template>
  <div>
    <!-- 标题栏 -->
    <div class="well well-small" style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px">
      <strong><i class="fa fa-file-text-o"></i> {{ $t('DOCUMENT_TEMPLATES') }}</strong>
      <button v-if="isAdmin" class="btn btn-small btn-primary" @click="showNewModal = true">
        <i class="fa fa-plus"></i> {{ $t('NEW_TEMPLATE') }}
      </button>
      <button
        v-if="selected.length > 0 && isAdmin"
        class="btn btn-small btn-danger"
        @click="deleteSelected"
      >
        <i class="fa fa-trash-o"></i> {{ $t('DELETE') }} ({{ selected.length }})
      </button>
    </div>

    <div v-if="error" class="alert alert-error">
      <button class="close" @click="error = ''">×</button>
      {{ error }}
    </div>

    <!-- 模板列表 -->
    <div v-if="loading" class="text-center"><i class="fa fa-spinner fa-spin"></i></div>
    <table v-else class="table table-striped table-hover table-condensed">
      <thead>
        <tr>
          <th style="width:20px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
          <th>{{ $t('REFERENCE') }}</th>
          <th>{{ $t('TYPE') }}</th>
          <th>{{ $t('MASK') }}</th>
          <th>{{ $t('ID_GENERATED') }}</th>
          <th>{{ $t('MODIFICATION_DATE') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="templates.length === 0">
          <td colspan="6" class="text-center muted">{{ $t('NO_DATA') }}</td>
        </tr>
        <tr v-for="tpl in templates" :key="tpl.id">
          <td><input type="checkbox" :value="tpl.id" v-model="selected" /></td>
          <td><strong>{{ tpl.reference }}</strong></td>
          <td>{{ tpl.documentType || '—' }}</td>
          <td>{{ tpl.mask || '—' }}</td>
          <td>
            <i :class="tpl.idGenerated ? 'fa fa-check text-success' : 'fa fa-times text-error'"></i>
          </td>
          <td>{{ formatDate(tpl.modificationDate) }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 新建模板弹窗 -->
  <Teleport to="body">
    <div v-if="showNewModal" class="modal-backdrop fade in" style="z-index:1040"></div>
    <div v-if="showNewModal" class="modal fade in" tabindex="-1" style="display:block;z-index:1050">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <button class="close" @click="showNewModal = false">×</button>
            <h3>{{ $t('NEW_TEMPLATE') }}</h3>
          </div>
          <div class="modal-body">
            <div v-if="newError" class="alert alert-error">{{ newError }}</div>
            <form @submit.prevent="createTemplate">
              <div class="control-group">
                <label class="control-label">{{ $t('REFERENCE') }} *</label>
                <div class="controls">
                  <input v-model="newTpl.reference" class="input-block-level" required />
                </div>
              </div>
              <div class="control-group">
                <label class="control-label">{{ $t('TYPE') }}</label>
                <div class="controls">
                  <input v-model="newTpl.documentType" class="input-block-level" />
                </div>
              </div>
              <div class="control-group">
                <label class="control-label">{{ $t('MASK') }}</label>
                <div class="controls">
                  <input v-model="newTpl.mask" class="input-block-level" :placeholder="$t('MASK_HELP').split('\n')[0]" />
                </div>
              </div>
              <div class="control-group">
                <div class="controls">
                  <label class="checkbox">
                    <input type="checkbox" v-model="newTpl.idGenerated" />
                    {{ $t('ID_GENERATED') }}
                  </label>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button class="btn" @click="showNewModal = false">{{ $t('CANCEL') }}</button>
            <button class="btn btn-primary" :disabled="creating" @click="createTemplate">
              <span v-if="creating"><i class="fa fa-spinner fa-spin"></i></span>
              {{ $t('CREATE') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '../../vue-common/store/auth.js';
import { useApi } from '../../vue-common/composables/useApi.js';

const route = useRoute();
const authStore = useAuthStore();
const { get, post, del } = useApi();

const workspaceId = computed(() => route.params.workspaceId || '');
const isAdmin = computed(() => authStore.isAdmin);

const templates = ref([]);
const loading = ref(false);
const selected = ref([]);
const error = ref('');

// 新建模板
const showNewModal = ref(false);
const newTpl = ref({ reference: '', documentType: '', mask: '', idGenerated: false });
const newError = ref('');
const creating = ref(false);

const allChecked = computed(() => templates.value.length > 0 && selected.value.length === templates.value.length);

function toggleAll(e) {
    selected.value = e.target.checked ? templates.value.map(t => t.id) : [];
}

function formatDate(ts) {
    if (!ts) return '—';
    return new Date(ts).toLocaleDateString();
}

async function loadTemplates() {
    loading.value = true;
    try {
        const data = await get(`/workspaces/${workspaceId.value}/document-templates`);
        templates.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '加载模板失败';
    } finally {
        loading.value = false;
    }
}

async function createTemplate() {
    if (!newTpl.value.reference.trim()) return;
    creating.value = true;
    newError.value = '';
    try {
        await post(`/workspaces/${workspaceId.value}/document-templates`, {
            reference: newTpl.value.reference.trim(),
            documentType: newTpl.value.documentType.trim(),
            mask: newTpl.value.mask.trim(),
            idGenerated: newTpl.value.idGenerated,
            attributeTemplates: [],
            attributesLocked: false
        });
        showNewModal.value = false;
        newTpl.value = { reference: '', documentType: '', mask: '', idGenerated: false };
        await loadTemplates();
    } catch (e) {
        newError.value = e.message || '创建模板失败';
    } finally {
        creating.value = false;
    }
}

async function deleteSelected() {
    if (!selected.value.length) return;
    if (!confirm(`确定删除 ${selected.value.length} 个模板？`)) return;
    for (const id of selected.value) {
        try {
            await del(`/workspaces/${workspaceId.value}/document-templates/${encodeURIComponent(id)}`);
        } catch (e) {
            error.value = e.message || `删除 ${id} 失败`;
        }
    }
    selected.value = [];
    await loadTemplates();
}

watch(workspaceId, (ws) => { if (ws) loadTemplates(); }, { immediate: true });
</script>
