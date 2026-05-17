# Manual Test Checklist — Vue 前端现代化

**测试环境**：`http://localhost:8000`  
**Vue 登录入口**：`http://localhost:8000/main-vue/`  
**原版入口**：`http://localhost:8000/`  
**工作区**：`Workspace_0`

---

## 测试账户矩阵

| 账户 | 密码 | 权限级别 |
|------|------|---------|
| admin | password | 全权限（全局超级管理员） |
| alice | password | 全权限（工作区管理员） |
| bob | password | 全权限（工作区普通用户） |
| carol | password | 只读 |
| dave | password | 只读 |

---

## 通用前置步骤

1. 打开无痕浏览器窗口
2. 访问 `http://localhost:8000/main-vue/`
3. 登录对应账户
4. 记录 console.error 数量（F12 → Console）
5. 记录 Network 面板 4xx/5xx 请求（F12 → Network）

---

## 模块 1：main-vue（登录页 + 卡片菜单）

### 访问路径
`http://localhost:8000/main-vue/`

### 验证项

| # | 步骤 | 期望结果 | admin | alice | carol |
|---|------|---------|-------|-------|-------|
| 1 | 输入正确账密登录 | 跳转至卡片菜单页 | ☐ | ☐ | ☐ |
| 2 | 输入错误密码 | 显示错误提示，不跳转 | ☐ | — | — |
| 3 | 卡片菜单显示 8 个模块卡片 | 每卡片有「Vue 版」和「原版」两个按钮 | ☐ | ☐ | ☐ |
| 4 | organization、document、workspace、change、account 卡片的「Vue 版」按钮可点击 | 正确跳转对应 Vue 版入口 | ☐ | ☐ | ☐ |
| 5 | product-structure、visualization、parts 卡片的「Vue 版」按钮显示为禁用 | 显示禁用样式，不可跳转 | ☐ | ☐ | ☐ |
| 6 | 点击右上角「退出」 | 清除 JWT，跳转回登录页 | ☐ | ☐ | ☐ |
| 7 | 中文界面（浏览器语言设中文） | 所有文本显示中文，无乱码 | ☐ | ☐ | ☐ |

### 已知遗留问题
- 无

---

## 模块 2：account-management-vue（账户管理）

### 访问路径
`http://localhost:8000/account-management-vue/`（或从卡片菜单进入）

### 验证项

| # | 步骤 | 期望结果 | admin | alice | carol |
|---|------|---------|-------|-------|-------|
| 1 | 页面正常加载 | 显示账户编辑表单，无 console.error | ☐ | ☐ | ☐ |
| 2 | 查看账户信息 | 显示正确的姓名/邮箱/语言/时区 | ☐ | ☐ | ☐ |
| 3 | 修改姓名后保存 | 显示「账户已更新」提示 | ☐ | ☐ | — |
| 4 | 切换语言（zh↔en） | 页面 reload 后语言切换生效 | ☐ | ☐ | ☐ |
| 5 | Vue 版 vs 原版外观对比 | 功能一致，布局相似 | ☐ | ☐ | ☐ |

---

## 模块 3：workspace-management-vue（工作区管理）

### 访问路径
`http://localhost:8000/workspace-management-vue/`

### 验证项

| # | 步骤 | 期望结果 | admin | alice | carol |
|---|------|---------|-------|-------|-------|
| 1 | 首页加载 | 显示工作区列表，无 console.error | ☐ | ☐ | ☐ |
| 2 | admin 账户：显示超级管理员专属菜单 | 「Admin Dashboard」「Accounts」链接可见 | ☐ | — | — |
| 3 | alice 账户：显示「创建工作区」按钮 | 按钮可见 | — | ☐ | — |
| 4 | 点击工作区进入编辑页 | URL 含 workspaceId，子菜单切换 | ☐ | ☐ | ☐ |
| 5 | 工作区编辑（alice/admin） | 可编辑描述，保存成功提示 | ☐ | ☐ | — |
| 6 | 工作区 Dashboard → 实体柱状图 | CJK 标签「文档」「零件」完整显示（不截断） | ☐ | ☐ | ☐ |
| 7 | 工作区 Dashboard → 用户柱状图 | CJK 用户名标签完整显示（不截断） | ☐ | ☐ | ☐ |
| 8 | 工作区 Dashboard → 签出散点图 | 散点图正常渲染 | ☐ | ☐ | ☐ |
| 9 | 用户管理：添加/禁用用户 | 操作生效 | ☐ | — | — |

### 已知遗留问题
- `/api/workspaces/{ws}/memberships` CORS 问题：carol/dave 可能触发 CORS 错误，属后端限制

---

## 模块 4：change-management-vue（变更管理）

### 访问路径
`http://localhost:8000/change-management-vue/`

### 验证项

| # | 步骤 | 期望结果 | admin | alice | carol |
|---|------|---------|-------|-------|-------|
| 1 | 页面加载 | 左侧导航+内容区正常显示 | ☐ | ☐ | ☐ |
| 2 | 选择工作区 Workspace_0 | 切换工作区后重新加载变更列表 | ☐ | ☐ | ☐ |
| 3 | 变更列表 | 显示问题单/变更单/变更请求/里程碑四个页签 | ☐ | ☐ | ☐ |
| 4 | carol 只读：无「新建」按钮 | 操作按钮隐藏 | — | — | ☐ |

---

## 模块 5：document-management-vue（文档管理）

### 访问路径
`http://localhost:8000/document-management-vue/`

### 子测试 5A：文件夹树 + FolderView

| # | 步骤 | 期望结果 | admin | alice |
|---|------|---------|-------|-------|
| 1 | 页面加载 | 左侧树+右侧列表正常显示 | ☐ | ☐ |
| 2 | 点击「~admin」文件夹 | **不出现 404**，右侧显示 admin 私有文档 | ☐ | — |
| 3 | 点击「~alice」文件夹 | 右侧显示 alice 私有文档 | — | ☐ |
| 4 | 点击普通文件夹 | 右侧显示对应文档 | ☐ | ☐ |
| 5 | 文件夹名含特殊字符（含冒号） | URL 编码正确，请求返回 200 | ☐ | ☐ |

### 子测试 5B：DocumentList 16 列

| 列 | 字段/说明 | 验证 |
|----|----------|------|
| ☐ | checkbox | 可全选/单选 |
| ☐ | Ref（文档 ID） | 正确显示 |
| ☐ | Ver（版本号） | 正确显示 |
| ☐ | Iter（迭代号） | 正确显示 |
| ☐ | Type（文档类型） | 正确显示或空 |
| ☐ | Title（标题） | 正确显示 |
| ☐ | Author（作者） | 正确显示 |
| ☐ | Mod Date（最后修改时间） | 正确显示 |
| ☐ | Status（状态） | 正确显示 |
| ☐ | Checkout By（签出人） | 签出时显示用户名 |
| ☐ | ACL（权限） | 有权限控制时显示标记 |
| ☐ | 🔒（已签出图标） | 签出状态正确显示 |
| ☐ | 🔄（订阅变更） | 有订阅时显示 |
| ☐ | 🌐（公开共享） | 公开文档时显示 |
| ☐ | 📎（附件） | 有附件时显示 |
| ☐ | Actions（操作列） | 签出/签入/下载等按钮 |

### 子测试 5C：其他页签

| # | 步骤 | 期望结果 | admin |
|---|------|---------|-------|
| 1 | Checked Out 页签 | 显示当前签出文档 | ☐ |
| 2 | Search 页签 | 搜索框可用，搜索返回结果 | ☐ |
| 3 | Tags 页签 | 显示标签列表 | ☐ |
| 4 | Templates 页签 | 显示模板列表 | ☐ |
| 5 | Baselines 页签 | 显示基线列表 | ☐ |
| 6 | Tasks 页签 | 显示任务列表 | ☐ |

### 已知遗留问题
- `~/folders` 首次点击可能出现 404（由浏览器路由时序导致），刷新后消失
- 文件夹名仅支持 `[A-Za-z0-9_-]`，含 CJK 字符的文件夹名可能触发 URL 编码问题

---

## 模块 6：organization-management-vue（组织管理）

### 访问路径
`http://localhost:8000/organization-management-vue/`

### 验证项（admin 为组织 owner）

| # | 步骤 | 期望结果 | admin | alice |
|---|------|---------|-------|-------|
| 1 | 页面加载 | 侧边栏+内容区正常显示，无 console.error | ☐ | ☐ |
| 2 | 无组织状态：显示「尚无组织」提示 | 显示创建链接 | ☐ | ☐ |
| 3 | 点击「创建组织」 | 跳转创建页，表单可填写 | ☐ | ☐ |
| 4 | 创建组织（名称 + 描述） | 成功提示，组织名出现在首页 | ☐ | ☐ |
| 5 | 首页显示成员数 | 成员数正确（≥1，含 owner 自己） | ☐ | ☐ |
| 6 | 进入成员管理页 | 成员列表正确显示姓名和邮箱 | ☐ | ☐ |
| 7 | 添加成员（输入已有用户 login） | 成员出现在列表 | ☐ | ☐ |
| 8 | 上移/下移成员 | 成员顺序改变 | ☐ | — |
| 9 | 删除成员（非自己） | 成员从列表移除 | ☐ | — |
| 10 | 进入编辑页修改描述 | 保存后描述更新 | ☐ | — |
| 11 | 删除组织（确认弹框） | 删除成功，跳回「尚无组织」状态 | ☐ | — |
| 12 | alice（非 owner）：无编辑/删除按钮 | 按钮隐藏 | — | ☐ |
| 13 | Vue 版 vs 原版功能对比 | 功能一致 | ☐ | ☐ |

---

## E2E 强化验证维度

### A. Console.error 检查

每个模块测试完成后：

1. F12 → Console
2. 筛选「Error」级别
3. 记录错误数量
4. **预期**：0 个 console.error（排除已知后端 CORS 错误）

| 模块 | admin | alice | carol |
|------|-------|-------|-------|
| main-vue | ☐ 0 | ☐ 0 | ☐ 0 |
| account-vue | ☐ 0 | ☐ 0 | ☐ 0 |
| workspace-vue | ☐ 0 | ☐ 0 | ☐ 0 |
| change-vue | ☐ 0 | ☐ 0 | ☐ 0 |
| document-vue | ☐ 0 | ☐ 0 | ☐ 0 |
| organization-vue | ☐ 0 | ☐ 0 | — |

### B. Network 4xx/5xx 检查

F12 → Network → 筛选 Status 4xx/5xx

**允许的已知 4xx**：
- `GET /organizations` 返回 404（用户无组织，属正常状态）
- `GET /workspaces/{ws}/memberships` 返回 403（CORS 后端限制）

**不允许的**：其他任何 4xx/5xx

| 模块 | admin | alice | carol |
|------|-------|-------|-------|
| main-vue | ☐ 仅已知 | ☐ 仅已知 | ☐ 仅已知 |
| account-vue | ☐ | ☐ | ☐ |
| workspace-vue | ☐ | ☐ | ☐ |
| change-vue | ☐ | ☐ | ☐ |
| document-vue | ☐ | ☐ | ☐ |
| organization-vue | ☐ | ☐ | — |

### C. CJK 渲染检查

| 项目 | 位置 | 期望 | 验证 |
|------|------|------|------|
| 切换中文界面 | main-vue 登录页 | 所有 UI 文本为中文，无乱码 | ☐ |
| 工作区 Dashboard Y 轴标签 | 实体/用户柱状图 | CJK 标签完整显示（不被 SVG 截断） | ☐ |
| 文档列表标题列 | DocumentList | 中文标题完整显示 | ☐ |
| 组织名/描述 | OrgHome | 中文组织名正确渲染 | ☐ |

### D. Visual Diff（Vue 版 vs 原版）

用两个标签页同时打开 Vue 版和原版，对比以下视觉要素：

| 模块 | 布局 | 配色 | 字体 | 表格列 | 操作按钮 |
|------|------|------|------|--------|---------|
| account | ☐ | ☐ | ☐ | — | ☐ |
| workspace | ☐ | ☐ | ☐ | — | ☐ |
| change | ☐ | ☐ | ☐ | ☐ | ☐ |
| document | ☐ | ☐ | ☐ | ☐ | ☐ |
| organization | ☐ | ☐ | ☐ | ☐ | ☐ |

---

## 已知遗留 Issue 汇总

| ID | 模块 | 问题描述 | 状态 |
|----|------|---------|------|
| I-01 | product-structure / visualization | 依赖 3D WebGL 库，暂不 vue 化，保留原版 | 已决定放弃，使用原版 |
| I-02 | parts | 与 3D 深度耦合，暂不 vue 化 | 已决定放弃，使用原版 |
| I-03 | document-vue | `~/folders` 首次点击可能 404（路由时序），刷新消失 | 已修复（folderId 编码修正） |
| I-04 | document-vue | 文件夹名仅支持 `[A-Za-z0-9_-]`，含 CJK 可能 URL 编码异常 | 低优先级，待后续 |
| I-05 | workspace-vue | `/api/workspaces/{ws}/memberships` 触发 CORS 403 | 后端配置问题，前端无法修复 |
| I-06 | workspace-vue | Dashboard 柱状图 CJK 标签被 SVG viewBox 截断 | 已修复（viewBox 高度 220→240） |
| I-07 | document-vue | 运行时字段名（currentIteration/lastIteration 等）需 Network 面板核对 | 已修复（DocumentList 使用 documentIterations[last]） |
| I-08 | main-vue | 登录提交时 apiEndPoint 未初始化会请求 `/main-vue/undefined/auth/login` | 已修复 |
| I-09 | change-vue | 只读用户仍显示新建/删除按钮 | 已修复 |
| I-10 | organization-vue | 无组织用户 `/organizations` 返回 204 时跳回原版 workspace 页面 | 已修复 |

---

## 测试通过标准

所有以下条件同时满足，视为通过：

1. ✅ 所有 ☐ 选项验证完毕，无意外失败
2. ✅ 每模块 console.error 为 0（除已知 CORS 外）
3. ✅ 每模块 Network 无意外 4xx/5xx
4. ✅ CJK 文本在所有模块中正确渲染无截断
5. ✅ Vue 版与原版功能对等（不要求视觉完全一致）
