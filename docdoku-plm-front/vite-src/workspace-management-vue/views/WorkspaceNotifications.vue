<template>
  <!-- 工作区通知设置，对应原 workspace-notifications.html + views/workspace-notifications.js -->
  <div class="actions well">
    <button class="btn btn-default" @click="$router.push('/')">{{ t('BACK') }}</button>
    <button class="btn btn-primary" style="margin-left:4px;" @click="openOptions">
      {{ t('OPTIONS') }}
    </button>
  </div>

  <div class="notifications">
    <AlertBanner v-if="error" type="error" :message="error" @close="error = null" />
    <AlertBanner v-if="!tags.length" type="info" :message="t('NO_TAGS_YET')" />
  </div>

  <div class="margin">
    <!-- 用户组通知设置 -->
    <div class="workspace-group-container">
      <div class="workspace-group well well-large">
        <h4><i class="fa fa-users"></i> {{ t('GROUPS') }}</h4>
        <p v-if="!groupsToManage.length">{{ t('NO_GROUP_TO_MANAGE') }}</p>
        <table v-else id="workspace_group_table" class="table table-striped table-condensed">
          <thead>
            <tr>
              <th></th>
              <th>{{ t('NAME') }}</th>
              <th>{{ t('ACCESS_RIGHTS') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="group in groupsToManage" :key="group.memberId">
              <td><input type="checkbox" /></td>
              <td>{{ group.memberId }}</td>
              <td>{{ group.readOnly ? t('READ_ONLY') : t('FULL_ACCESS') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 用户通知设置 -->
    <div class="workspace-group-container">
      <div class="workspace-group well well-large">
        <h4><i class="fa fa-user"></i> {{ t('USERS') }}</h4>
        <p v-if="!usersToManage.length">{{ t('NO_USER_TO_MANAGE') }}</p>
        <table v-else id="workspace_user_table" class="table table-striped table-condensed">
          <thead>
            <tr>
              <th></th>
              <th>{{ t('LOGIN') }}</th>
              <th>{{ t('NAME') }}</th>
              <th>{{ t('EMAIL') }}</th>
              <th>{{ t('ACCESS_RIGHTS') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in usersToManage" :key="user.login">
              <td><input type="checkbox" /></td>
              <td>{{ user.login }}</td>
              <td>{{ user.name }}</td>
              <td>{{ user.email }}</td>
              <td>{{ user.readOnly ? t('READ_ONLY') : t('FULL_ACCESS') }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ── 通知选项弹窗（对应原 notification-options.html） ────────────────── -->
  <Teleport to="body">
    <div v-if="showOptions" class="modal-backdrop fade in" style="z-index:1040;"></div>

    <div
      v-if="showOptions"
      id="notification_options_modal"
      class="modal fade in"
      tabindex="-1"
      role="dialog"
      style="display:block; z-index:1050;"
    >
      <div class="modal-header">
        <i class="fa fa-cog"></i>
        <button type="button" class="close" @click="closeOptions" aria-hidden="true">×</button>
        <h3>{{ t('OPTIONS') }}</h3>
      </div>

      <div class="modal-body">
        <div class="notifications">
          <AlertBanner v-if="optionsError"   type="error"   :message="optionsError"   @close="optionsError = null" />
          <AlertBanner v-if="optionsSaved"   type="success" :message="t('SAVED')"     @close="optionsSaved = false" />
        </div>

        <!-- Tab 导航 -->
        <ul class="nav nav-tabs">
          <li :class="{ active: activeTab === 'email' }">
            <a href="#" @click.prevent="activeTab = 'email'">{{ t('EMAIL') }}</a>
          </li>
          <li :class="{ active: activeTab === 'hooks' }">
            <a href="#" @click.prevent="switchToHooks">{{ t('HOOKS') }}</a>
          </li>
        </ul>

        <div class="tab-content" style="padding-top:12px;">
          <!-- Email tab -->
          <div v-show="activeTab === 'email'" class="tab-pane active">
            <div class="control-group">
              <label class="control-label" for="send-emails">
                {{ t('ENABLE_EMAIL_NOTIFICATIONS') }}
              </label>
              <div class="controls">
                <input
                  id="send-emails"
                  v-model="optionsSendEmails"
                  type="checkbox"
                />
              </div>
            </div>
          </div>

          <!-- Hooks tab（对应原版 hooks-manager.html + hooks-item.html） -->
          <div v-show="activeTab === 'hooks'" class="tab-pane">
            <div class="hooks-container">

              <!-- 加载中 -->
              <p v-if="hooksLoading" class="muted">Loading…</p>

              <!-- hook 列表 -->
              <div
                v-for="(hook, idx) in hooks"
                :key="hook._cid"
                class="well"
                style="margin-bottom:12px;"
              >
                <!-- 名称 -->
                <div class="control-group">
                  <label class="control-label"><strong>{{ t('NAME') }}</strong></label>
                  <div class="controls">
                    <input
                      v-model="hook.name"
                      type="text"
                      :placeholder="t('NAME')"
                    />
                  </div>
                </div>

                <!-- 启用 -->
                <div class="control-group">
                  <label class="control-label"><strong>{{ t('ENABLE_HOOK') }}</strong></label>
                  <div class="controls">
                    <input v-model="hook.active" type="checkbox" />
                  </div>
                </div>

                <!-- 类型选择 -->
                <div class="control-group">
                  <label class="control-label"><strong>{{ t('TYPE') }}</strong></label>
                  <div class="controls">
                    <select v-model="hook.appName" @change="onHookTypeChange(hook)">
                      <option value="SIMPLEWEBHOOK">SIMPLEWEBHOOK</option>
                      <option value="SNSWEBHOOK">SNSWEBHOOK</option>
                    </select>
                  </div>
                </div>

                <!-- 参数（根据类型动态渲染） -->
                <div class="control-group">
                  <label class="control-label"><strong>{{ t('PARAMETERS') }}</strong></label>
                  <div class="controls specific-hook-configuration">
                    <template v-if="hook.appName === 'SIMPLEWEBHOOK'">
                      <!-- method: GET/POST/PUT -->
                      <select :value="hookParam(hook, 'method')" @change="setHookParam(hook, 'method', $event.target.value)" style="margin-bottom:4px; display:block;">
                        <option value="GET">GET</option>
                        <option value="POST">POST</option>
                        <option value="PUT">PUT</option>
                      </select>
                      <!-- uri -->
                      <input
                        type="text"
                        placeholder="uri"
                        :value="hookParam(hook, 'uri')"
                        @input="setHookParam(hook, 'uri', $event.target.value)"
                        style="margin-bottom:4px; display:block; width:100%;"
                      />
                      <!-- authorization -->
                      <input
                        type="text"
                        placeholder="authorization"
                        :value="hookParam(hook, 'authorization')"
                        @input="setHookParam(hook, 'authorization', $event.target.value)"
                        style="display:block; width:100%;"
                      />
                    </template>

                    <template v-else-if="hook.appName === 'SNSWEBHOOK'">
                      <!-- region / topicArn / awsAccount / awsSecret -->
                      <input
                        v-for="field in ['region', 'topicArn', 'awsAccount', 'awsSecret']"
                        :key="field"
                        type="text"
                        :placeholder="field"
                        :value="hookParam(hook, field)"
                        @input="setHookParam(hook, field, $event.target.value)"
                        style="margin-bottom:4px; display:block; width:100%;"
                      />
                    </template>
                  </div>
                </div>

                <!-- 操作 -->
                <div class="control-group">
                  <label class="control-label">{{ t('ACTIONS') }}</label>
                  <div class="controls">
                    <button
                      type="button"
                      class="btn btn-default remove-hook"
                      @click="removeHook(idx)"
                    >
                      {{ t('DELETE') }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- 添加按钮（对应原版 .add-hook） -->
              <button type="button" class="btn btn-primary add-hook" @click="addHook">
                {{ t('ADD') }}
              </button>

            </div>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-default" @click="closeOptions">{{ t('CLOSE') }}</button>
        <button class="btn btn-primary" :disabled="optionsSaving" @click="saveOptions">
          {{ optionsSaving ? '…' : t('SAVE') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useApi } from '../../vue-common/composables/useApi.js'
import AlertBanner from '../../vue-common/components/AlertBanner.vue'

const { t }  = useI18n()
const route  = useRoute()
const api    = useApi()

const workspaceId = computed(() => route.params.workspaceId)

// 主页面状态
const error          = ref(null)
const tags           = ref([])
const groupsToManage = ref([])
const usersToManage  = ref([])

// 弹窗状态
const showOptions       = ref(false)
const activeTab         = ref('email')
const optionsSendEmails = ref(false)
const optionsError      = ref(null)
const optionsSaved      = ref(false)
const optionsSaving     = ref(false)

// ── Hooks 状态 ─────────────────────────────────────────────
const hooks        = ref([])   // 当前编辑中的 hook 列表
const hooksToDelete= ref([])   // 待删除的已有 hook（有 id 的）
const hooksLoading = ref(false)
let   _cidCounter  = 0

/** 生成前端临时 cid（无 id 时用于 v-for key） */
function nextCid() { return ++_cidCounter }

/** 获取 hook 某参数的当前值 */
function hookParam(hook, name) {
  const p = (hook.parameters || []).find(x => x.name === name)
  return p ? p.value : ''
}

/** 设置 hook 某参数值（深更新 parameters 数组） */
function setHookParam(hook, name, value) {
  const params = hook.parameters ? [...hook.parameters] : []
  const idx = params.findIndex(x => x.name === name)
  if (idx >= 0) {
    params[idx] = { name, value }
  } else {
    params.push({ name, value })
  }
  hook.parameters = params
}

/** 切换 hook 类型时重置参数为对应类型默认值 */
function onHookTypeChange(hook) {
  if (hook.appName === 'SIMPLEWEBHOOK') {
    hook.parameters = [
      { name: 'method',        value: 'POST'   },
      { name: 'uri',           value: 'http://' },
      { name: 'authorization', value: ''        },
    ]
  } else if (hook.appName === 'SNSWEBHOOK') {
    hook.parameters = [
      { name: 'region',     value: '' },
      { name: 'topicArn',   value: '' },
      { name: 'awsAccount', value: '' },
      { name: 'awsSecret',  value: '' },
    ]
  }
}

/** 添加新 hook（默认 SIMPLEWEBHOOK，对应原版 addNewHookItem） */
function addHook() {
  hooks.value.push({
    _cid:       nextCid(),
    name:       'New hook',
    appName:    'SIMPLEWEBHOOK',
    active:     true,
    parameters: [
      { name: 'method',        value: 'POST'    },
      { name: 'uri',           value: 'http://' },
      { name: 'authorization', value: ''        },
    ],
  })
}

/** 从列表移除 hook（若有 id 则加入待删除队列） */
function removeHook(idx) {
  const hook = hooks.value[idx]
  if (hook.id) {
    hooksToDelete.value.push(hook.id)
  }
  hooks.value.splice(idx, 1)
}

// ── 生命周期 ──────────────────────────────────────────────
onMounted(async () => {
  // 原版数据源：
  //   tags           → /workspaces/:id/tags
  //   groupsToManage → /workspaces/:id/memberships/usergroups  { memberId, readOnly }
  //   usersToManage  → /workspaces/:id/users 联立 /memberships/users（取 readOnly）
  const [tagsData, groupMembershipsData, usersData, userMembershipsData] = await Promise.allSettled([
    api.get(`/workspaces/${workspaceId.value}/tags`),
    api.get(`/workspaces/${workspaceId.value}/memberships/usergroups`),
    api.get(`/workspaces/${workspaceId.value}/users`),
    api.get(`/workspaces/${workspaceId.value}/memberships/users`),
  ])

  if (tagsData.status === 'fulfilled') {
    tags.value = tagsData.value || []
  }

  if (groupMembershipsData.status === 'fulfilled') {
    // /memberships/usergroups 返回 [{memberId, readOnly, workspaceId}, ...]
    groupsToManage.value = groupMembershipsData.value || []
  }

  if (usersData.status === 'fulfilled') {
    const users       = usersData.value || []
    // /memberships/users 返回 [{memberId, readOnly, workspaceId}, ...]
    const memberships = userMembershipsData.status === 'fulfilled'
      ? (userMembershipsData.value || [])
      : []
    // 联立：为每个 user 附加 readOnly 字段
    usersToManage.value = users.map(u => {
      const m = memberships.find(m => m.memberId === u.login)
      return { ...u, readOnly: m ? m.readOnly : false }
    })
  }
})

// ── 弹窗方法 ──────────────────────────────────────────────

async function openOptions() {
  optionsError.value = null
  optionsSaved.value = false
  activeTab.value    = 'email'
  showOptions.value  = true
  try {
    const data = await api.get(`/workspaces/${workspaceId.value}/back-options`)
    optionsSendEmails.value = !!data?.sendEmails
  } catch (err) {
    optionsError.value = err.message || 'Failed to load options'
  }
}

/** 切换到 Hooks tab，同时加载 webhooks */
async function switchToHooks() {
  activeTab.value = 'hooks'
  if (hooks.value.length || hooksLoading.value) return
  hooksLoading.value = true
  try {
    const data = await api.get(`/workspaces/${workspaceId.value}/webhooks`)
    hooks.value = (data || []).map(h => ({
      ...h,
      _cid: nextCid(),
      parameters: h.parameters || [],
    }))
    hooksToDelete.value = []
  } catch (err) {
    optionsError.value = err.message || 'Failed to load webhooks'
  } finally {
    hooksLoading.value = false
  }
}

function closeOptions() {
  showOptions.value = false
}

/** 保存：back-options (sendEmails) + 所有 hooks 的新建/更新/删除 */
async function saveOptions() {
  optionsSaving.value = true
  optionsError.value  = null
  optionsSaved.value  = false
  try {
    // 1. 保存邮件选项
    await api.put(`/workspaces/${workspaceId.value}/back-options`, {
      sendEmails: optionsSendEmails.value,
    })

    // 2. 保存每个 hook（有 id → PUT，无 id → POST）
    if (activeTab.value === 'hooks' || hooks.value.length) {
      const savePromises = hooks.value.map(hook => {
        const { _cid, ...payload } = hook
        if (payload.id) {
          return api.put(`/workspaces/${workspaceId.value}/webhooks/${payload.id}`, payload)
        } else {
          return api.post(`/workspaces/${workspaceId.value}/webhooks`, payload)
        }
      })

      // 3. 删除标记为删除的 hook
      const deletePromises = hooksToDelete.value.map(id =>
        api.del(`/workspaces/${workspaceId.value}/webhooks/${id}`)
      )

      await Promise.all([...savePromises, ...deletePromises])
      hooksToDelete.value = []

      // 保存后重新加载以获取服务器分配的 id
      const refreshed = await api.get(`/workspaces/${workspaceId.value}/webhooks`)
      hooks.value = (refreshed || []).map(h => ({
        ...h,
        _cid: nextCid(),
        parameters: h.parameters || [],
      }))
    }

    optionsSaved.value = true
  } catch (err) {
    optionsError.value = err.message || 'Failed to save options'
  } finally {
    optionsSaving.value = false
  }
}
</script>
