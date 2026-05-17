<template>
  <div class="menu-cards-page">
    <header class="menu-header">
      <h1>
        <i class="fa fa-th-large"></i>
        DocDokuPLM <span class="vue-badge">Vue 版</span>
      </h1>
      <div class="menu-user" v-if="userInfo">
        <span>{{ userInfo.name || userInfo.login }}</span>
        <a href="javascript:void(0)" @click="logout" class="btn btn-link">{{ t('LOG_OUT', { default: '退出' }) }}</a>
      </div>
    </header>

    <p class="compare-notice">
      <i class="fa fa-info-circle"></i>
      {{ t('COMPARE_NOTICE') }}
    </p>

    <div class="cards-grid">
      <div v-for="card in cards" :key="card.id" class="module-card">
        <div class="card-icon"><i :class="card.icon"></i></div>
        <h3>{{ card.title }}</h3>
        <p class="card-desc">{{ card.desc }}</p>
        <div class="card-actions">
          <a
            v-if="card.vueUrl"
            :href="card.vueUrl"
            class="btn btn-vue"
            :data-test="`btn-vue-${card.id}`">
            <i class="fa fa-bolt"></i> {{ t('VUE_VERSION') }}
          </a>
          <span
            v-else
            class="btn btn-vue btn-disabled"
            :title="t('VUE_NOT_READY')"
            :data-test="`btn-vue-disabled-${card.id}`">
            <i class="fa fa-ban"></i> {{ t('VUE_VERSION') }}
          </span>
          <a
            :href="card.legacyUrl"
            class="btn btn-legacy"
            :data-test="`btn-legacy-${card.id}`">
            <i class="fa fa-archive"></i> {{ t('LEGACY_VERSION') }}
          </a>
        </div>
      </div>
    </div>

    <footer class="menu-footer">
      <p>{{ t('VUE_MODULES_COUNT', { count: vueReadyCount, total: cards.length }) }}</p>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../../vue-common/store/app.js'

const { t } = useI18n()
const appStore = useAppStore()
const userInfo = ref(null)
const workspaceId = ref('Workspace_0')

onMounted(async () => {
  if (!localStorage.jwt) {
    window.location.hash = '#/'
    return
  }
  try {
    const res = await fetch(appStore.apiEndPoint + '/accounts/me', {
      headers: { Authorization: 'Bearer ' + localStorage.jwt },
    })
    if (res.status === 401) {
      delete localStorage.jwt
      window.location.hash = '#/?denied=true'
      return
    }
    if (res.ok) {
      userInfo.value = await res.json()
      if (userInfo.value.language && localStorage.locale !== userInfo.value.language) {
        localStorage.locale = userInfo.value.language
      }
    }
  } catch (_) { /* 网络失败不阻塞菜单显示 */ }

  try {
    const res = await fetch(appStore.apiEndPoint + '/workspaces', {
      headers: { Authorization: 'Bearer ' + localStorage.jwt },
    })
    if (res.ok) {
      const data = await res.json()
      const first = (data.allWorkspaces || [])[0]
      if (first && first.id) workspaceId.value = first.id
    }
  } catch (_) { /* 静默 */ }
})

async function logout() {
  try {
    await fetch(appStore.apiEndPoint + '/auth/logout', {
      headers: { Authorization: 'Bearer ' + localStorage.jwt },
    })
  } catch (_) { /* 忽略 */ }
  delete localStorage.jwt
  window.location.hash = '#/?logout=true'
}

const ctx = computed(() => appStore.contextPath || '/')

const cards = computed(() => {
  const ws = workspaceId.value
  const c = ctx.value
  return [
    {
      id: 'workspace', icon: 'fa fa-cogs',
      title: t('CARD_WORKSPACE_TITLE'), desc: t('CARD_WORKSPACE_DESC'),
      vueUrl: `${c}workspace-management-vue/index.html`,
      legacyUrl: `${c}workspace-management/index.html`,
    },
    {
      id: 'change', icon: 'fa fa-exchange',
      title: t('CARD_CHANGE_TITLE'), desc: t('CARD_CHANGE_DESC'),
      vueUrl: `${c}change-management-vue/index.html#/${ws}/workflows`,
      legacyUrl: `${c}change-management/index.html#${ws}/workflows`,
    },
    {
      id: 'document', icon: 'fa fa-file-text-o',
      title: t('CARD_DOCUMENT_TITLE'), desc: t('CARD_DOCUMENT_DESC'),
      vueUrl: `${c}document-management-vue/index.html#/${ws}/folders`,
      legacyUrl: `${c}document-management/index.html#${ws}/folders`,
    },
    {
      id: 'account', icon: 'fa fa-user',
      title: t('CARD_ACCOUNT_TITLE'), desc: t('CARD_ACCOUNT_DESC'),
      vueUrl: `${c}account-management-vue/index.html`,
      legacyUrl: `${c}account-management/index.html`,
    },
    {
      id: 'product-management', icon: 'fa fa-cube',
      title: t('CARD_PRODUCT_MGMT_TITLE'), desc: t('CARD_PRODUCT_MGMT_DESC'),
      vueUrl: null,
      legacyUrl: `${c}product-management/index.html#${ws}/products`,
    },
    {
      id: 'product-structure', icon: 'fa fa-sitemap',
      title: t('CARD_PRODUCT_STRUCT_TITLE'), desc: t('CARD_PRODUCT_STRUCT_DESC'),
      vueUrl: null,
      legacyUrl: `${c}product-structure/index.html#${ws}/products`,
    },
    {
      id: 'organization', icon: 'fa fa-users',
      title: t('CARD_ORG_TITLE'), desc: t('CARD_ORG_DESC'),
      vueUrl: `${c}organization-management-vue/index.html`,
      legacyUrl: `${c}organization-management/index.html`,
    },
    {
      id: 'parts', icon: 'fa fa-puzzle-piece',
      title: t('CARD_PARTS_TITLE'), desc: t('CARD_PARTS_DESC'),
      vueUrl: null,
      legacyUrl: `${c}parts/index.html#${ws}/parts`,
    },
    {
      id: 'visualization', icon: 'fa fa-eye',
      title: t('CARD_VISUAL_TITLE'), desc: t('CARD_VISUAL_DESC'),
      vueUrl: null,
      legacyUrl: `${c}visualization/index.html#${ws}/products`,
    },
    {
      id: 'documents', icon: 'fa fa-folder-open',
      title: t('CARD_DOCS_LEGACY_TITLE'), desc: t('CARD_DOCS_LEGACY_DESC'),
      vueUrl: null,
      legacyUrl: `${c}documents/index.html#${ws}/folders`,
    },
  ]
})

const vueReadyCount = computed(() => cards.value.filter(c => c.vueUrl).length)
</script>

<style scoped>
.menu-cards-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 30px 24px;
  font-family: 'Segoe UI', system-ui, sans-serif;
}
.menu-header {
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid #e1e4e8; padding-bottom: 16px; margin-bottom: 8px;
}
.menu-header h1 { font-size: 24px; margin: 0; color: #2c3e50; }
.menu-header h1 i { margin-right: 10px; color: #42b883; }
.vue-badge {
  display: inline-block; background: #42b883; color: #fff;
  font-size: 12px; padding: 3px 10px; border-radius: 12px;
  margin-left: 8px; vertical-align: middle; font-weight: normal;
}
.menu-user span { margin-right: 12px; color: #586069; }
.compare-notice {
  background: #f1f8ff; border-left: 4px solid #0366d6;
  padding: 10px 16px; margin: 16px 0 24px; color: #24292e; font-size: 14px;
}
.compare-notice i { margin-right: 8px; color: #0366d6; }
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}
.module-card {
  background: #fff; border: 1px solid #e1e4e8; border-radius: 8px;
  padding: 24px; transition: box-shadow 0.2s, transform 0.2s;
  display: flex; flex-direction: column;
}
.module-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-2px); }
.card-icon { font-size: 36px; color: #42b883; margin-bottom: 12px; }
.module-card h3 { margin: 0 0 8px; font-size: 18px; color: #2c3e50; }
.card-desc { color: #586069; font-size: 13px; line-height: 1.5; flex: 1; margin-bottom: 16px; }
.card-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px; border-radius: 4px; font-size: 13px;
  text-decoration: none; border: 1px solid transparent; cursor: pointer;
  transition: background 0.15s;
}
.btn-vue { background: #42b883; color: #fff; border-color: #369870; }
.btn-vue:hover { background: #369870; }
.btn-vue.btn-disabled {
  background: #e1e4e8; color: #959da5; border-color: #d1d5da;
  cursor: not-allowed; opacity: 0.7;
}
.btn-vue.btn-disabled:hover { background: #e1e4e8; }
.btn-legacy { background: #f6f8fa; color: #24292e; border-color: #d1d5da; }
.btn-legacy:hover { background: #e1e4e8; }
.menu-footer {
  margin-top: 32px; padding-top: 16px;
  border-top: 1px solid #e1e4e8;
  text-align: center; color: #586069; font-size: 13px;
}
</style>
