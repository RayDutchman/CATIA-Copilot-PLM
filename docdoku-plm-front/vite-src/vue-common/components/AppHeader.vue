<template>
  <!-- 复用原有 Bootstrap 2.x Header 样式，class 与原 header.html 完全一致 -->
  <a
    id="collapseButton"
    class="Header-collapseBtn btn btn-navbar btn-primary"
    @click.stop="toggle('mobile')"
  >
    <span class="icon-bar"></span>
    <span class="icon-bar"></span>
    <span class="icon-bar"></span>
  </a>

  <div class="HeaderContent Header-content navbar-inner">
    <a class="Brand" :href="contextPath + (isLoggedIn ? 'workspace-management/' : '') + 'index.html#'">
      <img class="Brand-logo" alt="docdoku_plm" :src="contextPath + 'images/docdokuplm_logo.png'" />
      <span class="Brand-name">DocDoku<strong>PLM</strong></span>
    </a>

    <!-- 已登录 -->
    <div v-if="isLoggedIn" :class="['nav-collapse', 'collapse', openMenu === 'mobile' ? 'in' : '']">
      <div class="HeaderFluidContent container-fluid">
        <!-- 左侧：工作区下拉（非 admin） -->
        <ul v-if="!isAdmin" class="BreadcrumbMenu nav header-menu">
          <li
            class="BreadcrumbMenuItem BreadcrumbMenu-item dropdown pull-left"
            id="workspace_container"
            :class="{ open: openMenu === 'workspace' }"
            @click.stop="toggle('workspace')"
          >
            <a class="BreadcrumbMenuItem-link dropdown-toggle">
              <i class="fa fa-home"></i>
              {{ t('MY_WORKSPACES') }}
              <span v-if="currentWorkspace">: {{ currentWorkspace }}</span>
            </a>
            <ul v-show="openMenu === 'workspace'" class="BreadcrumbMenuList dropdown-menu">
              <!-- 管理员工作区（子菜单由 Bootstrap CSS hover 展开，不用 Vue 控制） -->
              <li
                v-for="ws in administratedWorkspaces"
                :key="ws.id"
                class="BreadcrumbSubMenuItem dropdown-submenu visible-desktop"
              >
                <a>
                  <i v-if="ws.id === currentWorkspace" class="fa fa-check"></i>
                  <i class="fa fa-graduation-cap"></i> <span>{{ ws.id }}</span>
                </a>
                <!-- 不加 v-show：让 .dropdown-submenu:hover > .dropdown-menu { display:block } 生效 -->
                <ul class="BreadcrumbSubMenuList dropdown-menu">
                  <li><a :href="contextPath + 'document-management/index.html#' + ws.id + '/folders'">{{ t('DOCUMENTS') }}</a></li>
                  <li><a :href="contextPath + 'product-management/index.html#' + ws.id + '/products'">{{ t('PRODUCTS') }}</a></li>
                  <li><a :href="contextPath + 'change-management/index.html#' + ws.id + '/workflows'">{{ t('CHANGES') }}</a></li>
                  <li><a :href="contextPath + 'workspace-management/index.html#/workspace/' + ws.id + '/edit'">{{ t('WORKSPACE_MANAGEMENT') }}</a></li>
                </ul>
              </li>
              <!-- 普通成员工作区（同上：子菜单 CSS hover 展开） -->
              <li
                v-for="ws in nonAdministratedWorkspaces"
                :key="ws.id"
                class="BreadcrumbSubMenuItem dropdown-submenu visible-desktop"
              >
                <a>
                  <i v-if="ws.id === currentWorkspace" class="fa fa-check"></i>
                  <i class="fa fa-user"></i> <span>{{ ws.id }}</span>
                </a>
                <ul class="BreadcrumbSubMenuList dropdown-menu">
                  <li><a :href="contextPath + 'document-management/index.html#' + ws.id + '/folders'">{{ t('DOCUMENTS') }}</a></li>
                  <li><a :href="contextPath + 'product-management/index.html#' + ws.id + '/products'">{{ t('PRODUCTS') }}</a></li>
                  <li><a :href="contextPath + 'change-management/index.html#' + ws.id + '/workflows'">{{ t('CHANGES') }}</a></li>
                </ul>
              </li>
            </ul>
          </li>
        </ul>

        <!-- 右侧用户菜单 -->
        <ul class="HeaderMenu nav header-menu pull-right">
          <!-- CoWorkers 下拉（非 admin 才显示） -->
          <CoWorkers v-if="!isAdmin" :openKey="openMenu" @toggle="toggle" />

          <!-- 账户名下拉 -->
          <li
            class="HeaderMenu-item dropdown"
            :class="{ open: openMenu === 'user' }"
            @click.stop="toggle('user')"
          >
            <a href="#" class="dropdown-toggle">
              <i class="fa fa-user"></i>
              {{ userName }}
              <span class="caret"></span>
            </a>
            <ul v-show="openMenu === 'user'" class="dropdown-menu">
              <li>
                <a :href="contextPath + 'account-management/index.html'">
                  <i class="fa fa-user"></i> {{ t('MY_ACCOUNT') }}
                </a>
              </li>
              <li v-if="!isAdmin">
                <a :href="contextPath + 'organization-management/index.html'">
                  <i class="fa fa-building-o"></i> {{ t('MY_ORGANIZATION') }}
                </a>
              </li>
              <li>
                <a :href="contextPath + 'workspace-management/index.html'">
                  <i class="fa fa-cog"></i> {{ t('WORKSPACES_ADMINISTRATION') }}
                </a>
              </li>
              <li class="divider"></li>
              <li>
                <a :href="contextPath + 'download/index.html'">
                  <i class="fa fa-download"></i> {{ t('DOWNLOAD_DPLM_CLIENT') }}
                </a>
              </li>
              <li>
                <a href="http://www.docdokuplm.com/" target="_blank">
                  <i class="fa fa-question"></i> {{ t('ABOUT_DOCDOKUPLM') }}
                </a>
              </li>
              <li class="divider"></li>
              <li id="logout_link">
                <a @click.prevent="authStore.logout()" style="cursor:pointer">
                  <i class="fa fa-power-off"></i> {{ t('LOGOUT') }}
                </a>
              </li>
            </ul>
          </li>
        </ul>
      </div>
    </div>

    <!-- 未登录 -->
    <div v-else class="nav-collapse collapse">
      <div class="HeaderFluidContent container-fluid offline-menu">
        <ul class="HeaderMenu nav header-menu">
          <li><a :href="contextPath + '#'"><i class="fa fa-home"></i> {{ t('HOME_PAGE') }}</a></li>
          <li><a href="http://www.docdokuplm.com/" target="_blank"><i class="fa fa-cloud"></i> {{ t('OFFICIAL_SITE') }}</a></li>
          <li><a :href="contextPath + 'download/index.html'"><i class="fa fa-download"></i> {{ t('DOWNLOAD_DPLM_CLIENT') }}</a></li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAppStore } from '../store/app.js'
import { useAuthStore } from '../store/auth.js'
import { useDropdown } from '../composables/useDropdown.js'
import CoWorkers from './CoWorkers.vue'

// 父组件可传入 workspaceId prop（推荐，避免 Teleport 内 useRoute 的响应式问题）
// 未传时回退到解析 window.location.hash
const props = defineProps({
  workspaceId: { type: String, default: '' }
})

const { t } = useI18n()
const appStore  = useAppStore()
const authStore = useAuthStore()
const { openMenu, toggle } = useDropdown()

const contextPath             = computed(() => appStore.contextPath)
const isLoggedIn              = computed(() => authStore.isLoggedIn)
const isAdmin                 = computed(() => authStore.isAdmin)
const userName                = computed(() => authStore.userName)
const administratedWorkspaces = computed(() => authStore.workspaces.administratedWorkspaces || [])
const nonAdministratedWorkspaces = computed(() => authStore.workspaces.nonAdministratedWorkspaces || [])

// 当前工作区：优先使用 prop，回退到 hash 解析（兼容旧模块格式）
const currentWorkspace = computed(() => {
  if (props.workspaceId) return props.workspaceId
  const hash = window.location.hash
  // workspace-management 格式：#/workspace/WorkspaceId/...
  let m = hash.match(/^#\/workspace\/([^/]+)/)
  if (m) return m[1]
  // 其他模块格式：#WorkspaceId/...
  m = hash.match(/^#([^/]+)/)
  return m ? m[1] : ''
})

// 对应 Backbone HeaderView 中的 $el.show().addClass('loaded')
// CSS 默认 opacity:0，加 loaded class 后 transition 到 opacity:1
onMounted(() => {
  const el = document.getElementById('header')
  if (el) el.classList.add('loaded')
})
</script>
