# 前端 Vue 化工作 - Session 交接

**上一 session**：Opus 4.7，因 premium quota 切换至 Sonnet 4.6
**交接时间**：2026-05-18
**分支**：`feat/vue3-frontend-modernization`

---

## 一句话现状

main-vue 登录页已上线，4 模块已 vue 化，FolderView+DocumentList 两个 bug 代码已修但**未部署**，还剩 4 件事。

---

## 立即要做的事（按顺序）

### 1. 部署当前修复并验证（最高优先级）

```bash
cd /home/chenweibo/CATIA-Copilot-PLM/docdoku-plm-front
npm run vite:build

cd /home/chenweibo/CATIA-Copilot-PLM
docker build -f docdoku-plm-front/docker/Dockerfile docdoku-plm-front -t docdoku/docdoku-plm-front:2.6.2
cd docdoku-plm-docker
docker compose up -d --no-deps --force-recreate front

# 验证
curl -I http://localhost:8001/main-vue/   # 期望 200
```

然后 Playwright 验证：
- 登录 admin/password
- 进 document-management-vue
- 点 ~admin 文件夹（之前 404，应正常显示）
- 检查 DocumentList 16 列（checkbox|Ref|Ver|Iter|Type|Title|Author|ModDate|Status|CheckoutBy|ACL|🔒|🔄|🌐|📎|Actions）
- 字段名运行时核对（见下方"待验字段"）

### 2. 修 WorkspaceDashboard.vue Y 轴 CJK 截断

文件：`vite-src/workspace-management-vue/views/WorkspaceDashboard.vue`
位置：用户柱状图 SVG `viewBox="0 0 380 220"` 的 y=201 文本
问题：19px 空间被 CJK 截断
方向：扩 viewBox 高度或加 padding，或文本旋转 -45deg

### 3. vue 化 organization-management

源：`app/organization-management/`
目标：`vite-src/organization-management-vue/`
模式参考已完成的 `account-vue` / `change-vue` / `workspace-management-vue` / `document-management-vue`
完成后：
- 加入 `vite.config.js` 入口
- 加入 `Dockerfile` COPY
- 加入 `nginx.conf` location
- 更新 `MenuCards.vue` 对应卡片的 `vueUrl`

### 4. 生成 MANUAL_TEST_CHECKLIST.md

路径：`/home/chenweibo/CATIA-Copilot-PLM/MANUAL_TEST_CHECKLIST.md`
内容必须包含：
- 5 账户 × 多模块测试矩阵（admin/alice/bob 全权限，carol/dave 只读，密码均 `password`）
- 每个 vue 化模块的对比项（Vue 版 vs 原版）
- 已知遗留 issue 标注（3D 占位、~/folders 首次 404、CORS /memberships、文件夹名仅 `[A-Za-z0-9_-]`）
- intense E2E 维度：console.error / network 4xx5xx / visual diff / CJK 渲染

### 5. 更新 FRONTEND_MODERNIZATION_PLAN.md + Commit & Push

Conventional Commits：
- `feat(document-management-vue): support full 16 columns matching legacy`
- `fix(folder-view): correct ~user folder API path encoding`
- `feat(main-vue): add Vue version login page at /main-vue/`
- `feat(organization-management-vue): port organization module to Vue 3`
- `docs: add manual test checklist`

Push 需 classic PAT（细粒度 PAT 无效）。

---

## 已完成的事

- main-vue 9 文件 + 四语 i18n 落盘部署，HTTP 200
- vite.config.js / Dockerfile / nginx.conf 三处配置
- 4 模块已 vue 化：account / workspace / change / document-management-vue
- 放弃 vue 化：product-structure（3D）/ visualization（3D）/ parts
- FolderView.vue ~admin 404 修复（folderId 完整格式 `{ws}:~{login}`，URL 用斜杠代冒号）
- DocumentList.vue 16 列完整重写（清理了误编辑遗留的重复 td）

---

## 关键技术上下文

### ~admin 真实 API（curl 验证 200）
```
GET /workspaces/Workspace_0/documents?folder=Workspace_0:~admin
```

### DocumentList.vue 运行时待验字段
- `doc.currentIteration` / `doc.lastIteration.iteration`
- `doc.type`
- `doc.acl.userEntries` / `doc.acl.groupEntries`
- `doc.iterationChangeSubscription`
- `doc.stateChangeSubscription`
- `doc.publicShared`
- `doc.lastIteration.attachedFiles` / `doc.attachedFiles`

字段名以浏览器 network 面板实际响应为准，不一致就改 helper。

### 部署链路
- 端点：webapp.properties.json apiEndPoint = `http://localhost:8001/docdoku-plm-server-rest/api`
- 入口：`http://localhost:8001/main-vue/`（Vue 登录）vs `http://localhost:8001/`（原版）
- 部署后强制刷新（main.js 必须 import LESS 才能样式生效）

### 测试账户
| 账户 | 密码 | 权限 |
|---|---|---|
| admin | password | 全权限 |
| alice | password | 全权限 |
| bob | password | 全权限 |
| carol | password | 只读 |
| dave | password | 只读 |

工作区：`Workspace_0`

### 不能动的边界
- 后端 / 数据库 / docker-compose.yml 不改
- 注释（P3 必要注释）保留不改
- 用户体验只有"真实浏览器人工测试通过"才算验证通过

---

## 模型配置

- `~/.config/opencode/opencode.json` 默认模型已设 `github-copilot/claude-sonnet-4.6`
- `~/.config/opencode/oh-my-openagent.json` Sisyphus agent 已设 sonnet-4.6
- 重启 web server 后新 session 自动生效

---

## 并行策略建议（新 session 决定）

剩余 4 件事可拆 3 个 sisyphus-junior 后台子代理（用户能在浏览器左侧 session 列表看到）：

- A `quick`: 修 WorkspaceDashboard CJK + 部署验证
- B `unspecified-high`: vue 化 organization-management
- C `deep`: 写 MANUAL_TEST_CHECKLIST + intense Playwright E2E

主代理（Sonnet 4.6）做：部署当前修复 + 协调 + 合并 + commit。

spawn 方式：
```typescript
task(category="...", load_skills=[], run_in_background=true, prompt="...")
```

务必 `run_in_background=true`，否则浏览器看不到子 session。
