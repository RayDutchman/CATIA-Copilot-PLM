# DocDokuPLM 前端现代化计划

> 最后更新：2026-05-18（测试数据创建完毕 + Playwright 自动化验收完成）
> 当前进度：**change/document/workspace-management-vue 三个模块全部通过 Playwright 自动化验收；等待用户真实浏览器人工验证**

---

## 核心策略

不做"全量重写"，也不做"Backbone→ESM→Vue 三次迁移"。采用**双轨并行 + nginx 路由分流**：

- **旧轨**：未迁移的模块保留原 Grunt + RequireJS AMD 构建，输出到 `dist/`，由 nginx 继续服务
- **新轨**：新模块直接以 Vue 3 SFC 形式开发，由 Vite 构建，输出到 `dist-vite/`，nginx 按路径路由到新轨
- 两套系统通过 nginx 路由分流共存，**不在同一个构建里混合 AMD 和 Vue**
- 模块逐个迁移，每迁完一个模块旧轨对应路径切换到新轨，直到旧轨清空

```
浏览器请求
    │
    ▼
  nginx
    ├── /download/            → dist-vite/download/        (新轨，已迁移)
    ├── /account-management/  → dist-vite/account-management/ (新轨，已迁移)
    ├── /workspace-management/→ dist/workspace-management/ (旧轨，待迁移)
    ├── /document-management/ → dist/document-management/  (旧轨，待迁移)
    └── ...其余模块           → dist/                      (旧轨，待迁移)
```

---

## 阶段总览

| 阶段 | 名称 | 状态 | 产出 |
|------|------|------|------|
| **阶段 1** | 本地构建 + 中文支持 | ✅ 完成 | 前后端镜像本地构建，zh 语言支持 |
| **阶段 2** | Vite 构建链 + 共享基础设施 ESM | ✅ 完成 | Vite 搭建完毕，两个试点模块迁移完成 |
| **阶段 3** | Vue 3 架构搭建 | ✅ 完成 | Vue 3 + Pinia + vue-i18n 基础框架，account-management Vue SFC 版验证 |
| **阶段 4** | 逐模块 Vue 3 重写 | ✅ workspace-management 完成 | workspace-management Vue SFC 版完成并验证 ✅ |
| **阶段 5** | 3D 视图专项升级 | 🔲 未开始 | Three.js r90 → r165+，Web Component 封装 |

---

## 阶段 1：本地构建 + 中文支持 ✅

**目标**：脱离 DockerHub 预构建镜像，解决中文支持问题。

### 完成内容

- [x] 安装 JDK 11、Maven 3.9.12、nvm + Node.js v14.21.3
- [x] 后端源码重建（`PropertiesLoader.java` 加入 `zh` 到 `SUPPORTED_LANGUAGES`）
- [x] 前端源码重建（`grunt build`，zh NLS 文件内嵌镜像）
- [x] docker-compose 全部 11 个容器 Up，`http://localhost:8000` 正常
- [x] 修复 `moment.locale('zh')` → `'zh-cn'`
- [x] 修复 locale fallback `'zh'` → `'en'`
- [x] nginx NLS 缓存排除（`expires -1`）
- [x] `loadSample.sh` 409 幂等修复

---

## 阶段 2：Vite 构建链 + 共享基础设施 ESM ✅

**目标**：搭建 Vite 构建链，迁移共享库，完成两个试点模块验证可行性。  
**重要约束**：此阶段只迁移"必须先迁的共享基础设施"和两个简单试点模块，其余业务模块**不做 Backbone+ESM 迁移**（等阶段 4 直接用 Vue 3 重写）。

### 完成内容

#### 构建链
- [x] `vite.config.js`：root=`vite-src/`，多页面入口，Less，代理，resolve alias
- [x] Vite dev server（端口 9090）代理后端 REST API 和 nginx 静态资源
- [x] `dist-vite/` 输出目录，与原 `dist/` 隔离

#### 共享基础设施（`vite-src/common-objects/`）
- [x] `log.js`：日志工具 ES Module 版
- [x] `common/singleton_decorator.js`：单例装饰器
- [x] `contextResolver.js`：账户/服务器属性加载，XHR 拦截（JWT 注入 + 401 重定向）
- [x] `oidc.js`：OIDC 登录，改用 npm 版 `oidc-client@1.11.5`
- [x] `models/`：User、Language、Organization、Timezone、Workspace Backbone Model
- [x] `views/alert.js`：Alert 视图
- [x] `views/header.js`：顶部导航栏视图

#### 国际化（`vite-src/localization/`）
- [x] `common.js`：741 keys，en/fr/zh/ru（自动脚本从 `app/js/localization/nls/` 生成）
- [x] `download.js`：download 模块 i18n
- [x] `account-management.js`：account-management 模块 i18n

#### 试点模块 1：download（`vite-src/download/`）
- [x] AMD → ES Module 迁移完成
- [x] `vite build` 通过，dev server 验证通过

#### 试点模块 2：account-management（`vite-src/account-management/`）
- [x] AMD → ES Module 迁移完成（`app.js`、`router.js`、`views/edit-account.js`）
- [x] `vite build` 通过（205 modules，0 errors，1.82s）
- [x] dev server 验证通过（所有资源 HTTP 200）

### 关键技术决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| `oidc-client` 来源 | npm `oidc-client@1.11.5` | bower 版 `index.js` 依赖缺失的 `src/` 目录 |
| i18n 方案 | 自动脚本生成内联 JS 对象 | 无需引入 i18next，与现有 nls/ 格式兼容 |
| AMD 模板引用 | `?raw` import | Vite 原生支持，替代 `text!tpl.html` |
| `App.config` 引用 | 改为 `window.App.config` | ES Module 无 AMD 全局，通过 window 访问 |
| Less 样式 | 直接 import 原有 `app/less/` | 不复制，减少冗余 |
| 依赖安装 | `npm install moment oidc-client` | bower 版无法被 Vite 直接解析 |

---

## 阶段 3：Vue 3 架构搭建 ✅

**目标**：在现有 Vite 构建中引入 Vue 3，建立可复用的应用基础框架，供后续所有模块使用。

### 完成内容

#### 3.1 安装依赖
- [x] `npm install vue@3.5.34 vue-router@4.6.4 pinia@3.0.4 vue-i18n@9.14.5 @vitejs/plugin-vue@4.6.2`
- [x] `vite.config.js` 加入 `@vitejs/plugin-vue` 插件和 `vue-common` alias

#### 3.2 共享 Vue 基础设施（`vite-src/vue-common/`）
- [x] `i18n.js`：vue-i18n 实例（legacy:false），`mergeModuleStrings()` 按模块追加翻译
- [x] `store/app.js`：Pinia store，`resolveServerProperties`（替代 App.config）
- [x] `store/auth.js`：Pinia store，`resolveAccount/resolveWorkspaces/logout`，含 locale 同步和 JWT 刷新
- [x] `components/AppHeader.vue`：顶部导航栏 Vue SFC（替代 `common-objects/views/header.js`）
- [x] `components/AlertBanner.vue`：Alert 提示 Vue SFC（替代 `common-objects/views/alert.js`）
- [x] `composables/useApi.js`：fetch 封装，JWT 自动注入，401 跳转，`get/put/post/del`

#### 3.3 account-management Vue SFC 重写（`vite-src/account-management-vue/`）
- [x] `index.html`、`main.js`：Pinia bootstrap，resolveServerProperties + resolveAccount
- [x] `App.vue`：Teleport AppHeader 到 `#header` 挂载点
- [x] `router/index.js`：Vue Router 4，hash history
- [x] `views/EditAccount.vue`：账户编辑表单全 Vue 重写（替代原 Backbone View + Mustache 模板）

#### 3.4 构建与验证
- [x] `vite build` 通过（260 modules，0 errors，2.64s）
- [x] `account-management-vue-*.js` 出现在构建产物列表
- [x] dev server 所有资源 HTTP 200

#### 3.5 Docker 镜像更新与 nginx 路由分流
- [x] `docker/Dockerfile`：新增 `COPY dist-vite/assets`、`COPY dist-vite/account-management-vue`
- [x] `.dockerignore`：添加 `!dist-vite` 允许构建上下文包含新产物
- [x] `nginx.conf`：添加 `/assets/` 和 `/account-management-vue/` 两个 location 块
- [x] 重建镜像并强制重建容器，验证：
  - 旧轨 `/account-management/` → HTTP 200 ✅
  - 新轨 `/account-management-vue/` → HTTP 200 ✅
  - Vite 资产 `/assets/*.js` → HTTP 200 ✅

### 关键技术决策记录

| 决策 | 选择 | 原因 |
|------|------|------|
| `@vitejs/plugin-vue` 版本 | v4.6.2 | v6 要求 Vite 5+，项目当前使用 Vite 4 |
| Vue i18n 模式 | `legacy:false`（Composition API） | 与 Vue 3 `<script setup>` 配合，`useI18n()` 直接使用 |
| Vue Router 路由模式 | `createWebHashHistory` | 无需 nginx SPA fallback，避免内部重定向循环 |
| 新旧并存策略 | 新路径 `/account-management-vue/` | 旧路径保留，验证通过后再切换 nginx 路由 |
| Docker 构建上下文 | `.dockerignore` 添加 `!dist-vite` | 原配置 `*` 排除了所有文件，需要显式允许 `dist-vite` |
| nginx try_files fallback | `=404`（不做 SPA fallback） | hash 路由客户端处理，服务器侧循环重定向 bug 的根因 |

---

## 阶段 4：逐模块 Vue 3 重写 🔄

**目标**：按复杂度从低到高，逐个将旧 AMD 模块重写为 Vue 3 SFC，每完成一个模块切换 nginx 路由。

**迁移顺序**（按复杂度排序）：

| 优先级 | 模块 | 复杂度 | 状态 |
|--------|------|--------|------|
| 1 | `account-management` | 低 | ✅ 完成（阶段 3）|
| 2 | `workspace-management` | 低-中 | ✅ 完成 |
| 3 | `change-management` | 中 | ✅ 完成 |
| 4 | `document-management` | 高 | ✅ 完成 |
| 5 | `product-structure` | 极高 | 🔲 待迁移（阶段 5 专项）|

### document-management-vue 完成内容

- [x] `vite-src/localization/document-management.js`（en/fr/zh/ru 4 语言，default export 格式）
- [x] `index.html`、`main.js`（bootstrap 流程：resolveServerProperties→resolveAccount→resolveWorkspaces→mount）
- [x] `App.vue`（Teleport header + 两列布局 + 左侧导航：文件夹/标签/文档模板/基线/已签出/任务/搜索）
- [x] `router/index.js`（hash 路由，workspaceId 参数，10 条路由）
- [x] `components/FolderTree.vue`（递归文件夹树，展开/折叠，点击加载文档）
- [x] `components/DocumentList.vue`（可复用文档列表表格，含 checkout/undo/checkin 按钮）
- [x] `views/FolderView.vue`（文件夹主视图，FolderTree + DocumentList，新建/删除文件夹）
- [x] `views/TagsView.vue`（标签列表 + 标签文档查看）
- [x] `views/TemplatesView.vue`（文档模板 CRUD，基本字段 reference/type/mask/idGenerated）
- [x] `views/BaselinesView.vue`（基线 CRUD，name/description/type）
- [x] `views/CheckedOutView.vue`（已签出文档列表）
- [x] `views/TasksView.vue`（当前用户分配任务，只读列表）
- [x] `views/SearchView.vue`（快速搜索 + 高级搜索入口）
- [x] `vite.config.js` 加入 `document-management-vue` 入口
- [x] `docker/Dockerfile` 加入 `COPY dist-vite/document-management-vue`
- [x] `nginx.conf` 加入 `/document-management-vue/` location 块
- [x] `vite build` 通过（0 errors，4.14s，产物 38.93 kB）
- [x] Docker 镜像重建，容器重部署成功
 - [x] **浏览器验证通过**：文件夹树加载（~admin 主文件夹），文档模板/已签出/搜索/基线页全部加载，导航 active 高亮正确，0 console errors（2026-05-17）
 - [x] **Playwright 验收（2026-05-18）**：文件夹树（Change_Requests/Design_Docs/Test_Reports）加载正常，Design_Docs 内 3 个文档（DS-0001/DS-0002 签出、DS-0003 签入）状态显示正确，已签出视图显示 4 个文档，文档模板列表 3 个模板显示正确 ✅
 - ⚠️ 已知遗留问题：DocumentList.vue 目前 9 列，原版 16 列，缺 iteration/type/lifecycleState 等列
 - ⚠️ 已知遗留问题：admin 无个人文件夹（~/folders 返回 404），首次进入默认路由 ~/folders 报 404 错误横幅，切换到具体工作区路径后恢复正常

### change-management-vue 完成内容

- [x] `vite-src/localization/change-management.js`（en/fr/zh/ru 4 语言，全部 key）
- [x] `index.html`、`main.js`（bootstrap 流程：resolveServerProperties→resolveAccount→resolveWorkspaces→mount）
- [x] `App.vue`（Teleport header + 两列布局 + 左侧导航：工作流/里程碑/问题/请求/订单）
- [x] `router/index.js`（hash 路由，workspaceId 参数，6 条路由）
- [x] `components/ChangeItemList.vue`（issues / requests / orders 通用组件，含创建/编辑/删除弹窗）
- [x] `views/IssueList.vue`、`views/RequestList.vue`、`views/OrderList.vue`（复用 ChangeItemList）
- [x] `views/MilestoneList.vue`（里程碑 CRUD，独立弹窗）
- [x] `views/WorkflowList.vue`（工作流模型只读列表 + 删除）
- [x] `views/TaskList.vue`（当前用户被分配任务，只读列表）
- [x] `vite.config.js` 加入 `change-management-vue` 入口
- [x] `docker/Dockerfile` 加入 `COPY dist-vite/change-management-vue`
- [x] `nginx.conf` 加入 `/change-management-vue/` location 块
- [x] `vite build` 通过（0 errors，4.01s）
- [x] Docker 镜像重建，容器重部署成功
 - [x] **浏览器验证通过**：工作流/里程碑/问题/请求/订单页全部加载，0 console errors（2026-05-17）
 - [x] **Playwright 验收（2026-05-18）**：工作流/里程碑/问题/请求/订单页全部加载，3个问题单/2个请求/1个订单/3个里程碑均正确显示，关联文档/标签/负责人显示正常 ✅

### workspace-management-vue 完成内容

- [x] `vite-src/localization/workspace-management.js`（en/fr/zh/ru 4 语言）
- [x] `index.html`、`main.js`（bootstrap 流程：resolveServerProperties→resolveAccount→resolveWorkspaces→mount）
- [x] `App.vue`（Teleport header + 两列布局 + admin 条件显示左侧导航）
- [x] `router/index.js`（hash 路由，工作区/admin 权限守卫）
- [x] `views/Home.vue`（工作区列表，WorkspaceItem 卡片组件）
- [x] `views/WorkspaceCreate.vue`（新建工作区表单）
- [x] `views/WorkspaceEdit.vue`（编辑工作区，含删除、SetNewAdmin 跳转）
- [x] `views/WorkspaceUsers.vue`（完整用户/组管理，批量操作）
- [x] `views/WorkspaceDashboard.vue`（纯 SVG 饼图+柱状图，无 nvd3 依赖，含磁盘用量/实体统计/签出统计）
- [x] `views/WorkspaceNotifications.vue`（通知设置，含"选项"弹窗 + `/back-options` API + sendEmails 开关）
- [x] `views/WorkspaceCustomizations.vue`（tag-input 自定义列，API `/front-options`，默认/清空/保存按钮）
- [x] `views/AdminDashboard.vue`（管理员磁盘用量 + 实体统计）
- [x] `views/AdminAccounts.vue`（账户启用/禁用批量操作）
- [x] `views/WorkspaceAdminNew.vue`（设置新工作区管理员）
- [x] `vite.config.js` 加入 `workspace-management-vue` 入口
- [x] `docker/Dockerfile` 加入 `COPY dist-vite/workspace-management-vue`
- [x] `nginx.conf` 加入 `/workspace-management-vue/` location 块
- [x] `vite build` 通过（0 errors）
- [x] Docker 镜像重建，容器重部署成功
 - [x] **浏览器验证通过**：首页 stats 数字正常、侧边导航动态切换、WorkspaceUsers 无 console 错误、WorkspaceDashboard 数据正常加载（2026-05-17）
 - [x] **遗留 bug 全部修复**（2026-05-17）：WorkspaceCustomizations API `/front-options` + tag-input UI；WorkspaceNotifications 选项弹窗 + `back-options` API；WorkspaceDashboard 纯 SVG 饼图+柱状图；所有子页返回按钮 `<button @click>` 替代 `<router-link>`；CSS active 链路验证完整
 - [x] **本轮部署验证通过（2026-05-17）**：
   - 侧边导航各页 active 高亮正确（编辑/用户/自定义/通知/仪表盘均正常）✅
   - 用户组「完全访问」绿色 badge 右上角 `position:absolute` 定位正确 ✅
   - 仪表盘饼图左右两列布局、柱状图 y 轴刻度线、viewBox 扩大后字号清晰 ✅
   - 顶部「我的工作区 : Workspace_0」显示正常 ✅
   - ⚠️ 已知遗留问题：散点图 Y 轴旋转标签（CJK 字符在 `rotate(-90)` SVG 内显示为截断字符），低优先级，不影响功能
 - [x] **bug 修复（2026-05-18）**：
   - `WorkspaceNotifications.vue`：修复数据源错误。原用 `/memberships`（CORS 失败）和 `/groups`（字段名不对），改为：
     - 用户组 → `/memberships/usergroups`（有 `memberId` + `readOnly`）
     - 用户列表 → `/users` 联立 `/memberships/users`，取 `login/name/email` + `readOnly`
   - `WorkspaceUsers.vue` 访问权限列为空：确认为正确行为（admin 是工作区创建者，行内显示毕业帽图标而非权限 badge，与原版一致）
  - [x] **Playwright 验收（2026-05-18）**：workspace-management-vue 首页/用户页/通知页/仪表盘页全部正常加载，用户组（审阅者/工程师）名称和成员信息正确显示 ✅

## 测试数据（2026-05-18 已创建）

| 类型 | 条目 |
|------|------|
| 测试用户 | alice/bob（完全访问，工程师组）；carol/dave（只读，审阅者组）；密码均 `password` |
| 用户组 | 工程师（完全访问）；审阅者（只读） |
| 文件夹 | Design_Docs / Test_Reports / Change_Requests |
| 文档 | DS-0001~DS-0003（Design_Docs）；TR-0001~TR-0002（Test_Reports，已签入）；CR-0001（Change_Requests） |
| 文档状态 | DS-0001/DS-0002/CR-0001 签出中；DS-0003/TR-0001/TR-0002 已签入 |
| 文档标签 | DS-0001: 需审阅+设计文档；TR-0001: 已归档；CR-0001: 紧急 |
| 文档模板 | DESIGN(DS-####)；TEST_REPORT(TR-####)；CHANGE_REQUEST(CR-####) |
| 问题单 | 3 个（登录样式/导出性能/权限缺陷），CORRECTIVE/PERFECTIVE，alice/bob 负责 |
| 变更请求 | 2 个，关联里程碑 v1.1/v2.0，包含关联文档 |
| 变更订单 | 1 个（v1.1 前端重构发布），关联里程碑 v1.1 |
| 里程碑 | 3 个（v1.0 正式上线/v1.1 前端重构/v2.0 功能扩展） |

---


2. 创建 vite-src/<module-name>/App.vue 和 router/index.js
3. 逐个将 Backbone View + Mustache 模板重写为 Vue SFC
4. 迁移 Backbone Model 的 API 调用为 useApi composable
5. 接入 vue-i18n（复用已有翻译文件）
6. vite build 通过 + dev server 验证
7. 修改 nginx.conf，将 /<module-name>/ 路由切换到 dist-vite/
8. 重建 Docker 镜像，验证生产环境
```

---

## 阶段 5：3D 视图专项升级 🔲

**目标**：将 Three.js r90 升级到 r165+，封装为 Web Component 与 Vue 解耦。

### 任务清单

- [ ] 分析 `product-structure` 模块中 Three.js r90 的 API 使用范围
- [ ] 评估 r90 → r165 的 breaking changes（几何体 API、材质、加载器等）
- [ ] 将 3D 视图逻辑封装为 `<plm-3d-viewer>` Web Component
- [ ] Vue 组件中通过 `<plm-3d-viewer>` 标签嵌入，与 Vue 响应式系统解耦
- [ ] 升级 Three.js 并适配 API 变化
- [ ] 验证模型加载（STEP/OBJ 等格式）、交互（旋转/缩放）、标注功能

---

## 文件与路径参考

| 路径 | 说明 |
|------|------|
| `docdoku-plm-front/vite-src/` | 新轨源码根目录 |
| `docdoku-plm-front/vite-src/common-objects/` | 共享基础设施 ES Module 版 |
| `docdoku-plm-front/vite-src/localization/` | 自动生成的 i18n 对象 |
| `docdoku-plm-front/vite-src/download/` | 试点模块（已迁移，Backbone+ESM）|
| `docdoku-plm-front/vite-src/account-management/` | 试点模块（已迁移，Backbone+ESM）|
| `docdoku-plm-front/vite-src/vue-common/` | Vue 3 共享基础设施（i18n/store/composables/components）|
| `docdoku-plm-front/vite-src/account-management-vue/` | account-management Vue SFC 重写版（阶段 3，测试中）|
| `docdoku-plm-front/vite.config.js` | Vite 配置（root、多页面入口、代理、Less、alias）|
| `docdoku-plm-front/dist-vite/` | Vite 构建输出（新轨）|
| `docdoku-plm-front/dist/` | Grunt 构建输出（旧轨）|
| `docdoku-plm-docker/front/nginx.conf` | nginx 路由分流配置 |
| `docdoku-plm-docker/docker-compose.yml` | 容器编排 |

## 环境信息

| 项目 | 值 |
|------|-----|
| Node.js | v14.21.3（通过 nvm 管理）|
| nvm 激活 | `export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" && nvm use --delete-prefix v14.21.3` |
| Vite dev server | `http://localhost:9090` |
| 前端（nginx） | `http://localhost:8000` |
| 后端 REST API | `http://localhost:8001/docdoku-plm-server-rest/api/` |
| docker-compose 目录 | `docdoku-plm-docker/` |
