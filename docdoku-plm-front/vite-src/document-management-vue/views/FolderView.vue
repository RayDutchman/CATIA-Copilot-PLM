<template>
  <div class="row-fluid" style="height:100%">
    <!-- 左侧文件夹树 -->
    <div class="span3" style="border-right:1px solid #ddd; padding-right:8px; min-height:400px">
      <h5 style="margin:8px 0">
        <i class="fa fa-folder-open"></i> {{ $t('FOLDERS') }}
      </h5>
      <div v-if="loadingFolders" class="muted"><i class="fa fa-spinner fa-spin"></i></div>
      <FolderTree
        v-else
        :folders="rootFolders"
        :workspaceId="workspaceId"
        :activeFolder="activeFolderId"
        :isAdmin="isAdmin"
        :subFolders="subFolders"
        :showNewFolder="true"
        @select-folder="onSelectFolder"
        @delete-folder="onDeleteFolder"
        @create-folder="onCreateFolder"
      />
    </div>

    <!-- 右侧文档列表 -->
    <div class="span9">
      <!-- 标题栏 -->
      <div class="action-bar well well-small" style="margin-bottom:8px; display:flex; align-items:center; gap:8px; flex-wrap:wrap">
        <strong v-if="currentFolder">
          <i class="fa fa-folder"></i> {{ currentFolder.name }}
        </strong>
        <button
          v-if="currentFolder && isAdmin"
          class="btn btn-small btn-primary"
          @click="showNewDocModal = true"
        >
          <i class="fa fa-plus"></i> {{ $t('NEW_DOCUMENT') }}
        </button>
        <button
          v-if="selectedDocIds.length > 0 && isAdmin"
          class="btn btn-small btn-danger"
          @click="deleteSelectedDocs"
        >
          <i class="fa fa-trash-o"></i> {{ $t('DELETE') }} ({{ selectedDocIds.length }})
        </button>
      </div>

      <div v-if="error" class="alert alert-error">
        <button class="close" @click="error = ''">×</button>
        {{ error }}
      </div>

      <!-- 文档列表 -->
      <DocumentList
        :documents="documents"
        :loading="loadingDocs"
        :showActions="false"
        @checkout="doCheckout"
        @undo-checkout="doUndoCheckout"
        @checkin="doCheckin"
      />

      <!-- 文档选择复选框由 DocumentList 内部管理，这里传入 selectedDocIds -->
    </div>
  </div>

  <!-- 新建文档弹窗 -->
  <Teleport to="body">
    <div v-if="showNewDocModal" class="modal-backdrop fade in" style="z-index:1040"></div>
    <div v-if="showNewDocModal" class="modal fade in" tabindex="-1" style="display:block;z-index:1050">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <button class="close" @click="showNewDocModal = false">×</button>
            <h3>{{ $t('NEW_DOCUMENT') }}</h3>
          </div>
          <div class="modal-body">
            <div v-if="newDocError" class="alert alert-error">{{ newDocError }}</div>
            <form @submit.prevent="createDocument">
              <div class="control-group">
                <label class="control-label">{{ $t('DOCUMENT_S_REFERENCE') }} *</label>
                <div class="controls">
                  <input v-model="newDoc.reference" class="input-block-level" required />
                </div>
              </div>
              <div class="control-group">
                <label class="control-label">{{ $t('DOCUMENT_S_TITLE') }}</label>
                <div class="controls">
                  <input v-model="newDoc.title" class="input-block-level" />
                </div>
              </div>
              <div class="control-group">
                <label class="control-label">{{ $t('DESCRIPTION') }}</label>
                <div class="controls">
                  <textarea v-model="newDoc.description" class="input-block-level" rows="2"></textarea>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button class="btn" @click="showNewDocModal = false">{{ $t('CANCEL') }}</button>
            <button class="btn btn-primary" :disabled="creatingDoc" @click="createDocument">
              <span v-if="creatingDoc"><i class="fa fa-spinner fa-spin"></i></span>
              {{ $t('CREATE') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../vue-common/store/auth.js';
import { useAppStore } from '../../vue-common/store/app.js';
import { useApi } from '../../vue-common/composables/useApi.js';
import FolderTree from '../components/FolderTree.vue';
import DocumentList from '../components/DocumentList.vue';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const appStore = useAppStore();
const { get, post, del } = useApi();

// 计算属性：工作区 ID
const workspaceId = computed(() => route.params.workspaceId || '');

// 计算属性：当前路径
const currentPath = computed(() => {
    const p = route.params.path;
    return Array.isArray(p) ? p.join('/') : (p || null);
});

// 是否管理员
const isAdmin = computed(() => authStore.isAdmin);

// 文件夹状态
const rootFolders = ref([]);
const subFolders = ref({});  // folderId → 子文件夹[]
const loadingFolders = ref(false);
const activeFolderId = ref('');
const currentFolder = ref(null);

// 文档状态
const documents = ref([]);
const loadingDocs = ref(false);
const selectedDocIds = ref([]);
const error = ref('');

// 新建文档弹窗
const showNewDocModal = ref(false);
const newDoc = ref({ reference: '', title: '', description: '' });
const newDocError = ref('');
const creatingDoc = ref(false);

// 加载根文件夹
async function loadRootFolders() {
    loadingFolders.value = true;
    try {
        const ws = workspaceId.value;
        const data = await get(`/workspaces/${ws}/folders`);
        // 注入用户主文件夹
        const login = authStore.account?.login || '';
        const homeFolder = {
            id: `${ws}:~${login}`,
            name: `~${login}`,
            path: ws,
            home: true
        };
        rootFolders.value = [homeFolder, ...(Array.isArray(data) ? data : [])];
    } catch (e) {
        error.value = e.message || '加载文件夹失败';
    } finally {
        loadingFolders.value = false;
    }
}

// 加载子文件夹
async function loadSubFolders(folder) {
    try {
        const ws = workspaceId.value;
        const data = await get(`/workspaces/${ws}/folders/${encodeURIComponent(folder.id)}/folders`);
        subFolders.value[folder.id] = Array.isArray(data) ? data : [];
    } catch (e) {
        // 忽略子文件夹加载错误
    }
}

// 加载文件夹中的文档
async function loadDocuments(folderId) {
    if (!folderId) return;
    loadingDocs.value = true;
    documents.value = [];
    try {
        const ws = workspaceId.value;
        const data = await get(`/workspaces/${ws}/folders/${encodeURIComponent(folderId)}/documents`);
        documents.value = Array.isArray(data) ? data : [];
    } catch (e) {
        error.value = e.message || '加载文档失败';
    } finally {
        loadingDocs.value = false;
    }
}

// 选择文件夹
async function onSelectFolder(folder) {
    activeFolderId.value = folder.id;
    currentFolder.value = folder;
    selectedDocIds.value = [];
    error.value = '';

    // 加载子文件夹和文档
    await Promise.all([
        loadSubFolders(folder),
        loadDocuments(folder.id)
    ]);

    // 更新路由
    const ws = workspaceId.value;
    router.push(`/${ws}/folders/${encodeURIComponent(folder.id)}`);
}

// 删除文件夹
async function onDeleteFolder(folder) {
    if (!confirm(`${folder.name} を削除しますか？`)) return;
    try {
        const ws = workspaceId.value;
        await del(`/workspaces/${ws}/folders/${encodeURIComponent(folder.id)}`);
        await loadRootFolders();
        if (activeFolderId.value === folder.id) {
            currentFolder.value = null;
            documents.value = [];
        }
    } catch (e) {
        error.value = e.message || '删除文件夹失败';
    }
}

// 创建文件夹
async function onCreateFolder(name) {
    try {
        const ws = workspaceId.value;
        const parentId = activeFolderId.value || ws;
        await post(`/workspaces/${ws}/folders`, { completePath: `${parentId}/${name}` });
        await loadRootFolders();
    } catch (e) {
        error.value = e.message || '创建文件夹失败';
    }
}

// 签出文档
async function doCheckout(doc) {
    try {
        const ws = workspaceId.value;
        await post(`/workspaces/${ws}/documents/${encodeURIComponent(doc.id)}/checkout`, null);
        await loadDocuments(activeFolderId.value);
    } catch (e) {
        error.value = e.message || '签出失败';
    }
}

// 取消签出
async function doUndoCheckout(doc) {
    try {
        const ws = workspaceId.value;
        await post(`/workspaces/${ws}/documents/${encodeURIComponent(doc.id)}/undocheckout`, null);
        await loadDocuments(activeFolderId.value);
    } catch (e) {
        error.value = e.message || '取消签出失败';
    }
}

// 签入
async function doCheckin(doc) {
    try {
        const ws = workspaceId.value;
        await post(`/workspaces/${ws}/documents/${encodeURIComponent(doc.id)}/checkin`, null);
        await loadDocuments(activeFolderId.value);
    } catch (e) {
        error.value = e.message || '签入失败';
    }
}

// 创建文档
async function createDocument() {
    if (!newDoc.value.reference.trim()) return;
    creatingDoc.value = true;
    newDocError.value = '';
    try {
        const ws = workspaceId.value;
        const folderId = activeFolderId.value || ws;
        await post(`/workspaces/${ws}/folders/${encodeURIComponent(folderId)}/documents`, {
            reference: newDoc.value.reference.trim(),
            title: newDoc.value.title.trim(),
            description: newDoc.value.description.trim()
        });
        showNewDocModal.value = false;
        newDoc.value = { reference: '', title: '', description: '' };
        await loadDocuments(folderId);
    } catch (e) {
        newDocError.value = e.message || '创建文档失败';
    } finally {
        creatingDoc.value = false;
    }
}

// 删除选中文档
async function deleteSelectedDocs() {
    if (!selectedDocIds.value.length) return;
    if (!confirm(`确定删除 ${selectedDocIds.value.length} 个文档？`)) return;
    const ws = workspaceId.value;
    for (const id of selectedDocIds.value) {
        try {
            await del(`/workspaces/${ws}/documents/${encodeURIComponent(id)}`);
        } catch (e) {
            error.value = e.message || `删除 ${id} 失败`;
        }
    }
    selectedDocIds.value = [];
    await loadDocuments(activeFolderId.value);
}

// 路由参数变化时重新加载
watch([workspaceId, currentPath], async ([ws]) => {
    if (!ws) return;
    await loadRootFolders();
    // 如果路由带了路径，自动展开对应文件夹
    if (currentPath.value) {
        // 从路径推断文件夹 id（实际上路径就是 folderId 的 encoded 形式）
        const fid = currentPath.value;
        activeFolderId.value = fid;
        // 找到对应文件夹对象
        const found = rootFolders.value.find(f => f.id === fid);
        if (found) {
            currentFolder.value = found;
        } else {
            currentFolder.value = { id: fid, name: decodeURIComponent(fid) };
        }
        await loadDocuments(fid);
    }
}, { immediate: true });
</script>
