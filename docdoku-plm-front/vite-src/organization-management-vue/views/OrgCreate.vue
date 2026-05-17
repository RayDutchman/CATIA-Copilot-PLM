<template>
  <div class="actions well">
    <router-link to="/" class="btn btn-default">{{ t('BACK') }}</router-link>
  </div>

  <div class="notifications">
    <div v-if="success" class="alert alert-success">
      <button type="button" class="close" @click="success = false">×</button>
      <i class="fa fa-check"></i> <strong>{{ t('ORGANIZATION_CREATED') }}</strong>
    </div>
    <div v-if="error" class="alert alert-error">
      <button type="button" class="close" @click="error = ''">×</button>
      {{ error }}
    </div>
  </div>

  <div class="margin">
    <!-- 创建成功后提示，不再显示表单 -->
    <template v-if="success">
      <h4>
        <i class="fa fa-check"></i>
        <strong>{{ t('ORGANIZATION_CREATED') }}</strong>
      </h4>
    </template>

    <!-- 已有组织时不显示表单 -->
    <template v-else-if="!hasOrg">
      <h3>{{ t('CREATE_ORGANIZATION_SUBTITLE') }}</h3>
      <h3>{{ t('ADMIN') }}</h3>
      <p>{{ t('CREATE_ORGANIZATION_SIDE_TEXT') }}</p>

      <form id="organization_creation_form" class="form-horizontal" @submit.prevent="onSubmit">
        <div class="control-group">
          <label class="control-label" for="organization-name">{{ t('NAME') }}</label>
          <div class="controls">
            <input
              id="organization-name"
              v-model="name"
              type="text"
              name="organization-name"
              maxlength="50"
              size="20"
              required
            />
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
              {{ t('CREATE') }}
            </button>
          </div>
        </div>
      </form>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrgStore } from '../store/org.js'

const { t }    = useI18n()
const orgStore = useOrgStore()

const name        = ref('')
const description = ref('')
const submitting  = ref(false)
const success     = ref(false)
const error       = ref('')

const hasOrg = computed(() => orgStore.hasOrg)

async function onSubmit() {
  if (!name.value.trim()) return
  submitting.value = true
  error.value = ''
  try {
    await orgStore.createOrganization({
      name: name.value.trim(),
      description: description.value.trim(),
    })
    success.value = true
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}
</script>
