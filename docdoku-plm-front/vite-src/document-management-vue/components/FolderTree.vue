<template>
  <ul class="nav nav-list" style="padding-left: 4px">
    <li v-for="folder in folders" :key="folder.id">
      <!-- 文件夹条目：点击展开/显示内容 -->
      <a
        href="#"
        class="nav-list-entry folder-entry"
        :class="{ active: activeFolder === folder.id }"
        @click.prevent="selectFolder(folder)"
        style="display:flex; align-items:center; gap:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis"
      >
        <i
          class="fa"
          :class="expanded[folder.id] ? 'fa-folder-open' : 'fa-folder'"
          @click.stop="toggleExpand(folder)"
          style="cursor:pointer; min-width:14px"
        ></i>
        <span style="overflow:hidden; text-overflow:ellipsis">{{ folder.name }}</span>
        <!-- 删除按钮（仅 admin 可见） -->
        <button
          v-if="isAdmin && !folder.home"
          class="btn btn-mini btn-danger"
          style="padding:1px 4px; margin-left:auto; flex-shrink:0"
          :title="$t('DELETE')"
          @click.stop="$emit('delete-folder', folder)"
        ><i class="fa fa-times"></i></button>
      </a>

      <!-- 递归子文件夹 -->
      <FolderTree
        v-if="expanded[folder.id] && subFolders[folder.id]"
        :folders="subFolders[folder.id]"
        :workspaceId="workspaceId"
        :activeFolder="activeFolder"
        :isAdmin="isAdmin"
        @select-folder="$emit('select-folder', $event)"
        @delete-folder="$emit('delete-folder', $event)"
      />
    </li>

    <!-- 新建文件夹按钮 -->
    <li v-if="isAdmin && showNewFolder">
      <a href="#" class="nav-list-entry" @click.prevent="startCreate">
        <i class="fa fa-plus"></i> {{ $t('NEW_FOLDER') }}
      </a>
    </li>
    <li v-if="creating">
      <div style="padding:4px">
        <input
          ref="newFolderInput"
          v-model="newFolderName"
          class="input-small"
          :placeholder="$t('FOLDER_S_NAME')"
          @keyup.enter="confirmCreate"
          @keyup.escape="creating = false"
          style="width:100%"
        />
        <div style="margin-top:4px; display:flex; gap:4px">
          <button class="btn btn-mini btn-primary" @click="confirmCreate">✓</button>
          <button class="btn btn-mini" @click="creating = false">✗</button>
        </div>
      </div>
    </li>
  </ul>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import { useAuthStore } from '../../vue-common/store/auth.js';

// 递归自引用
import FolderTree from './FolderTree.vue';

const props = defineProps({
    folders: { type: Array, default: () => [] },
    workspaceId: { type: String, default: '' },
    activeFolder: { type: String, default: '' },
    isAdmin: { type: Boolean, default: false },
    subFolders: { type: Object, default: () => ({}) },   // folderId → 子文件夹数组
    showNewFolder: { type: Boolean, default: true }
});

const emit = defineEmits(['select-folder', 'delete-folder', 'create-folder']);

// 展开状态
const expanded = ref({});

// 新建文件夹
const creating = ref(false);
const newFolderName = ref('');
const newFolderInput = ref(null);

function selectFolder(folder) {
    expanded.value[folder.id] = !expanded.value[folder.id];
    emit('select-folder', folder);
}

function toggleExpand(folder) {
    expanded.value[folder.id] = !expanded.value[folder.id];
}

async function startCreate() {
    creating.value = true;
    newFolderName.value = '';
    await nextTick();
    newFolderInput.value?.focus();
}

function confirmCreate() {
    const name = newFolderName.value.trim();
    if (name) {
        emit('create-folder', name);
    }
    creating.value = false;
    newFolderName.value = '';
}
</script>
