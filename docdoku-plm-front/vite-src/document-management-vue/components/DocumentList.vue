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

    <!-- 文档表格：16 列（与表头严格对应） -->
    <table v-else class="table table-striped table-hover table-condensed" style="font-size:12px">
      <thead>
        <tr>
          <th style="width:20px"><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
          <th>{{ $t('DOCUMENT_S_REFERENCE') }}</th>
          <th>{{ $t('VERSION') }}</th>
          <th>{{ $t('ITERATION') }}</th>
          <th>{{ $t('TYPE') }}</th>
          <th>{{ $t('DOCUMENT_S_TITLE') }}</th>
          <th>{{ $t('AUTHOR') }}</th>
          <th>{{ $t('MODIFICATION_DATE') }}</th>
          <th>{{ $t('STATUS') }}</th>
          <th>{{ $t('CHECKOUT_BY') }}</th>
          <th style="width:20px" :title="$t('ACL')"><i class="fa fa-key"></i></th>
          <th style="width:20px" :title="$t('ITERATION_CHANGE_SUBSCRIPTION')">🔒</th>
          <th style="width:20px" :title="$t('STATE_CHANGE_SUBSCRIPTION')">🔄</th>
          <th style="width:20px" :title="$t('PUBLIC_SHARED')">🌐</th>
          <th style="width:20px" :title="$t('ATTACHED_FILES')">📎</th>
          <th style="width:120px">{{ $t('ACTIONS') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="documents.length === 0">
          <td colspan="16" class="text-center muted">{{ $t('NO_DOCUMENT') }}</td>
        </tr>
        <tr
          v-for="doc in documents"
          :key="doc.id"
          :class="{
            success: isCheckedOut(doc) && isMyCheckout(doc),
            warning: isCheckedOut(doc) && !isMyCheckout(doc)
          }"
        >
          <!-- 1. 选择框 -->
          <td><input type="checkbox" :value="doc.id" v-model="selected" /></td>

          <!-- 2. 文档 ID -->
          <td><strong>{{ getReference(doc) }}</strong></td>

          <!-- 3. 版本号 -->
          <td>{{ doc.version }}</td>

          <!-- 4. 迭代号 -->
          <td>{{ getIteration(doc) }}</td>

          <!-- 5. 类型 -->
          <td>{{ doc.type || '—' }}</td>

          <!-- 6. 标题 -->
          <td>{{ doc.title || '—' }}</td>

          <!-- 7. 作者 -->
          <td>{{ doc.author?.name || doc.author?.login || '—' }}</td>

          <!-- 8. 修改时间（取最新迭代的 modificationDate，fallback 到 creationDate） -->
          <td>{{ formatDate(getLastIteration(doc)?.modificationDate || doc.creationDate) }}</td>

          <!-- 9. 状态 -->
          <td>
            <span :class="statusBadge(doc)">{{ $t(doc.status || 'UNDEFINED') }}</span>
          </td>

          <!-- 10. 签出人 -->
          <td>{{ doc.checkOutUser?.login || '—' }}</td>

          <!-- 11. ACL（有访问控制时显示锁） -->
          <td style="text-align:center">
            <i v-if="hasAcl(doc)" class="fa fa-lock" :title="$t('ACL_RESTRICTED')"></i>
            <i v-else class="fa fa-unlock-alt muted"></i>
          </td>

          <!-- 12. 🔒 迭代变更订阅 -->
          <td style="text-align:center">
            <i v-if="doc.iterationSubscription" class="fa fa-check-circle" style="color:#5cb85c"></i>
          </td>

          <!-- 13. 🔄 状态变更订阅 -->
          <td style="text-align:center">
            <i v-if="doc.stateSubscription" class="fa fa-check-circle" style="color:#5cb85c"></i>
          </td>

          <!-- 14. 🌐 公开共享 -->
          <td style="text-align:center">
            <i v-if="doc.publicShared" class="fa fa-globe" style="color:#337ab7"></i>
          </td>

          <!-- 15. 📎 附件数量 -->
          <td style="text-align:center">
            <span v-if="hasFiles(doc)" :title="$t('FILES')">
              <i class="fa fa-paperclip"></i>{{ fileCount(doc) }}
            </span>
          </td>

          <!-- 16. 操作按钮 -->
          <td>
            <!-- 签出：未签出时显示 -->
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

// 获取最新迭代对象（documentIterations 最后一个）
function getLastIteration(doc) {
    const iters = doc.documentIterations;
    if (!iters || iters.length === 0) return null;
    return iters[iters.length - 1];
}

// 文档 Reference：id 最后一个 "-" 之前的部分（去掉版本号）
function getReference(doc) {
    const id = doc.id || '';
    const lastDash = id.lastIndexOf('-');
    return lastDash > 0 ? id.substring(0, lastDash) : id;
}

// 迭代号：取最新迭代的 iteration 字段
function getIteration(doc) {
    return getLastIteration(doc)?.iteration ?? '—';
}

// 是否有 ACL 限制
function hasAcl(doc) {
    return !!doc.acl;
}

// 是否有附件
function hasFiles(doc) {
    return (getLastIteration(doc)?.attachedFiles?.length ?? 0) > 0;
}

// 附件数量
function fileCount(doc) {
    return getLastIteration(doc)?.attachedFiles?.length ?? 0;
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
