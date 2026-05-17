<template>
  <div class="actions well">
    <router-link to="/" class="btn btn-default">{{ t('BACK') }}</router-link>
    <button
      v-if="hasOrg"
      class="btn btn-custom"
      @click.prevent="showDeleteModal = true"
    >
      {{ t('DELETE') }}
    </button>
  </div>

  <div class="notifications">
    <div v-if="successMsg" class="alert alert-success">
      <button type="button" class="close" @click="successMsg = ''">×</button>
      {{ successMsg }}
    </div>
    <div v-if="error" class="alert alert-error">
      <button type="button" class="close" @click="error = ''">×</button>
      {{ error }}
    </div>
  </div>

  <div class="margin">
    <!-- 删除成功后提示 -->
    <template v-if="deleting">
      <h4>
        <i class="fa fa-check"></i>
        <strong>{{ t('ORGANIZATION_DELETING_TITLE') }}</strong>
      </h4>
    </template>

    <!-- 编辑表单 -->
    <template v-else-if="hasOrg">
      <h3>{{ t('EDIT_ORGANIZATION_SUBTITLE') }}</h3>

      <form id="organization_update_form" class="form-horizontal" @submit.prevent="onSubmit">
        <div class="control-group">
          <label class="control-label">{{ t('ORGANIZATION') }}</label>
          <div class="controls">
            <span>{{ org.name }}</span>
          </div>
        </div>

        <div class="control-group">
          <label class="control-label" for="description">{{ t('DESCRIPTION') }}</label>
          <div class="controls">
            <textarea
              id="description"
              v-model="description"
              placeholder="Description"
              rows="3"
            ></textarea>
          </div>
        </div>

        <div class="actions-btn">
          <div class="controls">
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              {{ t('SAVE') }}
            </button>
          </div>
        </div>
      </form>
    </template>
  </div>

  <!-- 删除确认对话框 -->
  <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
    <div class="modal-dialog well">
      <h4 v-html="t('DELETE_ORGANIZATION_QUESTION')"></h4>
      <p>
        <i class="fa fa-warning"></i> {{ t('DELETE_ORGANIZATION_TEXT') }}
      </p>
      <div class="modal-footer">
        <button class="btn btn-default" @click="showDeleteModal = false">{{ t('CANCEL') }}</button>
        <button class="btn btn-danger" @click="doDelete">{{ t('DELETE') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrgStore } from '../store/org.js'

const { t }    = useI18n()
const orgStore = useOrgStore()

const description    = ref('')
const submitting     = ref(false)
const successMsg     = ref('')
const error          = ref('')
const deleting       = ref(false)
const showDeleteModal = ref(false)

const hasOrg = computed(() => orgStore.hasOrg)
const org    = computed(() => orgStore.organization || {})

onMounted(() => {
  description.value = org.value.description || ''
})

async function onSubmit() {
  submitting.value = true
  error.value = ''
  successMsg.value = ''
  try {
    await orgStore.updateOrganization({
      name:        org.value.name,
      description: description.value.trim(),
    })
    successMsg.value = t('ORGANIZATION_UPDATED')
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

async function doDelete() {
  showDeleteModal.value = false
  error.value = ''
  try {
    await orgStore.deleteOrganization()
    deleting.value = true
  } catch (e) {
    error.value = e.message
  }
}
</script>

<style scoped>
/* 简单的模态框覆盖层 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-dialog {
  min-width: 320px;
  max-width: 480px;
  padding: 20px;
}
.modal-footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
