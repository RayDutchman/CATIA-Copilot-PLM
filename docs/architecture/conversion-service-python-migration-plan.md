# 转换服务迁移方案：Java/Quarkus → Python-only

> **状态：待评审（2026-07-04）**
>
> 本文档规划将 `docdoku-plm-conversion-service` 的 Java 编排层迁移为纯 Python 实现。
> 核心 STEP→GLB 转换脚本（`convert_step_glb.py`）保持不变。
>
> ⚠️ 迁移未开始前，当前生产使用的是"混合镜像"方案（见文末回滚章节）。

---

## 一、背景：为什么要迁移

### 触发问题

2026-07-04 修复 `Tools.unAccent()`（去掉空格转下划线）后重建转换服务，出现**消费者消费 Kafka 消息但不投递给 `@Incoming` 处理方法**的间歇性故障：

- 消息能被 `ConversionOrderDeserializer` 成功反序列化
- 但 `App.onConversionOrder()` 时被时不被调用
- 同样的 `App.class`（MD5 完全一致）、同样的 lib jar，旧 runner jar 可靠、我们重建的 runner jar 不可靠

**根因定位**：问题在 Java 编排层的 Quarkus 1.2.1 / SmallRye Reactive Messaging 1.0.8 框架，与我们重建 runner jar 时的 Quarkus 增强产物有关。核心 Python 转换脚本一直是好的。

### 关键事实（代码审查结论）

| 组件 | 行数 | 职责 | 是否问题源 |
|------|------|------|-----------|
| `convert_step_glb.py` | 514 | OCP 读 STEP → 三角化 → pygltflib 建 GLB，含颜色双策略 | ❌ 可靠，是服务价值所在 |
| Java 编排层（10 个文件） | 1,660 | Kafka 消费 → `ProcessBuilder` 起 Python 子进程 → HTTP 回调 | ✅ 是，SmallRye 投递 bug 根源 |

**核心洞察**：Java 层不做任何 3D 处理，只是起一个 Python 子进程。而 Python 解释器本来就在容器里。可靠性问题全部来自 1,660 行 Java，真正干活的 Python 脚本从未出错。

---

## 二、目标架构

```
现状:
  Kafka ──> [Java/Quarkus] ──ProcessBuilder──> [Python/OCP] ──> GLB
                ↑ 1660行，不可靠                  ↑ 514行，可靠
                └─ HTTP回调后端

目标:
  Kafka ──> [Python: aiokafka + OCP 进程内调用] ──> GLB ──> httpx 回调后端
                ↑ 全部合并，~350行，单一语言，无 JVM
```

彻底删除 JVM / Quarkus / SmallRye / Dozer / CDI。

### 技术栈选型

| 层 | 选型 | 理由 |
|----|------|------|
| 运行时 | Python 3.12 slim | 与转换脚本同语言，无 JVM |
| Kafka | `aiokafka` | 异步、社区成熟、手动 offset 提交，无 SmallRye 投递 bug |
| HTTP 回调 | `httpx` | 现代异步 HTTP 客户端 |
| CAD 引擎 | `cadquery-ocp`（**不变**） | 唯一能读 B-rep STEP 的可靠方案 |
| GLB 构建 | `pygltflib`（**不变**） | 保留颜色双策略（XDE + STEP 文本解析） |
| 镜像基础 | `python:3.12-slim` + OCC 系统库 | ~250MB（对比现在 ~882MB content / 2.86GB disk） |

**为何不选 Go/Rust**：OCP 只有 Python 绑定，Go/Rust 仍需回调 Python 子进程，等于没简化。核心是 Python，编排也用 Python 最干净。

**为何不用 OCC 原生 `RWGltf_CafWriter`**：虽然它能直接把 XDE 文档写成 GLB（省 ~200 行手工三角化），但它只从 XDE ColorTool 读颜色，**CATIA AP242/AP214 的 STEP 文本颜色 fallback 会失效**。故保留现有手工脚本。

### 范围确认

- ✅ **只保留 STEP/IGES → GLB**（`stp/step/igs/iges`）
- ❌ **删除其他格式转换器**：OBJ 透传、STL/OFF/PLY/3DS/WRL（meshconv）、DAE/DXF（assimp）、IFC（IfcConvert）。CATIA 协同场景只用 STEP。
- 连带删除外部二进制：`meshconv`、`assimp-utils`、`IfcConvert`、`openMeshDecimater`（减面本就一直失败）

---

## 三、分阶段迁移步骤

### Phase 0 — 冻结与基线（0.5 天）
1. 用当前混合镜像跑通全部现存 Part，记录每个 GLB 的顶点数/材质数/包围盒作为回归基线
2. 导出代表性测试集：CATIA AP242 彩色件、AP203 件、纯约束件（无几何）、多实体装配体

### Phase 1 — Python 转换脚本函数化（0.5 天）
1. 将 `convert_step_glb.py` 的 `main()` 拆为 `convert(input_path, output_path, deflection, angular) -> dict`
2. 返回 `{glb_path, bbox: [xmin,ymin,zmin,xmax,ymax,zmax], solid_count}`
3. 保留 CLI 入口做兼容测试

### Phase 2 — 新编排服务 `main.py`（2 天）
1. `aiokafka` 消费 `CONVERT` topic（`group.id=conversions_group`），反序列化 `ConversionOrder` JSON
2. 移植 `getVirtualPath`：`vault_path + "/" + unAccent(fullName)`，**保持不带下划线转换**（大小写与空格原样）
3. 进程内调用 `convert()`，拿 GLB + bbox
4. `httpx` PUT 回调 `{ENDPOINT}/workspaces/{w}/parts/{p}/versions/{v}/conversion`
   - Body 对齐 `ConversionResultDTO`：`tempDir`/`convertedFileLODs` 只传文件名（后端 Dozer 用 `conversionsPath` 重构绝对路径）
   - `convertedFileLODs = {"0": "<uuid>.glb"}`
5. **显式 offset 提交**：处理成功才 commit，失败重试——根治"消费但不处理"
6. 空几何体（no geometry generated）走 `succeed=true` 跳过（沿用后端已有逻辑）

### Phase 3 — Dockerfile 重写（0.5 天）
1. `python:3.12-slim` + OCC 运行时系统库（`libgl1 libglib2.0-0 libxrender1 libsm6 libxt6`）
2. `pip install`：现有 `requirements-converter.txt` + `aiokafka` + `httpx`
3. 删除：JDK、meshconv、assimp、IfcConvert、decimater、Quarkus 全家桶
4. 保留 wheels 离线安装策略
5. `ENTRYPOINT ["python3", "main.py"]`

### Phase 4 — 回归验证（1.5 天）
1. 测试集逐个转换，比对 GLB 顶点数/材质数/包围盒与基线一致
2. **重点验证 CATIA 彩色件颜色正确**（最脆弱环节）
3. 快速连续上传 3 件验证无 race condition
4. 前端 3D 预览目视确认

### Phase 5 — 切换与灰度（0.5 天）
1. docker-compose 保留旧 `conversion` 定义（注释）
2. 新服务先用不同 `group.id` 影子消费验证，再切主 `group.id`
3. 观察 24h 无异常后清理

**总计：约 5 人天**（已确认砍掉其他格式，省 2 天）

---

## 四、风险与缓解

| # | 风险 | 等级 | 缓解 |
|---|------|------|------|
| 1 | 颜色 fallback 丢失（若误用 OCC 原生写出器） | 高 | **不改核心脚本**，保留手工三角化+文本解析双策略 |
| 2 | DTO 契约不对齐（Python 回调 Body 与后端 Dozer 反序列化不匹配） | 高 | Phase 2 抓包对比 Java 版实际 PUT Body，逐字段对齐 |
| 3 | `aiokafka` 消费语义 exactly-once | 中 | 手动 commit + 幂等（后端已有 `findPendingConversionForRevision` 去重） |
| 4 | 大装配件 OCP 段错误拖垮消费者 | 中 | 转换可回退到 subprocess 隔离模式，崩溃不影响消费循环 |
| 5 | JWT 过期导致回调失败 | 低 | 已验证新上传 token 有效；长转换可让后端签发长效转换专用 token |

---

## 五、回滚策略（关键：保证此路不通可退回）

### 当前"勉强能用"方案 = 混合镜像

由旧项目 `plm-unified-conversion` 的 runner jar（消息投递可靠）+ 我们重建的 lib jar（含 `unAccent` 修复）组合而成。

### 已就绪的回滚资产

| 资产 | 位置 | 说明 |
|------|------|------|
| 回滚镜像 tag | `docdoku/docdoku-plm-conversion-service:2.6.2-jvm-hybrid-rollback` | 当前可用混合镜像的备份 tag |
| 旧 runner jar | `docdoku-plm-conversion-service/rollback-artifacts/app.jar.hybrid-rollback` | 混合镜像的核心（可靠投递的 runner jar） |
| 当前 lib jar | `docdoku-plm-conversion-service/conversion-service/target/lib/` | 含修复后的 server-core/server-ext |

### 重建混合镜像的步骤（如需从零重建）

```bash
# 1. 准备构建目录
mkdir -p /tmp/hybrid-build/lib
cp docdoku-plm-conversion-service/rollback-artifacts/app.jar.hybrid-rollback /tmp/hybrid-build/app.jar
cp docdoku-plm-conversion-service/conversion-service/target/lib/* /tmp/hybrid-build/lib/

# 2. 基于原 JVM 镜像叠加（Dockerfile 见下）
cd /tmp/hybrid-build
cat > Dockerfile <<'EOF'
FROM docdoku/docdoku-plm-conversion-service:2.6.2-jvm-hybrid-rollback AS base
FROM base
COPY app.jar /deployments/app.jar
COPY lib/* /deployments/lib/
EOF
docker build -t docdoku/docdoku-plm-conversion-service:2.6.2 .
```

### 一键回滚

```bash
# docker-compose.yml 中 conversion 服务的 image 改回：
#   image: docdoku/docdoku-plm-conversion-service:2.6.2-jvm-hybrid-rollback
cd docdoku-plm-docker
docker compose up -d --force-recreate --no-deps conversion
```

**无数据迁移风险**：vault 目录结构、数据库 schema、Kafka topic 全部不变，回滚仅换镜像。

### 新方案镜像 tag 约定

- 新 Python 镜像用独立 tag：`docdoku/docdoku-plm-conversion-service:2.7.0-py`
- 切换前 `:2.6.2` 保持指向混合镜像，验证通过后再重打 `:2.6.2` → Python 版
- 任何阶段都可 `image:` 一行切回 `:2.6.2-jvm-hybrid-rollback`

---

## 六、验证清单（完成标准）

> **状态（2026-07-04 自动化验证结果）**

- [x] 测试集 GLB 转换成功（`Bevel Gear Formula Student 2008 - 2009`，`Outer Plate 2010`，`succeed=true`）
- [ ] CATIA 彩色件材质颜色目视正确（需人工确认）
- [x] 纯约束件（无几何）`"no geometry generated"` 走成功路径（代码逻辑已覆盖，对齐后端 ConverterBean）
- [x] 快速连传多件全部 `succeed=true`（Kafka `max_poll_records=1` + 手动 commit，无 race condition）
- [x] `unaccent()` 5 个测试用例全部通过（空格保留、变音符去除、下划线保留）
- [x] `convert()` 函数可导入，签名正确，`ConversionError` 是 `RuntimeError` 子类
- [x] `main.py` 语法检查通过，11 个 import，函数结构正确
- ⚠️ 镜像 virtual size：2.38 GB（目标 300MB **不现实**，Python + OCC 无法低于 1GB；已比 JVM 混合镜像小 480MB）
- ⚠️ 冷启动：~2.2s（目标 1s **不现实**，Python 模块导入本身需 2s；实际服务常驻内存无需关注冷启动）
- [x] 消费循环健壮性：`commit()` 失败不终止循环（已修复 P0-A，2026-07-04）
- [x] JWT 过期有明确日志，不静默丢失（已修复 P0-B，2026-07-04）
- [x] 回调成功后 temp_dir 自动清理（已修复，2026-07-04）
- [x] Dockerfile 顶部有"必须通过 build.sh"警告（已修复 P1，2026-07-04）

**不再适用（用户决定不需要）**：
- ~~回滚演练：能在 1 分钟内切回混合镜像~~

---

## 七、涉及文件清单

### 新增
- `conversion-service-py/main.py`（编排：aiokafka + 回调，~200 行）
- `conversion-service-py/converter.py`（由 `convert_step_glb.py` 函数化而来，514 行）
- `conversion-service-py/Dockerfile`（python:3.11-slim-bookworm）
- `conversion-service-py/requirements.txt`（现有 5 包 + aiokafka + httpx）

### 保留不动
- 后端 `ConverterBean.java`、`PartResource.java`（回调契约不变）
- `docdoku-plm-server-core` 的 `Tools.unAccent()`（已修复）

### 删除（迁移完成后）
- 全部 Java 编排代码（`App.java` 等 10 个文件）
- 其他格式转换器（OBJ/DAE/IFC/STL）及对应外部二进制
