/**
 * Pinia store：组织管理状态
 * 封装原 common-objects/models/organization.js 的所有 API 调用
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAppStore } from '../../vue-common/store/app.js'

/** 带鉴权头的 fetch 工具 */
function authFetch(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      Authorization: 'Bearer ' + localStorage.jwt,
      ...(options.headers || {}),
    },
  })
}

export const useOrgStore = defineStore('org', () => {
  /** 当前用户的组织（null = 未拥有组织） */
  const organization = ref(null)
  /** 组织成员列表 */
  const members      = ref([])

  const hasOrg       = computed(() => !!organization.value?.name)
  const orgName      = computed(() => organization.value?.name || '')

  /** 加载组织信息（404 表示用户无组织，不抛错） */
  async function fetchOrganization() {
    const appStore = useAppStore()
    const res = await authFetch(appStore.apiEndPoint + '/organizations')
    if (res.status === 404) {
      organization.value = null
      return
    }
    if (!res.ok) throw new Error('Failed to load organization')
    organization.value = await res.json()
  }

  /** 加载成员列表 */
  async function fetchMembers() {
    const appStore = useAppStore()
    const res = await authFetch(appStore.apiEndPoint + '/organizations/members')
    if (!res.ok) throw new Error('Failed to load members')
    members.value = await res.json()
    return members.value
  }

  /** 创建组织 */
  async function createOrganization(data) {
    const appStore = useAppStore()
    const res = await authFetch(appStore.apiEndPoint + '/organizations', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Failed to create organization')
    }
    organization.value = await res.json()
    return organization.value
  }

  /** 更新组织描述 */
  async function updateOrganization(data) {
    const appStore = useAppStore()
    const res = await authFetch(appStore.apiEndPoint + '/organizations', {
      method: 'PUT',
      body: JSON.stringify(data),
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Failed to update organization')
    }
    organization.value = await res.json()
    return organization.value
  }

  /** 删除组织 */
  async function deleteOrganization() {
    const appStore = useAppStore()
    const res = await authFetch(appStore.apiEndPoint + '/organizations', {
      method: 'DELETE',
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Failed to delete organization')
    }
    organization.value = null
    members.value = []
  }

  /** 添加成员 */
  async function addMember(login) {
    const appStore = useAppStore()
    const res = await authFetch(appStore.apiEndPoint + '/organizations/add-member', {
      method: 'PUT',
      body: JSON.stringify({ login }),
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Failed to add member')
    }
    await fetchMembers()
  }

  /** 移除成员（单个） */
  async function removeMember(login) {
    const appStore = useAppStore()
    const res = await authFetch(appStore.apiEndPoint + '/organizations/remove-member', {
      method: 'PUT',
      body: JSON.stringify({ login }),
    })
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Failed to remove member')
    }
  }

  /** 批量移除成员 */
  async function removeMembers(logins) {
    await Promise.all(logins.map(login => removeMember(login)))
    await fetchMembers()
  }

  /** 上移成员 */
  async function moveMemberUp(login) {
    const appStore = useAppStore()
    const res = await authFetch(
      appStore.apiEndPoint + '/organizations/move-member?direction=up',
      { method: 'PUT', body: JSON.stringify({ login }) }
    )
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Failed to move member up')
    }
    await fetchMembers()
  }

  /** 下移成员 */
  async function moveMemberDown(login) {
    const appStore = useAppStore()
    const res = await authFetch(
      appStore.apiEndPoint + '/organizations/move-member?direction=down',
      { method: 'PUT', body: JSON.stringify({ login }) }
    )
    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || 'Failed to move member down')
    }
    await fetchMembers()
  }

  return {
    organization, members, hasOrg, orgName,
    fetchOrganization, fetchMembers,
    createOrganization, updateOrganization, deleteOrganization,
    addMember, removeMembers, moveMemberUp, moveMemberDown,
  }
})
