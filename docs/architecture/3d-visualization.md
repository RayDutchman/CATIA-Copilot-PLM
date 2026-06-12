# DocDokuPLM 3D 可视化与转换机制

> 记录 3D 模型可视化所依赖的完整技术链路，包括文件转换流程、常见失败场景、数据库结构与前端渲染机制。

---

## 整体流程概览

```
用户上传 .stp 文件
      │
      ▼
PartBinaryResource.uploadNativeCADFile()
  ├─ 校验扩展名白名单（BUG-09 修复）
  ├─ productService.saveNativeCADInPartIteration()   ← 要求零件已 checkout
  └─ converterService.convertCADFileToOBJ()          ← 发送 Kafka 消息
                        │
                        ▼（异步，经 Kafka 消息队列）
              转换服务（独立容器 converter）
              使用 OCCT / Assimp 转换 stp → obj
                        │
                        ▼（HTTP 回调）
              ConverterBean.handleConversionResultCallback()
                ├─ 再次检查 isCheckedOut()            ← 关键检查点
                ├─ 保存 .obj 到 partiteration_geometry
                └─ productService.endConversion(succeed=true)
```

---

## 转换成功的必要条件

### 1. 零件必须处于 Checkout 状态

`saveNativeCADInPartIteration`（`ProductManagerBean.java:645`）要求：
```java
if (isCheckoutByUser(user, partR) && partR.getLastIteration().equals(partI))
```
- 零件必须被**当前用户** checkout
- 上传的 iteration 必须是**最新迭代**

否则抛出 `NotAllowedException4`，上传直接失败（HTTP 403/400）。

### 2. 转换回调时零件仍须处于 Checkout 状态

`ConverterBean.handleConversionResultCallback()`（`ConverterBean.java:172`）：
```java
if(!partRevision.isCheckedOut()) {
    LOGGER.severe("Cannot proceed as the part is not checked out");
    productService.endConversion(partIterationKey, false);
    return;  // geometry 不保存
}
```

转换是**异步的**（经 Kafka 队列），耗时数秒至数十秒。若转换尚未完成就执行 check-in，回调时 `isCheckedOut()` 为 false，geometry 被丢弃。

**这是"无转换"最常见的成因。**

---

## 正确操作顺序

```
1. POST /workspaces/{ws}/parts/{num}/versions/{ver}/checkouts
       ← 必须先 checkout

2. PUT  /workspaces/{ws}/parts/{num}/versions/{ver}/iterations/{iter}/nativecad
       ← 上传 .stp，此时触发异步转换

3. GET  /workspaces/{ws}/parts/{num}/versions/{ver}/iterations/{iter}/conversion
       ← 轮询直到 pending=false && succeed=true

4. POST /workspaces/{ws}/parts/{num}/versions/{ver}/checkins
       ← 确认转换完成后再 check-in
```

---

## 转换状态查询

```
GET /api/workspaces/{workspaceId}/parts/{partNumber}/versions/{version}/iterations/{iteration}/conversion
```

返回：
```json
{
  "pending": false,
  "succeed": true,
  "startDate": "2026-05-21T19:24:33.722Z",
  "endDate": "2026-05-21T19:24:34.310Z"
}
```

| pending | succeed | 含义 |
|---------|---------|------|
| true    | -       | 转换进行中，不要 check-in |
| false   | true    | 转换成功，可以 check-in |
| false   | false   | 转换失败（格式不支持、或 checkout 状态错误） |

---

## 数据库结构

### `binaryresource` 表

| 字段 | 说明 |
|------|------|
| `fullname` | 主键，文件完整路径，如 `Workspace_1/parts/lowerpad/A/1/nativecad/lowerpad2.stp` |
| `dtype` | `BinaryResource`（普通文件）或 `Geometry`（转换后的 .obj） |
| `quality` | LOD 质量级别（仅 Geometry 类型有值，通常为 0） |
| `x_min/x_max` 等 | 包围盒坐标（仅 Geometry 类型有值） |

### `partiteration_geometry` 表

关联 partiteration 与其转换后的 geometry 文件：

```sql
SELECT * FROM partiteration_geometry WHERE workspace_id = 'Workspace_1';
```

若此表中无某零件的记录，前端即显示"无转换"。

### `conversion` 表

记录每次转换任务的状态：

```sql
SELECT * FROM conversion WHERE workspace_id = 'Workspace_1';
```

关键字段：`pending`（boolean）、`succeed`（boolean）。

---

## 实测数据（Workspace_1，2026-05-21）

| 零件 | nativecad 文件 | conversion.succeed | geometry 记录 | 前端显示 |
|------|---------------|-------------------|--------------|---------|
| lowerpad | lowerpad2.stp ✓ | false | 无 | 无转换 |
| diffear_rd-right | diffear_rd-right.stp ✓ | false | 无 | 无转换 |
| difffear-left | difffear-left.stp ✓ | false | 无 | 无转换 |
| rearuprear_ear | rearuprear_ear-inframe2.stp ✓ | false | 无 | 无转换 |
| subpad | 无（NULL） | 无记录 | 无 | — |
| testPartNumber | Bell_Crank_Rear_Ear.stp ✓ | **true** | 有 .obj | 3D 正常显示 |

**结论：** lowerpad 等四个零件的 `.stp` 文件上传时零件未保持 checkout 状态至转换完成，导致回调时 geometry 被丢弃。

---

## 可支持转换的文件格式

以下格式可触发 stp→obj 转换（`PartBinaryResource.java` 白名单）：

```
obj, stl, off, ply, 3ds, wrl, dae, dxf, lwo, x, ac, cob, scn, ms3d,
stp, step, igs, iges, ifc
```

**不支持的格式（上传返回 HTTP 400）：**
- `.CATPart`、`.CATProduct`（CATIA 原生格式，需商业 CAD 库，见 BUG-10）

---

## 前端 3D 渲染流程

1. 用户点击"可视化装配体"，前端调用：
   ```
   GET /api/workspaces/{ws}/products/{ciId}/instances?configSpec=latest
   ```

2. 后端 `InstanceBodyWriterTools.java` 递归装配树，**累乘层级变换矩阵**，返回每个叶子零件的全局 4×4 世界坐标矩阵（16 个 double）及对应 `.obj` 文件 URL。

3. 前端 `InstancesManager.js` 下载 `.obj` 文件，调用 `mesh.applyMatrix4(matrix)` 放置到三维场景中。

4. **若某叶子零件无 geometry 记录（`files` 数组为空），该零件在三维场景中不显示**，整个装配体可能因此看起来是空的。

---

## 装配体感叹号（ModificationNotification）说明

### 现象

当某零件的子件发生了新 check-in（迭代变化）后，该零件在前端会显示感叹号，提示"子件已更新，请确认"。用户可点击"标记为已验证"（Acknowledge）消除感叹号。

### 技术实现

触发链路：

```
checkInPart()
  → CDI Event: @CheckedIn
    → PartNotificationManager.onCheckInPartIteration()
      → ProductManagerBean.createModificationNotifications()
        → 对所有把该零件作为子件/替代件的父装配迭代
          → 创建 ModificationNotification 记录（acknowledged=false）
```

"标记为已验证" 对应接口：
```
PUT /api/workspaces/{ws}/notifications/{notificationId}
Body: { "ackComment": "..." }
```

处理方法：`ProductManagerBean.updateModificationNotification()`（第 1006–1026 行），仅设置 `acknowledged=true` 和时间戳，无其他副作用。

### 是否影响 3D 预览

**不影响。** `configSpec=latest` 对应 `LatestCheckedInPSFilter`，其 `filter()` 方法只调用 `getLastRevision().getLastCheckedInIteration()`，完全不读 `ModificationNotification` 表。感叹号状态只附加在 `ComponentDTO.notifications` 字段上用于前端展示，不参与任何版本选择或 geometry 加载逻辑。

**结论：装配体及其全部子件完成 check-in 后，3D 预览即可正常显示，无需点击"标记为已验证"。**

---

## 修复建议

### 方案 A：用正确顺序重新上传（无需改代码）

对未能正常显示 3D 的零件，执行：
```
checkout → 上传 .stp → 等转换完成（轮询 conversion 接口） → checkin
```

也可对已上传但 geometry 在 checkout 状态的迭代，直接调用 check-in 接口（如本次对 Assem1 装配树的处理）：
```
PUT /api/workspaces/{ws}/parts/{partNumber}-{version}/checkin
```

### 方案 B：修改 ConverterBean 逻辑（改代码）

去除或放宽 `ConverterBean.java:172` 中对 `isCheckedOut()` 的强制要求，允许已 check-in 的零件保存转换结果。

**依据：** 转换是异步的，合理使用场景下用户 checkout → 上传 → 立即 checkin 是完全合法的操作，不应因此丢失转换结果。

**修改位置：** `docdoku-plm-server/docdoku-plm-server-ejb/src/main/java/com/docdoku/plm/server/ConverterBean.java:172`

---

## 相关源码位置

| 文件 | 说明 |
|------|------|
| `docdoku-plm-server-rest/.../file/PartBinaryResource.java:106~168` | 上传 nativecad 接口，含格式白名单和转换触发 |
| `docdoku-plm-server-ejb/.../ConverterBean.java:103~145` | 发送 Kafka 转换任务 |
| `docdoku-plm-server-ejb/.../ConverterBean.java:147~225` | 处理转换回调，含 checkout 检查（:172） |
| `docdoku-plm-server-ejb/.../ProductManagerBean.java:638~688` | `saveNativeCADInPartIteration`，含 checkout 检查（:645） |
| `docdoku-plm-server-rest/.../util/InstanceBodyWriterTools.java` | 装配体矩阵递归合成 |
| `docdoku-plm-front/.../dmu/InstancesManager.js` | 前端下载 .obj 并应用变换矩阵 |

---

## 零件、装配体、CADInstance 三者的地位与数据库结构

### 概念地位

| 概念 | 本质 |
|------|------|
| **零件（PartMaster）** | 设计对象本体，有编号和版本。叶子零件（无子件）和装配体（有子件）是**同一个实体类** |
| **装配体** | 不是独立类型，就是 `components` 非空的 PartMaster。由 `PartIteration.isAssembly()` 动态判断（非数据库字段） |
| **CADInstance** | 描述"某个子件在父装配体中的空间摆放位置"，是纯几何变换记录，**不是零件本身**，脱离 PartUsageLink 毫无意义 |

三者关系一句话：**PartMaster 是"什么"，PartUsageLink 是"谁用了谁"，CADInstance 是"放在哪里"。**

### 数据库表结构

```
partmaster                          零件主表（partnumber + workspace_id 为 PK）
  └── partrevision                  版本表（version A/B/C...）
        └── partiteration           迭代表（iteration 1/2/3...）
              │
              ├── partiteration_geometry      转换后的 .obj geometry 文件（有则可显示3D）
              ├── partiteration_binres        附件文件（.CATPart 等）
              │
              └── partiteration_partusagelink  BOM 行关联表
                    └── partusagelink           BOM 行（引用一个子件）
                          ├── component_partnumber → partmaster  （被引用子件）
                          └── partusagelink_cadinstance           位置实例关联表
                                └── cadinstance                   位置（tx/ty/tz + 旋转矩阵）
```

### 关键设计点

- **一个 `partusagelink` 可对应多个 `cadinstance`**：同一子件在装配体中出现 N 次（阵列、镜像），就有 N 个 CADInstance
- **`cadinstance` 只存变换数据**（tx/ty/tz + 欧拉角或 3×3 旋转矩阵），通过 `partusagelink` 才能知道"这个位置放的是什么零件"
- **`isAssembly()` 不是数据库字段**，无法在 SQL/JPQL 中直接过滤

### 前端零件列表"零件与装配体混合展示"分析

PLM 将零件和装配体混合在同一列表展示，这是 PLM 领域的惯常设计（Teamcenter、Windchill 同理），因为装配体本质上就是"有子件引用的零件"，共享相同的版本管理和工作流机制。

**现有过滤能力（截至分析时）：**

| 层级 | 现状 |
|------|------|
| `GET /parts` QueryParam | 只有 `start`、`length`，无过滤能力 |
| `GET /parts/search` QueryParam | 16 个参数，无 `assembly` 参数 |
| `PartMaster` 实体字段 | 有 `standardPart`，无 `assembly` 字段 |
| `PartIteration.isAssembly()` | 动态计算，非持久化，无法直接 SQL 过滤 |
| 前端 UI | DataTables 本地文本框，无装配体过滤 |

**如需实现"只显示零件/只显示装配体"过滤，需要：**

- **纯前端方案**（改动最小）：API 返回的 JSON 中已有 `assembly` 字段，前端加载后客户端过滤，加切换按钮。缺点：分页条数会不准确。
- **前后端完整方案**：后端 `GET /parts` 新增 `@QueryParam("assembly") Boolean assembly`，JPQL 用 `WHERE components IS [NOT] EMPTY` 过滤；前端 Collection `url()` 附加参数，视图加切换 UI。
