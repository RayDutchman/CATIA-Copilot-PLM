<template>
  <div class="document-list">
    <!-- 操作栏 -->
    <div v-if="showActions" class="action-bar well well-small" style="margin-bottom:8px">
      <slot name="actions" />
      <button
        v-if="selected.length > 0 && canDelete"
        class="btn btn-small btn-danger"
        @click="$emit('delete-selected', selected)"
      >
        <i class="fa fa-trash-o"></i> {{ $t('DELETE') }}
      </button>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="alert alert-error">
      <button type="button" class="close" @click="error = ''">×</button>
      {{ error }}
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="text-center" style="padding:20px">
      <i class="fa fa-spinner fa-spin"></i> {{ $t('LOADING') }}
    </div>

    <!-- 文档表格 -->
    <table v-else class="table table-striped table-hover table-condensed" style="font-size:12px">
      <thead>
        <tr>
          <th style="width:20px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
          <th>{{ $t('DOCUMENT_S_REFERENCE') }}</th>
          <th>{{ $t('VERSION') }}</th>
          <th>{{ $t('DOCUMENT_S_TITLE') }}</th>
          <th>{{ $t('AUTHOR') }}</th>
          <th>{{ $t('MODIFICATION_DATE') }}</th>
          <th>{{ $t('STATUS') }}</th>
          <th>{{ $t('CHECKOUT_BY') }}</th>
          <th style="width:120px">{{ $t('ACTIONS') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="documents.length === 0">
          <td colspan="9" class="text-center muted">{{ $t('NO_DOCUMENT') }}</td>
        </tr>
        <tr
          v-for="doc in documents"
          :key="doc.id"
          :class="{ success: isCheckedOut(doc) && isMyCheckout(doc), warning: isCheckedOut(doc) && !isMyCheckout(doc) }"
        >
          <td><input type="checkbox" :value="doc.id" v-model="selected" /></td>
          <td>
            <strong>{{ getReference(doc) }}</strong>
          </td>
          <td>{{ doc.version }}</td>
          <td>{{ doc.title || '—' }}</td>
          <td>{{ doc.author?.name || doc.author?.login || '—' }}</td>
          <td>{{ formatDate(doc.modificationDate) }}</td>
          <td>
            <span :class="statusBadge(doc)">{{ $t(doc.status || 'UNDEFINED') }}</span>
          </td>
          <td>{{ doc.checkOutUser?.login || '—' }}</td>
          <td>
            <!-- 签出按钮：未签出时显示 -->
            <button
              v-if="!isCheckedOut(doc) && !doc.obsolete"
              class="btn btn-mini"
              :title="$t('CHECKOUT')"
              @click="$emit('checkout', doc)"
            ><i class="fa fa-sign-out"></i></button>
            <!-- 取消签出：自己签出时显示 -->
            <button
              v-if="isMyCheckout(doc)"
              class="btn btn-mini btn-warning"
              :title="$t('CANCEL_CHECKOUT')"
              @click="$emit('undo-checkout', doc)"
            ><i class="fa fa-undo"></i></button>
            <!-- 签入：自己签出时显示 -->
            <button
              v-if="isMyCheckout(doc)"
              class="btn btn-mini btn-success"
              :title="$t('CHECKIN')"
              @click="$emit('checkin', doc)"
            ><i class="fa fa-sign-in"></i></button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useAuthStore } from '../../vue-common/store/auth.js';

const props = defineProps({
    documents: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    showActions: { type: Boolean, default: true },
    canDelete: { type: Boolean, default: false }
});

const emit = defineEmits(['delete-selected', 'checkout', 'undo-checkout', 'checkin']);

const authStore = useAuthStore();
const error = ref('');
const selected = ref([]);

// 文档 ID 格式：reference-version（如 DOC001-A）
function getReference(doc) {
    const id = doc.id || '';
    const lastDash = id.lastIndexOf('-');
    return lastDash > 0 ? id.substring(0, lastDash) : id;
}

// 判断是否已签出
function isCheckedOut(doc) {
    return !!doc.checkOutUser;
}

// 判断是否本人签出
function isMyCheckout(doc) {
    return doc.checkOutUser?.login === authStore.account?.login;
}

// 格式化日期
function formatDate(ts) {
    if (!ts) return '—';
    return new Date(ts).toLocaleDateString();
}

// 状态徽章样式
function statusBadge(doc) {
    const s = doc.status;
    if (s === 'RELEASED') return 'label label-success';
    if (s === 'OBSOLETE') return 'label label-inverse';
    return 'label';
}

// 全选/取消全选
const allChecked = computed(() => props.documents.length > 0 && selected.value.length === props.documents.length);
function toggleAll(e) {
    if (e.target.checked) {
        selected.value = props.documents.map(d => d.id);
    } else {
        selected.value = [];
    }
}
</script>
