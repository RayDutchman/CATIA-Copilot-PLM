<template>
  <!-- 工作区用户管理，对应原 workspace-users.html + views/workspace-users.js -->
  <div class="actions well">
    <button class="btn btn-default" @click="$router.push('/')">{{ t('BACK') }}</button>

    <!-- 添加用户按钮 / 表单 -->
    <template v-if="!showAddUserForm">
      <button class="btn btn-default" @click="showAddUserForm = true">
        <i class="fa fa-plus"></i> {{ t('ADD_USER') }}
      </button>
    </template>
    <form v-else class="inline form-inline" @submit.prevent="addUser">
      <input v-model="newUserLogin" type="text" required :placeholder="t('LOGIN')" />
      <button class="btn btn-default" type="submit">{{ t('ADD') }}</button>
      <button class="btn btn-default" type="reset" @click="showAddUserForm = false">{{ t('CANCEL') }}</button>
    </form>

    <!-- 创建用户组按钮 / 表单 -->
    <template v-if="!showAddGroupForm">
      <button class="btn btn-default" @click="showAddGroupForm = true">
        <i class="fa fa-plus"></i> {{ t('CREATE_GROUP') }}
      </button>
    </template>
    <form v-else class="inline form-inline" @submit.prevent="addGroup">
      <input v-model="newGroupId" type="text" required :placeholder="t('NAME')" />
      <button class="btn btn-default" type="submit">{{ t('ADD') }}</button>
      <button class="btn btn-default" type="reset" @click="showAddGroupForm = false">{{ t('CANCEL') }}</button>
    </form>

    <!-- 批量操作按钮（有选中用户时显示）-->
    <template v-if="selectedUsers.length > 0">
      <button class="btn btn-default" @click="deleteSelectedUsers">
        <i class="fa fa-remove"></i> {{ t('DELETE') }}
      </button>
      <button class="btn btn-default" @click="disableSelectedUsers">{{ t('DISABLE_USER') }}</button>
      <button class="btn btn-default" @click="enableSelectedUsers">{{ t('ENABLE_USER') }}</button>

      <!-- 移动到用户组下拉 -->
      <span v-if="groupMemberships.length" class="dropdown">
        <button class="btn btn-default dropdown-toggle" type="button" data-toggle="dropdown">
          <i class="fa fa-group"></i> {{ t('MOVE_TO_GROUP') }} <span class="caret"></span>
        </button>
        <ul class="dropdown-menu" role="menu">
          <li v-for="g in groupMemberships" :key="g.memberId">
            <a @click.prevent="moveUsersToGroup(g.memberId)">{{ g.memberId }}</a>
          </li>
        </ul>
      </span>
    </template>

    <!-- 从用户组移除（有选中用户组成员时显示）-->
    <button v-if="selectedGroupUsers.length > 0" class="btn btn-default" @click="removeSelectedFromGroup">
      <i class="fa fa-minus"></i> {{ t('REMOVE_FROM_GROUP') }}
    </button>
  </div>

  <div class="notifications">
    <AlertBanner v-if="error" type="error" :message="error" @close="error = null" />
  </div>

  <div class="margin">
    <div class="workspace-group-container">
      <!-- 用户组列表 -->
      <div
        v-for="group in groupMemberships"
        :key="group.memberId"
        class="workspace-group well well-large"
      >
        <!-- 访问权限开关（对应原版 bootstrapSwitch：绿色=完全访问，橙色=只读） -->
        <div class="pull-right readonly-switch">
          <span
            :class="['readonly-toggle', group.readOnly ? 'toggle-readonly' : 'toggle-full']"
            :title="group.readOnly ? t('FULL_ACCESS') + ' ?' : t('READ_ONLY') + ' ?'"
            @click="setGroupAccess(group.memberId, group.readOnly)"
          >
            {{ group.readOnly ? t('READ_ONLY') : t('FULL_ACCESS') }}
          </span>
        </div>

        <h4><i class="fa fa-users"></i> {{ group.memberId }}</h4>

        <p v-if="!group.users || !group.users.length">{{ t('NO_USER_IN_GROUP') }}</p>

        <table v-else class="group_user_table table table-striped table-condensed">
          <thead>
            <tr>
              <th><input type="checkbox" @change="toggleGroupCheckboxes(group, $event)" /></th>
              <th>{{ t('LOGIN') }}</th>
              <th>{{ t('NAME') }}</th>
              <th>{{ t('EMAIL') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in group.users" :key="user.login">
              <td>
                <input
                  type="checkbox"
                  :data-group-id="group.memberId"
                  :value="user.login"
                  v-model="selectedGroupUsers"
                />
              </td>
              <td>
                <i v-if="user.isCurrentAdmin" class="fa fa-graduation-cap"></i>
                {{ user.login }}
              </td>
              <td>{{ user.name }}</td>
              <td>{{ user.email }}</td>
            </tr>
          </tbody>
        </table>

        <small><a @click.prevent="deleteGroup(group.memberId)" href="#">{{ t('DELETE') }}</a></small>
      </div>
    </div>
  </div>

  <div class="margin">
    <div class="workspace-group-container">
      <div class="workspace-group well well-large">
        <h4><i class="fa fa-user"></i> {{ t('USERS') }}</h4>
        <p v-if="!users.length">{{ t('NO_USER_TO_MANAGE') }}</p>

        <table v-else id="workspace_user_table" class="table table-striped table-condensed">
          <thead>
            <tr>
              <th><input type="checkbox" @change="toggleUserCheckboxes($event)" /></th>
              <th>{{ t('LOGIN') }}</th>
              <th>{{ t('NAME') }}</th>
              <th>{{ t('EMAIL') }}</th>
              <th>{{ t('ACCESS_RIGHTS') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="user in users"
              :key="user.login"
              :class="{ 'no-membership': !user.membership }"
            >
              <td>
                <input type="checkbox" :value="user.login" v-model="selectedUsers" />
              </td>
              <td>
                <i v-if="user.isCurrentAdmin" class="fa fa-graduation-cap"></i>
                {{ user.login }}
              </td>
              <td>{{ user.name }}</td>
              <td>{{ user.email }}</td>
              <td>
                <template v-if="!user.isCurrentAdmin">
                  <template v-if="user.membership">
                    <!-- 访问权限 badge（绿色=完全访问，橙色=只读），点击切换 -->
                    <span
                      :class="['readonly-toggle', user.membership.readOnly ? 'toggle-readonly' : 'toggle-full']"
                      :title="user.membership.readOnly ? t('FULL_ACCESS') + ' ?' : t('READ_ONLY') + ' ?'"
                      @click="setUserAccess(user.login, user.membership.readOnly)"
                    >
                      {{ user.membership.readOnly ? t('READ_ONLY') : t('FULL_ACCESS') }}
                    </span>
                  </template>
                  <a v-else href="#" @click.prevent="enableUser(user.login)">{{ t('ENABLE_USER') }}</a>
                </template>
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
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import { useAuthStore } from '../../vue-common/store/auth.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'

const { t }     = useI18n()
const route     = useRoute()
const api       = useApi()
const authStore = useAuthStore()

const workspaceId = computed(() => route.params.workspaceId)

const users            = ref([])
const memberships      = ref([])
const groupMemberships = ref([])
const error            = ref(null)

const showAddUserForm  = ref(false)
const showAddGroupForm = ref(false)
const newUserLogin     = ref('')
const newGroupId       = ref('')

// 用于批量操作的选中项
const selectedUsers      = ref([])
const selectedGroupUsers = ref([])

const currentLogin = computed(() => authStore.login)

onMounted(() => loadData())

/** 加载用户、成员关系、用户组数据 */
async function loadData() {
  error.value = null
  try {
    // 并行获取：工作区用户列表、用户 memberships、用户组 memberships
    // 正确端点：GET /workspaces/:id/users
    //           GET /workspaces/:id/memberships/users
    //           GET /workspaces/:id/memberships/usergroups
    const [usersData, membershipsData, groupsData] = await Promise.all([
      api.get(`/workspaces/${workspaceId.value}/users`),
      api.get(`/workspaces/${workspaceId.value}/memberships/users`),
      api.get(`/workspaces/${workspaceId.value}/memberships/usergroups`)
    ])

    memberships.value = membershipsData || []

    // 填充用户组及其成员（GET /workspaces/:id/groups/:groupId/users）
    const groups = groupsData || []
    await Promise.all(groups.map(async (group) => {
      try {
        const groupUsers = await api.get(`/workspaces/${group.workspaceId}/groups/${group.memberId}/users`)
        group.users = (groupUsers || []).map(u => ({
          ...u,
          isCurrentAdmin: u.login === currentLogin.value
        }))
      } catch (_) {
        group.users = []
      }
    }))
    groupMemberships.value = groups

    // 为每个用户挂载 membership 信息
    // membershipsData 结构：[{ member: { login, ... }, readOnly: bool, ... }]
    users.value = (usersData || []).map(user => {
      const m = (membershipsData || []).find(ms => ms.member?.login === user.login)
      return {
        ...user,
        isCurrentAdmin: user.login === currentLogin.value,
        membership: m ? { login: user.login, readOnly: m.readOnly } : null
      }
    })

    // 清空选中状态
    selectedUsers.value      = []
    selectedGroupUsers.value = []
  } catch (err) {
    error.value = err.message || 'Failed to load workspace users'
  }
}

/** 添加用户到工作区（PUT /workspaces/:id/add-user body {login}）*/
async function addUser() {
  if (!newUserLogin.value.trim()) return
  try {
    await api.put(`/workspaces/${workspaceId.value}/add-user`, { login: newUserLogin.value.trim() })
    newUserLogin.value    = ''
    showAddUserForm.value = false
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to add user'
  }
}

/** 创建用户组（POST /workspaces/:id/user-group body {id}）*/
async function addGroup() {
  if (!newGroupId.value.trim()) return
  try {
    await api.post(`/workspaces/${workspaceId.value}/user-group`, { id: newGroupId.value.trim() })
    newGroupId.value      = ''
    showAddGroupForm.value = false
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to create group'
  }
}

/** 从工作区移除选中用户（每个用户独立调用 PUT /workspaces/:id/remove-from-workspace body {login}）*/
async function deleteSelectedUsers() {
  // 不允许删除自己
  const toDelete = selectedUsers.value.filter(l => l !== currentLogin.value)
  if (!toDelete.length) return
  try {
    await Promise.all(
      toDelete.map(login =>
        api.put(`/workspaces/${workspaceId.value}/remove-from-workspace`, { login })
      )
    )
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to delete users'
  }
}

/** 启用选中用户（PUT /workspaces/:id/enable-user body {login}）*/
async function enableSelectedUsers() {
  try {
    await Promise.all(
      selectedUsers.value.map(login =>
        api.put(`/workspaces/${workspaceId.value}/enable-user`, { login })
      )
    )
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to enable users'
  }
}

/** 禁用选中用户（PUT /workspaces/:id/disable-user body {login}）*/
async function disableSelectedUsers() {
  try {
    await Promise.all(
      selectedUsers.value.map(login =>
        api.put(`/workspaces/${workspaceId.value}/disable-user`, { login })
      )
    )
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to disable users'
  }
}

/** 单独启用用户（从表格中点击"启用"链接）*/
async function enableUser(login) {
  try {
    await api.put(`/workspaces/${workspaceId.value}/enable-user`, { login })
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to enable user'
  }
}

/** 将选中用户移至指定组（PUT /workspaces/:id/add-user?group=:groupId body {login}，每人单独调用）*/
async function moveUsersToGroup(groupId) {
  try {
    await Promise.all(
      selectedUsers.value.map(login =>
        api.put(`/workspaces/${workspaceId.value}/add-user?group=${groupId}`, { login })
      )
    )
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to move users to group'
  }
}

/** 从组中移除选中用户（PUT /workspaces/:id/remove-from-group/:groupId body {login}）*/
async function removeSelectedFromGroup() {
  try {
    const promises = []
    for (const group of groupMemberships.value) {
      for (const user of (group.users || [])) {
        if (selectedGroupUsers.value.includes(user.login)) {
          promises.push(
            api.put(`/workspaces/${workspaceId.value}/remove-from-group/${group.memberId}`, { login: user.login })
          )
        }
      }
    }
    await Promise.all(promises)
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to remove users from group'
  }
}

/** 设置用户组访问权限（PUT /workspaces/:id/group-access body {memberId, readOnly}）*/
async function setGroupAccess(groupId, fullAccess) {
  try {
    await api.put(`/workspaces/${workspaceId.value}/group-access`, {
      memberId: groupId,
      readOnly: !fullAccess
    })
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to set group access'
  }
}

/** 设置用户访问权限（PUT /workspaces/:id/user-access body {login, membership}）*/
async function setUserAccess(login, fullAccess) {
  try {
    await api.put(`/workspaces/${workspaceId.value}/user-access`, {
      login,
      membership: fullAccess ? 'FULL_ACCESS' : 'READ_ONLY'
    })
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to set user access'
  }
}

/** 删除用户组（DELETE /workspaces/:id/user-group/:groupId）*/
async function deleteGroup(groupId) {
  try {
    await api.del(`/workspaces/${workspaceId.value}/user-group/${groupId}`)
    await loadData()
  } catch (err) {
    error.value = err.message || 'Failed to delete group'
  }
}

function toggleUserCheckboxes(e) {
  if (e.target.checked) {
    selectedUsers.value = users.value.map(u => u.login)
  } else {
    selectedUsers.value = []
  }
}

function toggleGroupCheckboxes(group, e) {
  const logins = (group.users || []).map(u => u.login)
  if (e.target.checked) {
    selectedGroupUsers.value = [...new Set([...selectedGroupUsers.value, ...logins])]
  } else {
    selectedGroupUsers.value = selectedGroupUsers.value.filter(l => !logins.includes(l))
  }
}
</script>

<style scoped>
/* 访问权限切换按钮，模仿 Bootstrap Switch 外观 */
.readonly-toggle {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 3px;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  border: 1px solid transparent;
  transition: opacity 0.15s;
}
.readonly-toggle:hover {
  opacity: 0.8;
}
/* 完全访问：绿色 */
.toggle-full {
  background-color: #5cb85c;
  border-color: #4cae4c;
  color: #fff;
}
/* 只读：橙色 */
.toggle-readonly {
  background-color: #f0ad4e;
  border-color: #eea236;
  color: #fff;
}
/* 卡片右上角定位，对应原版 .group-readonly-switch { position:absolute; top:12px; right:20px } */
.readonly-switch {
  position: absolute;
  top: 12px;
  right: 20px;
}
</style>
