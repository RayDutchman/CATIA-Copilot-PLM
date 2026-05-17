/**
 * useDropdown — 纯 Vue 3 下拉菜单状态管理
 * 替代 Bootstrap 2.x data-toggle="dropdown" + jQuery 行为：
 *   - toggle(name)  切换指定下拉（再次点击关闭）
 *   - openMenu      当前打开的下拉名称（null = 全部关闭）
 *   - close()       强制关闭所有下拉
 *
 * 每个使用方在组件根元素上加 @click.stop 阻止冒泡，
 * document click 监听负责点外部关闭（clickOutside 逻辑）。
 *
 * ─── 重要规范（迁移各模块时务必遵守）─────────────────────────────
 * 1. 【顶层 .dropdown】用 Vue 控制：
 *      :class="{ open: openMenu === 'key' }"
 *      @click.stop="toggle('key')"
 *      <ul v-show="openMenu === 'key'" class="dropdown-menu">
 *
 * 2. 【嵌套 .dropdown-submenu】禁止用 Vue 控制，由 Bootstrap 2.x CSS 处理：
 *      .dropdown-submenu:hover > .dropdown-menu { display: block }
 *    即：子菜单 <li> 不加 @click，子菜单 <ul> 不加 v-show。
 *    如果给 <ul> 加了 v-show="false"，inline display:none 会覆盖 CSS hover 规则，
 *    导致子菜单永远不展开。
 * ──────────────────────────────────────────────────────────────────
 */
import { ref, onMounted, onUnmounted } from 'vue'

export function useDropdown() {
  const openMenu = ref(null)

  function toggle(name) {
    openMenu.value = openMenu.value === name ? null : name
  }

  function close() {
    openMenu.value = null
  }

  // 点击任意 .dropdown 之外的区域时关闭所有下拉
  function onDocClick(e) {
    if (!e.target.closest || !e.target.closest('.dropdown')) {
      openMenu.value = null
    }
  }

  onMounted(() => document.addEventListener('click', onDocClick, true))
  onUnmounted(() => document.removeEventListener('click', onDocClick, true))

  return { openMenu, toggle, close }
}
