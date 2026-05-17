# Playwright Intense 自测报告 — Vue 前端现代化

**测试时间**：2026-05-18  
**环境**：`http://localhost:8000`  
**工作区**：`Workspace_0`  
**截图目录**：`playwright-visual-diff/`

## 测试方法

本次按用户要求补做了真实浏览器自测：

1. 用 Playwright 逐项打开 Vue 版与原版页面。
2. 对每个核心页面保存截图，便于人工视觉对比。
3. 不仅检查 console，也检查页面内容、路由跳转、关键交互入口、只读权限表现。
4. 对 `MANUAL_TEST_CHECKLIST.md` 中可自动验证的项目执行浏览器操作。
5. 写操作中涉及删除的数据破坏性操作只验证确认 modal，不执行最终确认。

## 截图矩阵

截图文件位于 `playwright-visual-diff/`：

| 编号 | 页面 | Vue 截图 | 原版截图 | 结果 |
|---|---|---|---|---|
| 01 | main 菜单 | `01-main-menu-vue.png` | `01-main-menu-legacy.png` | 已对比 |
| 02 | account 首页 | `02-account-home-vue.png` | `02-account-home-legacy.png` | 已对比 |
| 03 | workspace 首页 | `03-workspace-home-vue.png` | `03-workspace-home-legacy.png` | 已对比 |
| 04 | workspace dashboard | `04-workspace-dashboard-vue.png` | `04-workspace-dashboard-legacy.png` | 已对比 |
| 05 | change workflows | `05-change-workflows-vue.png` | `05-change-workflows-legacy.png` | 已对比 |
| 06 | change issues | `06-change-issues-vue.png` | `06-change-issues-legacy.png` | 已对比 |
| 07 | change requests | `07-change-requests-vue.png` | `07-change-requests-legacy.png` | 已对比 |
| 08 | change orders | `08-change-orders-vue.png` | `08-change-orders-legacy.png` | 已对比 |
| 09 | document folders | `09-document-folders-vue.png` | `09-document-folders-legacy.png` | 已对比 |
| 10 | document templates | `10-document-templates-vue.png` | `10-document-templates-legacy.png` | 已对比 |
| 11 | document baselines | `11-document-baselines-vue.png` | `11-document-baselines-legacy.png` | 已对比 |
| 12 | document checked out | `12-document-checkedouts-vue.png` | `12-document-checkedouts-legacy.png` | 已对比 |
| 13 | document search | `13-document-search-vue.png` | `13-document-search-legacy.png` | 已对比 |
| 14 | document tags | `14-document-tags-vue.png` | `14-document-tags-legacy.png` | 已对比 |
| 15 | document tasks | `15-document-tasks-vue.png` | `15-document-tasks-legacy.png` | 已对比 |
| 16 | organization home | `16-organization-home-vue.png` | `16-organization-home-legacy.png` | 已对比 |
| 17 | organization members | `17-organization-members-vue.png` | `17-organization-members-legacy.png` | 已对比 |
| 18 | organization edit | `18-organization-edit-vue.png` | `18-organization-edit-legacy.png` | 已对比 |

## 关键交互验证

| 项目 | 截图/证据 | 结果 |
|---|---|---|
| 错误密码登录显示错误 | `19-main-wrong-password.png` | 通过 |
| admin 登录进入 Vue 菜单并写入 JWT | `25-admin-menu-after-final-fixes.png` | 通过 |
| 文档搜索 `DS` 返回结果 | `26-document-search-ds-final.png` | 通过，返回 `DS-0001`、`DS-0003` |
| 组织删除按钮弹出确认 modal，不执行删除 | `27-organization-delete-modal-final.png` | 通过 |
| carol 访问 change issues 只读无新建/删除按钮 | `28-change-issues-carol-final.png` | 通过 |
| alice/corol 无组织时停留 Vue organization 页面 | `32-organization-alice-home-after-204-fix.png`、`32-organization-carol-home-after-204-fix.png` | 通过 |

## 本次 intense 自测发现并修复的问题

| ID | 问题 | 根因 | 修复 |
|---|---|---|---|
| P-01 | 某些状态下 Vue 登录页请求 `/main-vue/undefined/auth/login` | submit 时 `appStore.apiEndPoint` 可能还未初始化 | `LoginForm.vue` 中 submit 前保证重新加载 server properties |
| P-02 | organization edit 删除按钮不弹出确认框 | 点击处理不稳定，函数中转无必要 | `OrgEdit.vue` 改为模板内联设置 `showDeleteModal = true` |
| P-03 | carol 只读用户在 change issues 仍看到新建/删除按钮 | Vue 版未按工作区管理员权限隐藏写操作 | `ChangeItemList.vue` 增加 `canWrite`，非管理员隐藏 actions |
| P-04 | alice/carol 访问 organization-vue 会跳到 workspace 原版 | `/organizations` 返回 204 No Content，被 Vue store 当 JSON 解析导致 bootstrap 失败 | `org.js` 将 204/404 都视作“无组织”正常状态 |

## 仍需人工执行的项目

以下项目会修改真实数据，自动测试只验证入口和确认框，未执行最终写入/删除：

1. account 保存账户信息。
2. workspace 创建/编辑工作区、成员管理。
3. document 签出/签入/取消签出、附件上传、创建文档。
4. change 创建 Issue/Request/Order。
5. organization 创建组织、添加/删除成员、移动成员顺序、真正删除组织。

## 备注

- Vue 与原版路由格式不同：Vue 使用 `#/Workspace_0/...`，原版 Backbone 使用 `#Workspace_0/...`。本次截图对比已按各自正确格式访问。
- LSP 未能运行 `.vue` 诊断，原因是环境缺少 `vue-language-server`；已用 `npm run vite:build` 验证构建通过。
