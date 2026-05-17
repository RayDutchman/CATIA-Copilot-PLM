<template>
  <!-- 工作区自定义设置，对应原 workspace-customizations.html + views/workspace-customizations.js -->
  <!-- 原版用 selectize.js：空 input 点击展开下拉，选中后以 badge 显示并可拖拽排序 -->
  <!-- Vue 版用纯 CSS + Vue 事件复现 selectize 交互 -->
  <div class="actions well">
    <button class="btn btn-default" @click="$router.push('/')">{{ t('BACK') }}</button>
  </div>

  <div class="notifications">
    <AlertBanner v-if="error"   type="error"   :message="error"     @close="error = null" />
    <AlertBanner v-if="success" type="success" :message="t('SAVED')" @close="success = false" />
  </div>

  <div class="margin" id="customizations-content">
    <h3>{{ t('PARTS') }}</h3>

    <div id="columns-selectize">
      <div>
        <label>{{ t('CUSTOMIZE_PART_TABLE_COLUMNS') }}</label>

        <!-- selectize 风格容器：已选列显示为 badge，末尾是空 input -->
        <div
          ref="selectizeContainer"
          class="selectize-input"
          :class="{ focus: dropdownOpen }"
          @click="focusInput"
        >
          <!-- 已选列 badge（带 × 移除） -->
          <div
            v-for="col in selectedColumns"
            :key="col"
            class="item"
          >
            <span>{{ columnLabel(col) }}</span>
            <a
              href="#"
              class="remove"
              @click.prevent.stop="removeColumn(col)"
            >×</a>
          </div>

          <!-- 空 input，点击或聚焦打开下拉 -->
          <input
            ref="selectizeInput"
            v-model="filterText"
            type="text"
            :placeholder="selectedColumns.length ? '' : t('CUSTOMIZE_PART_TABLE_COLUMNS') + '…'"
            autocomplete="off"
            @focus="openDropdown"
            @blur="scheduleClose"
            @keydown.escape="closeDropdown"
          />
        </div>

        <!-- 下拉选项列表 -->
        <div v-show="dropdownOpen && filteredOptions.length" class="selectize-dropdown">
          <div class="selectize-dropdown-content">
            <div
              v-for="col in filteredOptions"
              :key="col"
              class="option"
              :class="{ active: hoveredOption === col }"
              @mousedown.prevent="addColumnFromDropdown(col)"
              @mouseenter="hoveredOption = col"
              @mouseleave="hoveredOption = ''"
            >
              {{ columnLabel(col) }}
            </div>
          </div>
        </div>

        <p v-if="loading" class="muted">Loading…</p>
        <p v-if="!loading && !selectedColumns.length" class="text-warning">
          {{ t('EMPTY_COLUMNS') }}
        </p>
      </div>
    </div>

    <!-- 按钮行（对应原版 .reset / .clear / .submit） -->
    <!-- .reset → DEFAULT_COLUMNS（"默认列"）；.clear → RESET（"重置"）；.submit → SAVE -->
    <div style="margin-top:8px; overflow:hidden;">
      <button class="btn btn-default reset" :disabled="loading" @click="resetToDefault">
        {{ t('DEFAULT_COLUMNS') }}
      </button>
      <button class="btn btn-default clear" :disabled="loading" style="margin-left:4px;" @click="clearAll">
        {{ t('RESET') }}
      </button>
      <button class="btn btn-primary submit pull-right" :disabled="loading || saving" @click="save">
        {{ saving ? '…' : t('SAVE') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'

const { t }    = useI18n()
const route    = useRoute()
const api      = useApi()

const workspaceId = computed(() => route.params.workspaceId)

const error   = ref(null)
const success = ref(false)
const loading = ref(true)
const saving  = ref(false)

// 当前已选列（从 API 加载）
const selectedColumns = ref([])

// 所有可用的默认列（对应原版 PartTableColumns.defaultColumns）
const ALL_COLUMNS = [
  'pr.number',
  'pr.version',
  'pr.iteration',
  'pr.type',
  'pr.name',
  'pr.author',
  'pr.modificationDate',
  'pr.lifecycleSate',
  'pr.checkoutUser',
  'pr.acl',
]

// 列名 → i18n key 映射（对应原版 columnNameMapping）
const COLUMN_KEY_MAP = {
  'pr.number':           'PART_NUMBER',
  'pr.version':          'VERSION',
  'pr.iteration':        'ITERATION',
  'pr.type':             'TYPE',
  'pr.name':             'PART_NAME',
  'pr.author':           'AUTHOR_NAME',
  'pr.modificationDate': 'MODIFICATION_DATE',
  'pr.lifecycleSate':    'LIFECYCLE_STATE',
  'pr.checkoutUser':     'CHECKOUT_BY',
  'pr.acl':              'ACL',
}

function columnLabel(col) {
  const key = COLUMN_KEY_MAP[col]
  return key ? t(key) : col
}

// ── selectize 交互状态 ─────────────────────────────────────
const dropdownOpen   = ref(false)
const filterText     = ref('')
const hoveredOption  = ref('')
const selectizeInput = ref(null)
let   closeTimer     = null

// 可选列 = 全部列中还未选中的，按 filterText 过滤
const filteredOptions = computed(() => {
  const q = filterText.value.toLowerCase()
  return ALL_COLUMNS.filter(c => {
    if (selectedColumns.value.includes(c)) return false
    if (!q) return true
    return columnLabel(c).toLowerCase().includes(q)
  })
})

function focusInput() {
  selectizeInput.value?.focus()
}

function openDropdown() {
  if (closeTimer) { clearTimeout(closeTimer); closeTimer = null }
  dropdownOpen.value = true
}

function scheduleClose() {
  // blur 后延迟 150ms 关闭，给 mousedown 事件留时间
  closeTimer = setTimeout(() => {
    dropdownOpen.value = false
    filterText.value = ''
    hoveredOption.value = ''
  }, 150)
}

function closeDropdown() {
  dropdownOpen.value = false
  filterText.value = ''
}

function addColumnFromDropdown(col) {
  if (closeTimer) { clearTimeout(closeTimer); closeTimer = null }
  addColumn(col)
  filterText.value = ''
  // 继续保持 focus 以便连续选列
  selectizeInput.value?.focus()
}

function addColumn(col) {
  if (col && !selectedColumns.value.includes(col)) {
    selectedColumns.value = [...selectedColumns.value, col]
  }
}

function removeColumn(col) {
  selectedColumns.value = selectedColumns.value.filter(c => c !== col)
}

// ── 按钮操作 ──────────────────────────────────────────────

// .reset 按钮：恢复默认列（DEFAULT_COLUMNS）
function resetToDefault() {
  selectedColumns.value = [...ALL_COLUMNS]
}

// .clear 按钮：清空所有列（RESET）
function clearAll() {
  selectedColumns.value = []
}

// .submit 按钮：保存（PUT /front-options）
async function save() {
  if (!selectedColumns.value.length) {
    error.value = t('EMPTY_COLUMNS')
    return
  }
  saving.value = true
  error.value = null
  success.value = false
  try {
    await api.put(`/workspaces/${workspaceId.value}/front-options`, {
      partTableColumns: selectedColumns.value,
    })
    success.value = true
  } catch (err) {
    error.value = err.message || 'Failed to save customizations'
  } finally {
    saving.value = false
  }
}

// ── 生命周期 ───────────────────────────────────────────────
onMounted(async () => {
  try {
    const data = await api.get(`/workspaces/${workspaceId.value}/front-options`)
    selectedColumns.value = data?.partTableColumns?.length
      ? data.partTableColumns
      : [...ALL_COLUMNS]
  } catch {
    selectedColumns.value = [...ALL_COLUMNS]
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* selectize 风格输入框，模仿 selectize.css 核心样式 */
.selectize-input {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  min-height: 38px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: text;
  position: relative;
}
.selectize-input.focus {
  border-color: #66afe9;
  box-shadow: inset 0 1px 1px rgba(0,0,0,.075), 0 0 8px rgba(102,175,233,.6);
  outline: 0;
}

/* 已选 item badge */
.selectize-input .item {
  display: inline-flex;
  align-items: center;
  background: #d0e8f8;
  border: 1px solid #aacce8;
  border-radius: 3px;
  padding: 2px 6px;
  font-size: 12px;
  line-height: 1.4;
  cursor: default;
  white-space: nowrap;
}
.selectize-input .item .remove {
  color: #6699cc;
  margin-left: 5px;
  text-decoration: none;
  font-weight: bold;
  font-size: 13px;
  line-height: 1;
}
.selectize-input .item .remove:hover {
  color: #c0392b;
}

/* 内嵌 input */
.selectize-input input {
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  min-width: 80px;
  flex: 1;
  padding: 0;
  margin: 0;
}

/* 下拉面板 */
.selectize-dropdown {
  position: absolute;
  z-index: 1050;
  margin-top: 2px;
  background: #fff;
  border: 1px solid #ccc;
  border-radius: 4px;
  box-shadow: 0 6px 12px rgba(0,0,0,.175);
  width: 100%;
  max-height: 200px;
  overflow-y: auto;
}
.selectize-dropdown-content {
  padding: 4px 0;
}
.selectize-dropdown .option {
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.selectize-dropdown .option.active,
.selectize-dropdown .option:hover {
  background: #428bca;
  color: #fff;
}

/* 让父容器成为 relative，以便下拉定位 */
#columns-selectize > div {
  position: relative;
}
</style>
