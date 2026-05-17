<template>
  <div class="actions well">
    <router-link to="/" class="btn btn-default">{{ t('BACK') }}</router-link>

    <button
      v-if="isOwner"
      class="btn btn-default"
      @click="showAddForm = !showAddForm"
    >
      <i class="fa fa-plus"></i> {{ t('ADD_USER') }}
    </button>

    <!-- 添加成员内联表单 -->
    <form
      v-if="showAddForm"
      id="organization-add-user-form"
      class="inline form-inline"
      @submit.prevent="onAddUser"
    >
      <input
        v-model="newLogin"
        type="text"
        required
        :placeholder="t('LOGIN')"
      />
      <button type="submit" class="btn btn-default">{{ t('ADD') }}</button>
      <button type="reset" class="btn btn-default" @click="cancelAddForm">{{ t('CANCEL') }}</button>
    </form>

    <button
      v-if="isOwner && selectedLogins.length > 0"
      class="btn btn-default"
      @click="deleteSelected"
    >
      <i class="fa fa-remove"></i> {{ t('DELETE') }}
    </button>

    <button
      v-if="isOwner && selectedLogins.length === 1"
      class="btn btn-default"
      @click="moveUp"
    >
      <i class="fa fa-chevron-up"></i> {{ t('MOVE_UP') }}
    </button>

    <button
      v-if="isOwner && selectedLogins.length === 1"
      class="btn btn-default"
      @click="moveDown"
    >
      <i class="fa fa-chevron-down"></i> {{ t('MOVE_DOWN') }}
    </button>
  </div>

  <div class="notifications">
    <div v-if="error" class="alert alert-error">
      <button type="button" class="close" @click="error = ''">×</button>
      {{ error }}
    </div>
  </div>

  <div class="margin">
    <div class="organization-group-container">
      <div class="organization-group well well-large">
        <h4>
          <i class="fa fa-user"></i> {{ t('MEMBERS') }}
        </h4>

        <table
          id="organization_user_table"
          class="table table-striped table-condensed"
        >
          <thead>
            <tr>
              <th v-if="isOwner">
                <input
                  type="checkbox"
                  :checked="allChecked"
                  @change="toggleAll"
                />
              </th>
              <th>{{ t('NAME') }}</th>
              <th>{{ t('EMAIL') }}</th>
            </tr>
          </thead>
          <tbody class="items">
            <tr v-for="member in members" :key="member.login">
              <td v-if="isOwner">
                <input
                  type="checkbox"
                  :value="member.login"
                  v-model="selectedLogins"
                />
              </td>
              <td>{{ member.name }}</td>
              <td>{{ member.email }}</td>
            </tr>
            <tr v-if="members.length === 0">
              <td :colspan="isOwner ? 3 : 2" class="muted" style="text-align:center;">
                —
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../vue-common/store/auth.js'
import { useOrgStore }  from '../store/org.js'

const { t }     = useI18n()
const authStore = useAuthStore()
const orgStore  = useOrgStore()

const error          = ref('')
const showAddForm    = ref(false)
const newLogin       = ref('')
const selectedLogins = ref([])

const members  = computed(() => orgStore.members)
const isOwner  = computed(() =>
  !!orgStore.organization && authStore.login === orgStore.organization.owner
)
const allChecked = computed(() =>
  members.value.length > 0 && selectedLogins.value.length === members.value.length
)

onMounted(async () => {
  try {
    await orgStore.fetchMembers()
  } catch (e) {
    error.value = e.message
  }
})

function toggleAll(e) {
  selectedLogins.value = e.target.checked
    ? members.value.map(m => m.login)
    : []
}

function cancelAddForm() {
  showAddForm.value = false
  newLogin.value = ''
}

async function onAddUser() {
  const login = newLogin.value.trim()
  if (!login) return
  error.value = ''
  try {
    await orgStore.addMember(login)
    cancelAddForm()
    selectedLogins.value = []
  } catch (e) {
    error.value = e.message
  }
}

async function deleteSelected() {
  // 不能删除自己
  const toDelete = selectedLogins.value.filter(l => l !== authStore.login)
  if (!toDelete.length) return
  error.value = ''
  try {
    await orgStore.removeMembers(toDelete)
    selectedLogins.value = []
  } catch (e) {
    error.value = e.message
  }
}

async function moveUp() {
  if (selectedLogins.value.length !== 1) return
  error.value = ''
  try {
    await orgStore.moveMemberUp(selectedLogins.value[0])
  } catch (e) {
    error.value = e.message
  }
}

async function moveDown() {
  if (selectedLogins.value.length !== 1) return
  error.value = ''
  try {
    await orgStore.moveMemberDown(selectedLogins.value[0])
  } catch (e) {
    error.value = e.message
  }
}
</script>
