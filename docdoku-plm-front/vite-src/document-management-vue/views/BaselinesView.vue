<template>
  <div>
    <!-- 标题栏 -->
    <div class="well well-small" style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px">
      <strong><i class="fa fa-database"></i> {{ $t('BASELINES') }}</strong>
      <button v-if="isAdmin" class="btn btn-small btn-primary" @click="showNewModal = true">
        <i class="fa fa-plus"></i> {{ $t('NEW_BASELINE') }}
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

    <!-- 基线列表 -->
    <div v-if="loading" class="text-center"><i class="fa fa-spinner fa-spin"></i></div>
    <table v-else class="table table-striped table-hover table-condensed">
      <thead>
        <tr>
          <th style="width:20px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
          <th>{{ $t('NAME') }}</th>
          <th>{{ $t('TYPE') }}</th>
          <th>{{ $t('DESCRIPTION') }}</th>
          <th>{{ $t('AUTHOR') }}</th>
          <th>{{ $t('CREATION_DATE') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="baselines.length === 0">
          <td colspan="6" class="text-center muted">{{ $t('NO_DATA') }}</td>
        </tr>
        <tr v-for="bl in baselines" :key="bl.id">
          <td><input type="checkbox" :value="bl.id" v-model="selected" /></td>
          <td><strong>{{ bl.name }}</strong></td>
          <td>
            <span :class="bl.type === 'RELEASED' ? 'label label-success' : 'label'">{{ bl.type }}</span>
          </td>
          <td>{{ bl.description || '—' }}</td>
          <td>{{ bl.author?.name || bl.author?.login || '—' }}</td>
          <td>{{ formatDate(bl.creationDate) }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 新建基线弹窗 -->
  <Teleport to="body">
    <div v-if="showNewModal" class="modal-backdrop fade in" style="z-index:1040"></div>
    <div v-if="showNewModal" class="modal fade in" tabindex="-1" style="display:block;z-index:1050">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <button class="close" @click="showNewModal = false">×</button>
            <h3>{{ $t('NEW_BASELINE') }}</h3>
          </div>
          <div class="modal-body">
            <div v-if="newError" class="alert alert-error">{{ newError }}</div>
            <form @submit.prevent="createBaseline">
              <div class="control-group">
                <label class="control-label">{{ $t('NAME') }} *</label>
                <div class="controls">
                  <input v-model="newBl.name" class="input-block-level" required />
                </div>
              </div>
              <div class="control-group">
                <label class="control-label">{{ $t('DESCRIPTION') }}</label>
                <div class="controls">
                  <textarea v-model="newBl.description" class="input-block-level" rows="2"></textarea>
                </div>
              </div>
              <div class="control-group">
                <label class="control-label">{{ $t('TYPE') }}</label>
                <div class="controls">
                  <select v-model="newBl.type" class="input-block-level">
                    <option value="LATEST">LATEST</option>
                    <option value="RELEASED">RELEASED</option>
                  </select>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button class="btn" @click="showNewModal = false">{{ $t('CANCEL') }}</button>
            <button class="btn btn-primary" :disabled="creating" @click="createBaseline">
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

const baselines = ref([]);
const loading = ref(false);
const selected = ref([]);
const error = ref('');

const showNewModal = ref(false);
const newBl = ref({ name: '', description: '', type: 'LATEST' });
const newError = ref('');
const creating = ref(false);

const allChecked = computed(() => baselines.value.length > 0 && selected.value.length === baselines.value.length);

function toggleAll(e) {
    selected.value = e.target.checked ? baselines.value.map(b => b.id) : [];
}

function formatDate(ts) {
    if (!ts) return '—';
    return new Date(ts).toLocaleDateString();
}

async function loadBaselines() {
    loading.value = true;
    try {
        const data = await get(`/workspaces/${workspaceId.value}/document-baselines/`);
        baselines.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '加载基线失败';
    } finally {
        loading.value = false;
    }
}

async function createBaseline() {
    if (!newBl.value.name.trim()) return;
    creating.value = true;
    newError.value = '';
    try {
        await post(`/workspaces/${workspaceId.value}/document-baselines`, {
            name: newBl.value.name.trim(),
            description: newBl.value.description.trim(),
            type: newBl.value.type,
            baselinedDocuments: []
        });
        showNewModal.value = false;
        newBl.value = { name: '', description: '', type: 'LATEST' };
        await loadBaselines();
    } catch (e) {
        newError.value = e.message || '创建基线失败';
    } finally {
        creating.value = false;
    }
}

async function deleteSelected() {
    if (!selected.value.length) return;
    if (!confirm(`确定删除 ${selected.value.length} 个基线？`)) return;
    for (const id of selected.value) {
        try {
            await del(`/workspaces/${workspaceId.value}/document-baselines/${id}`);
        } catch (e) {
            error.value = e.message || `删除 ${id} 失败`;
        }
    }
    selected.value = [];
    await loadBaselines();
}

watch(workspaceId, (ws) => { if (ws) loadBaselines(); }, { immediate: true });
</script>
