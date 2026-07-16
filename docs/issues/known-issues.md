# PLM 问题记录（PLM_ISSUES.md）

> 本文件记录项目中发现的所有 Bug、缺陷及待修复问题。
> 每条记录包含：问题描述、根本原因、影响范围、修复状态、修复方案。
>
> **状态说明：**
> - `已修复` — 代码已修改并重建镜像，生产环境已生效
> - `已修复待验证` — 代码已修改，但运行时测试受限，未完整验证
> - `未修复` — 已知问题，尚未处理
> - `不修复/设计如此` — 确认为已知限制，暂不处理

---

## 最新修复（FastAPI 迁移字段契约）

### [BUG-50] 账号注册/更新字段契约偏移：`password`/`newPassword`、`timeZone`/`timezone` 混用
- **文件：**
  - `docdoku-plm-server-py/app/routers/accounts.py`
  - `docdoku-plm-server-py/app/services/account_manager.py`
  - `docdoku-plm-server-py/app/services/user_manager.py`
- **根本原因：** Python 迁移代码未严格对齐 Java `AccountDTO`/前端 JSON 字段名：注册读取 `password` 而非 `newPassword`，`create_account` 调用链未透传 `timeZone`，服务层使用自创缩写 `lang` 和小写 `timezone`。
- **影响：** 新注册账号密码被写为 `md5("")`，用户无法用输入密码登录；注册/更新账号时 `timeZone` 丢失。
- **修复状态：** `已修复`
- **修复方案：** 注册接口优先读取 `newPassword`；`create_account` 调用链补齐 `timeZone`；服务层参数统一为 `language`，更新账号读取 `timeZone`；新增 `scripts/check_body_field_names.py` 防回归。

---

### [BUG-51] ChangeRequest/ChangeOrder 关联 milestone 使用蛇形 `milestone_id`，前端标准 `milestoneId` 被忽略
- **文件：** `docdoku-plm-server-py/app/services/change_manager.py`
- **根本原因：** ORM 列名 `milestone_id` 被错误当作 JSON 输入字段名使用；Java `ChangeRequestDTO`/`ChangeOrderDTO` 和前端契约均为 `milestoneId`。
- **影响：** 创建或更新 ChangeRequest/ChangeOrder 时传入 `milestoneId` 不会写入，关联 milestone 功能失效。
- **修复状态：** `已修复`
- **修复方案：** 输入层读取 `milestoneId`，验证 milestone 存在后赋值给 ORM `milestone_id`。

---

## 一、高危 NPE（空指针异常）修复记录

### [BUG-01] JWT 鉴权模块未检查 Authorization 头为 null
- **文件：** `docdoku-plm-server-rest/.../auth/modules/JWTSAM.java:67`
- **根本原因：** 未检查 `Authorization` 请求头是否为 null，也未验证是否以 `Bearer ` 开头，直接 substring 操作导致 NPE 或越界
- **影响：** 所有未携带 Authorization 头的请求可能触发 500 内部错误
- **修复状态：** `已修复`
- **修复方案：** 增加 null 检查及 `startsWith("Bearer ")` 校验，非法请求返回 401

---

### [BUG-02] BasicHeader 鉴权模块：null 检查缺失
- **文件：** `docdoku-plm-server-rest/.../auth/modules/BasicHeaderSAM.java`
- **根本原因：** 三处缺陷：① credentials 为 null 时未返回 401；② 无冒号分隔符时未返回 400；③ 认证失败时 null 安全处理缺失
- **影响：** BASIC_AUTH_ENABLED=true 时，畸形认证请求可能触发 NPE
- **修复状态：** `已修复待验证`（当前 `BASIC_AUTH_ENABLED=false`，无法运行时验证）
- **修复方案：** 三处均加入 null/格式检查，返回对应 HTTP 状态码

---

### [BUG-03] 产品实例文件上传：getSubmittedFileName() 未做 null 检查
- **文件：** `docdoku-plm-server-rest/.../rest/ProductInstancesResource.java:1018`
- **根本原因：** `part.getSubmittedFileName()` 返回 null 时直接使用，导致 NPE
- **影响：** 上传无文件名的 multipart 请求时服务端 500 崩溃
- **修复状态：** `已修复`
- **修复方案：** 加入 null 检查，缺少文件名时返回 400

---

### [BUG-04] 二进制资源下载元数据：lastModified 可能为 null
- **文件：** `docdoku-plm-server-rest/.../rest/file/util/BinaryResourceDownloadMeta.java:143`
- **根本原因：** `lastModified` 字段为 null 时直接参与计算
- **影响：** 特定文件的下载请求可能触发 NPE
- **修复状态：** `已修复`（静态审查）
- **修复方案：** null 时用 0 代替

---

### [BUG-05] 产品实例二进制资源：链式调用未拆解
- **文件：** `docdoku-plm-server-rest/.../rest/file/ProductInstanceBinaryResource.java:323`
- **根本原因：** 多层链式调用，中间结果可能为 null
- **影响：** 特定产品实例文件请求触发 NPE 导致 500
- **修复状态：** `已修复`
- **修复方案：** 拆解链式调用，逐步 null 检查，为 null 时返回 404

---

### [BUG-06] 产品文件导出：文档链接目标为 null 时未跳过
- **文件：** `docdoku-plm-server-rest/.../rest/writers/ProductFileExportMessageBodyWriter.java:140`
- **根本原因：** 遍历文档链接时，目标对象或迭代列表为 null 时未 continue
- **影响：** 含空文档链接的产品导出请求触发 NPE
- **修复状态：** `已修复`（静态审查）
- **修复方案：** null 或空列表时 `continue` 跳过

---

### [BUG-07] Tools.java：getLastIteration() 返回 null 未处理
- **文件：** `docdoku-plm-server-rest/.../rest/Tools.java:259`
- **根本原因：** `getLastIteration()` 在零件版本无迭代时返回 null，后续直接调用其方法
- **影响：** 获取产品结构时，含无迭代版本的零件导致 NPE
- **修复状态：** `已修复`（静态审查）
- **修复方案：** `== null` 时跳过该版本

---

### [BUG-08] 产品基线资源：多处 null 未处理
- **文件：** `docdoku-plm-server-rest/.../rest/ProductBaselinesResource.java:150,152,161`
- **根本原因：** ① `type` 字段 null 时未设默认值；② `baselinedParts` 为 null；③ `substituteLinks`/`optionalUsageLinks` 为 null
- **影响：** 创建/查询产品基线时可能触发 NPE
- **修复状态：** `已修复`
- **修复方案：** `type` null 时默认 `LATEST`；列表 null 时默认空列表

---

## 二、文件上传相关 Bug

### [BUG-09] CAD 文件上传：不支持的格式允许上传但转换静默失败
- **文件：**
  - 前端：`docdoku-plm-front/app/js/common-objects/templates/file/file_list.html`（`<input type="file">` 无 `accept` 属性）
  - 后端：`PartBinaryResource.java`（无文件格式白名单）
  - 转换服务：`App.java`（找不到转换器时静默 return，无错误通知）
- **根本原因：**
  1. 前端 `<input type="file">` 没有 `accept` 属性，用户可选择任意格式文件上传
  2. 后端无格式校验，任何文件都被保存并触发转换流程
  3. 转换服务收到不支持格式的消息后，`selectConverter()` 返回 null，直接 return，不回调错误给用户
- **影响：** 用户上传不支持的 CAD 格式（如 `.CATPart`、`.CATProduct`、`.3dxml` 等）后，界面上无任何错误提示，3D 预览永远不会出现，用户无从得知原因
- **修复状态：** `已修复`（commit 待提交）
- **修复方案：**
  1. **前端 `FileListView`**：新增 `isFileAccepted()` 方法，支持 `accept` options 参数；`bindDomElements` 后自动给 `<input>` 设置 `accept` 属性；`fileSelectHandler` 和 `fileDropHandler` 均加格式校验，不支持的格式弹出错误提示
  2. **前端 `part_modal_view.js`**：`cadFileView` 初始化时传入 `accept` 参数，值为全部支持的 CAD 扩展名列表
  3. **后端 `PartBinaryResource.java`**：`uploadNativeCADFile` 方法加入扩展名白名单（Set），不支持的格式直接返回 HTTP 400 并说明支持的格式列表

---

### [BUG-10] CATIA 原生格式完全不支持转换
- **涉及格式：** `.CATPart`、`.CATProduct`、`.3dxml`
- **根本原因：** 转换服务中 5 个 `CADConverter` 实现类均不支持 CATIA 专有格式，系统中无任何 CATIA 转换器实现
- **影响：** 项目定位为 CATIA 协同 PLM 系统，但无法直接处理 CATIA 原生文件，必须在 CATIA 中手动预先导出为 STEP/STL
- **修复状态：** `未修复`
- **当前可用 Workaround：** 在 CATIA 中将文件导出为 `.step` 或 `.stl` 后上传
- **长期修复方向：** 实现 `CatiaFileConverterImpl`，集成第三方 CAD 转换库（如 HOOPS Exchange、CADExchanger、Aspose CAD）

---

## 三、文件上传/下载编码问题

### [BUG-11] 文件上传：文件名含特殊字符/中文时 URI 编码缺失
- **文件：** `PartBinaryResource.java`、`DocumentBinaryResource.java` 等上传接口
- **根本原因：** 文件名未经 URI 编码直接拼接到路径/响应头，含中文或特殊字符时服务端报错或客户端解析失败
- **影响：** 含中文、空格、括号等特殊字符的文件名上传/下载异常
- **修复状态：** `已修复`（分支 `fix/file-upload-npe-and-encoding`，commit `41bc390`）
- **修复方案：** 文件名在构造路径和 Content-Disposition 响应头时统一进行 URI 编码

---

## 四、认证与鉴权问题

### [BUG-12] admin 账号无法访问工作空间业务接口（设计限制）
- **根本原因：** `admin` 账号属于 `admin` 组，不具备 `regular_user` 角色；大多数工作空间业务接口（文档、零件等）要求 `regular_user` 角色，admin 调用返回 `401 Access denied`
- **影响：** admin 无法通过 REST API 直接操作工作空间内的文档/零件，需使用普通用户账号
- **修复状态：** `不修复/设计如此`（DocDokuPLM 原始设计，admin 仅管理系统，不参与业务）
- **备注：** 已创建 `testuser`（login=`testuser`，`users` 组，已加入 `Workspace_0`）用于业务接口测试

---

## 五、前端表单校验问题

### [BUG-13] 注册/编辑账号表单缺乏前端校验（已修复）
- **文件：** `docdoku-plm-front/app/js/...`（账号注册/编辑相关视图）
- **根本原因：** login、name、email、password 字段在前端无任何格式校验，空值或非法格式可直接提交到后端
- **影响：** 用户体验差，后端承受无效请求压力
- **修复状态：** `已修复`（commit `ea6bb85`）
- **修复方案：** 前端增加双重校验（HTML5 属性 + JS 逻辑），含 i18n 错误提示（zh/en/fr/ru）

---

## 六、Kafka 转换消息链路风险

### [BUG-14] Kafka Producer acks=0，转换消息可能静默丢失
- **文件：** `docdoku-plm-server-ejb/.../ConverterBean.java`（Producer 配置第 88–100 行）
- **根本原因：** `acks=0`（fire and forget），Kafka broker 未就绪时消息不重试即丢弃
- **影响：** 在 Kafka 刚启动或短暂不可用时，上传 CAD 文件后转换任务可能丢失，3D 预览永远不出现
- **修复状态：** `未修复`
- **建议修复方案：** 将 `acks` 改为 `1` 或 `all`，增加合理的 `retries` 和 `retry.backoff.ms`

---

### [BUG-15] Kafka 消息最大尺寸限制为 2MB，大型 CAD 文件可能触发
- **文件：** `ConverterBean.java`（`max.request.size=2097152`）
- **根本原因：** Kafka Producer 设置 `max.request.size=2MB`，而 ConversionOrder 中含文件路径等信息，若序列化后超过此限制则发送失败
- **影响：** 极端情况下（路径极长等）转换请求发送失败
- **修复状态：** `未修复`（低优先级，实际触发概率低）

---

## 七、构建与部署环境 Bug

### [BUG-16] docker-compose.yml 中 PostgreSQL volume 路径错误（MySQL 路径）
- **文件：** `docdoku-plm-docker/docker-compose.yml`
- **根本原因：** `db` 服务的 volume 挂载路径写成了 `/var/lib/mysql`（MySQL 的路径），而非 PostgreSQL 正确路径 `/var/lib/postgresql/data`，导致数据库数据目录未被持久化
- **影响：** 容器重启后数据库数据全部丢失
- **修复状态：** `已修复`（commit `92f1d43`）
- **修复方案：** 改为 `/var/lib/postgresql/data`

---

### [BUG-17] Kafka 使用了不兼容的 wurstmeister 镜像
- **文件：** `docdoku-plm-docker/docker-compose.yml`、`env/kafka.env`
- **根本原因：** 原配置使用 `wurstmeister/kafka` 和 `wurstmeister/zookeeper` 镜像，与当前环境不兼容，导致 Kafka 服务无法正常启动
- **影响：** CAD 文件转换消息无法发送，3D 预览功能完全失效
- **修复状态：** `已修复`（commit `44d7c00`）
- **修复方案：** 替换为 `confluentinc/cp-kafka:7.6.1` 和 `confluentinc/cp-zookeeper:7.6.1`

---

### [BUG-18] maven-compiler-plugin source/target 设置为 1.7，与 JDK 8+ 不兼容
- **文件：** `docdoku-plm-sample-data/pom.xml`
- **根本原因：** `maven-compiler-plugin` 的 `source`/`target` 版本设为 `1.7`，在 JDK 8+ 环境下编译失败（`Source option 7 is no longer supported`）
- **影响：** `docdoku-plm-sample-data` 模块无法编译，`loadSample.sh` 无法运行
- **修复状态：** `已修复`（commit `7f106dc`）
- **修复方案：** 将 `source`/`target` 改为 `1.8`

---

### [BUG-19] maven-war-plugin 版本过高导致 JDK 17+ 构建失败
- **文件：** `docdoku-plm-server/pom.xml`
- **根本原因：** `maven-war-plugin` 未锁定版本，Maven 自动拉取的最新版本与 JDK 17+ 不兼容，构建报错
- **影响：** JDK 17+ 环境下后端无法编译打包
- **修复状态：** `已修复`（commit `b884245`）
- **修复方案：** 锁定 `maven-war-plugin` 为 `3.3.2`

---

### [BUG-20] CDI 部署失败：缺少 `-parameters` 编译器标志
- **文件：** `docdoku-plm-server/pom.xml`
- **根本原因：** Payara/CDI 框架需要方法参数名信息（`-parameters` 编译标志）用于依赖注入，未加此标志时 CDI Bean 部署失败
- **影响：** 后端服务启动时 CDI 依赖注入报错，部分 Bean 无法部署
- **修复状态：** `已修复`（commit `9536a69`）
- **修复方案：** 在 `maven-compiler-plugin` 配置中添加 `<compilerArg>-parameters</compilerArg>`

---

### [BUG-21] JAXB API 缺失导致 swagger-maven-plugin 在 Java 11+ 下构建失败
- **文件：** `docdoku-plm-api/docdoku-plm-api-base/pom.xml`
- **根本原因：** Java 11 起 JAXB API 从 JDK 中移除，`swagger-maven-plugin` 依赖 JAXB，未显式声明依赖导致构建失败
- **影响：** API 模块在 Java 11+ 环境下无法构建
- **修复状态：** `已修复`（commit `53be8c0`）
- **修复方案：** 在 `pom.xml` 中显式添加 `jaxb-api` 依赖

---

### [BUG-22] BasicHeaderSAM 使用 javax.xml.bind.DatatypeConverter，Java 11+ 不可用
- **文件：** `docdoku-plm-server-rest/.../auth/modules/BasicHeaderSAM.java`
- **根本原因：** `javax.xml.bind.DatatypeConverter` 在 Java 9 后被标记废弃，Java 11 起从 JDK 移除，直接引用导致运行时 `ClassNotFoundException`
- **影响：** Java 11+ 环境下 Basic Auth 认证模块在类加载阶段即崩溃
- **修复状态：** `已修复`（commit `228008a`）
- **修复方案：** 替换为 `java.util.Base64`（JDK 标准库，无外部依赖）

---

### [BUG-23] pdfbox2-layout 依赖版本号错误，JitPack 无法解析
- **文件：** `docdoku-plm-server/pom.xml`
- **根本原因：** `pdfbox2-layout` 版本号写为 `1.0.0`，但 JitPack 上该库实际发布的最早版本 git tag 为 `v1.0.0`（含前缀 `v`），直接写 `1.0.0` 导致 Maven 依赖解析失败
- **影响：** 后端构建时 Maven 无法下载该依赖，编译失败
- **修复状态：** `已修复`（commit `7d4a64a`，升级至 `1.0.1`）
- **修复方案：** 升级版本到 JitPack 上实际存在的 `1.0.1`

---

### [BUG-24] BeanLocator 使用 javax.rmi.PortableRemoteObject，Java 11+ 已移除
- **文件：** `docdoku-plm-server-ejb/.../BeanLocator.java`（或相关 EJB 工具类）
- **根本原因：** `javax.rmi.PortableRemoteObject` 在 Java 11 起从 JDK 移除，直接引用导致编译或运行时失败
- **影响：** Java 11+ 环境下 EJB Bean 定位器无法使用
- **修复状态：** `已修复`（commit `af72886`）
- **修复方案：** 移除对该类的引用，改用兼容 Java 11+ 的替代方式

---

### [BUG-25] SPA 路由：nginx 缺少 try_files 导致刷新页面 404
- **文件：** `docdoku-plm-docker/front/nginx.conf`
- **根本原因：** 单页应用（SPA）的前端路由由 JavaScript 管理，nginx 未配置 `try_files` 时，直接访问或刷新非根路径（如 `/product-management/`）会返回 404
- **影响：** 用户刷新页面或通过书签直接访问子路径时页面空白/404
- **修复状态：** `已修复`（commit `8b0bd01`）
- **修复方案：** 添加 `try_files $uri $uri/ /index.html`

---

### [BUG-26] Adminer 4.7.1 与 PostgreSQL 13 不兼容（relhasoids 字段已移除）
- **文件：** `docdoku-plm-docker/docker-compose.yml`（Adminer 镜像版本）
- **根本原因：** PostgreSQL 12 起移除了 `pg_class.relhasoids` 系统列，Adminer 4.7.1 仍查询该列，导致 Adminer 连接 PostgreSQL 13 时报错崩溃
- **影响：** 无法通过 Adminer Web 界面管理数据库
- **修复状态：** `已修复`（commit `4c2de90`）
- **修复方案：** 升级 Adminer 至 `4.8.1`

---

## 八、前端国际化（i18n）Bug

### [BUG-27] 中文语言包（zh）缺失，界面默认显示英文
- **文件：** `docdoku-plm-front/app/js/localization/nls/`（缺少 `zh/` 子目录及相关文件）
- **根本原因：** 原始项目仅包含 `en`/`fr`/`ru` 三种语言，完全没有中文语言包
- **影响：** 中文用户访问系统时界面全为英文
- **修复状态：** `已修复`（commit `a55d9c4`、`fe2b503` 等，添加完整中文翻译）
- **修复方案：** 新增 `nls/zh/` 目录，翻译所有模块的 i18n 键值

---

### [BUG-28] locale 切换后界面不重载，仍显示旧语言
- **文件：** `docdoku-plm-front/app/js/common-objects/contextResolver.js`
- **根本原因：** `contextResolver.js` 在账户语言与当前页面 locale 不一致时，未触发页面重载，导致切换账户语言设置后界面语言不变
- **影响：** 用户在个人设置中切换语言后，界面不会切换到新语言，需手动刷新
- **修复状态：** `已修复`（commit `9475829`）
- **修复方案：** 检测到 locale 不匹配时自动调用 `location.reload()`

---

### [BUG-29] locale fallback 硬编码为 `zh`，导致无中文包时加载失败
- **文件：** `docdoku-plm-front/app/main/main.js`
- **根本原因：** `main.js` 中 locale 默认回退值设为 `'zh'`，但当时中文包尚未完整，回退到不存在的语言包导致 RequireJS 加载错误
- **影响：** 在中文包缺失时，系统初始化失败或界面空白
- **修复状态：** `已修复`（commit `d9ee650`，fallback 改为 `'en'`）

---

### [BUG-30] nginx 对 NLS 翻译文件设置了 1 年强缓存，语言包更新不生效
- **文件：** `docdoku-plm-docker/front/nginx.conf`
- **根本原因：** nginx 配置对所有静态资源设置 `Cache-Control: max-age=31536000`（1年），包括 `nls/` 翻译文件，导致更新翻译后浏览器继续使用旧缓存
- **影响：** 修改或新增翻译后，用户必须强制清除浏览器缓存才能看到新翻译
- **修复状态：** `已修复`（commit `d9ee650`，将 `nls/` 路径排除出长期缓存规则）

---

### [BUG-31] nginx NLS 文件响应缺少 `charset utf-8`，中文内容乱码
- **文件：** `docdoku-plm-docker/front/nginx.conf`
- **根本原因：** nginx 未设置 `charset utf-8`，部分浏览器以非 UTF-8 编码解析 JS 文件，导致中文字符串显示为乱码
- **影响：** 中文翻译文件在部分浏览器中乱码显示
- **修复状态：** `已修复`（commit `e3d75b7`）
- **修复方案：** nginx.conf 中添加 `charset utf-8` 及对应 MIME 类型配置

---

### [BUG-32] moment.js locale 映射错误：传入 `'zh'` 而非 `'zh-cn'`
- **文件：** `docdoku-plm-front/app/js/common-objects/utils/date.js`
- **根本原因：** `moment.locale('zh')` 在 moment.js 中无效，正确代码应为 `moment.locale('zh-cn')`，导致日期格式未按中文本地化显示
- **影响：** 中文环境下日期格式仍显示为英文格式
- **修复状态：** `已修复`（commit `d9ee650`）

---

## 九、后端 NPE（其他模块）

### [BUG-33] PartResource.createComponents：substitutes 列表为 null 时 NPE
- **文件：** `docdoku-plm-server-rest/.../rest/PartResource.java`
- **根本原因：** 创建零件组件时，请求体中 `substitutes` 字段为 null，直接遍历导致 NPE
- **影响：** 不含替代链接的零件组件创建请求触发 500
- **修复状态：** `已修复`（commit `010b540`）
- **修复方案：** null 时替换为空列表 `Collections.<PartSubstituteLink>emptyList()`

---

### [BUG-34] UpdatePartIterationPSFilter：零件过滤时 NPE
- **文件：** `docdoku-plm-server-ejb/.../filter/UpdatePartIterationPSFilter.java`
- **根本原因：** 更新零件迭代时，产品结构过滤器中存在 null 未检查
- **影响：** 特定条件下更新零件迭代触发 500
- **修复状态：** `已修复`（commit `6b555af`）

---

### [BUG-35] ProductManagerBean：isCheckoutByUser/isCheckoutByAnotherUser 调用顺序导致 NPE
- **文件：** `docdoku-plm-server-ejb/.../ProductManagerBean.java`
- **根本原因：** `checkOutUser.equals(user)` 中 `checkOutUser` 在零件未检出时为 null，应反转为 `user.equals(checkOutUser)`
- **影响：** 检查未检出零件的检出状态时触发 NPE
- **修复状态：** `已修复`（commit `1ccb925`）
- **修复方案：** 翻转 `equals()` 调用方，由非 null 的 `user` 调用

---

## 十、前端 UI Bug

### [BUG-36] 3D 查看器模型默认颜色为红色（0xff0000）
- **文件：** `docdoku-plm-front/app/product-structure/js/dmu/LoaderManager.js`
- **根本原因：** OBJ 文件加载后未指定材质时，默认使用 `0xff0000`（纯红色）作为 fallback 颜色
- **影响：** 无材质文件的 3D 模型显示为全红色，视觉效果差，难以辨别几何形状
- **修复状态：** `已修复`（commit `d531abb`）
- **修复方案：** 改为 `0xcccccc`（浅灰色）

---

### [BUG-37] 移动端/小屏幕折叠导航菜单项对齐错乱
- **文件：** `docdoku-plm-front/app/less/common/header.less`
- **根本原因：** 小屏媒体查询下 `.HeaderMenu` 缺少 `float: none`，折叠后菜单项浮动方向不正确，与面包屑菜单对齐错位
- **影响：** 在手机或窄屏浏览器下，折叠后的导航菜单布局错乱
- **修复状态：** `已修复`（commit `861fb3a`）
- **修复方案：** 在移动端断点的媒体查询内添加 `.HeaderMenu { float: none }`

---

## 十一、网络与反代 Bug

### [BUG-38] 外网/手机访问时提示"服务器不可用"
- **文件：** `docdoku-plm-docker/front/nginx.conf`、`env/front.json`
- **根本原因：** `webapp.properties.json` 中 `domain` 字段硬编码为固定 IP，外网或手机通过不同地址访问时，前端发出的 API 请求仍指向原硬编码地址，导致跨域或连接失败
- **影响：** 局域网以外的设备无法正常使用系统 API
- **修复状态：** `已修复`（commit `c259037`）
- **修复方案：** nginx 通过 `sub_filter` 将 `domain` 动态替换为请求方实际访问的 Host，并加入 `proxy_pass` 将 API 请求从 8000 转发到 `back:8080`

---

### [BUG-39] X-Forwarded-Proto 检测反代失效，DDNSTO 等穿透工具不注入该头
- **文件：** `docdoku-plm-docker/front/nginx.conf`
- **根本原因：** BUG-38 的修复方案依赖 `X-Forwarded-Proto` 头判断是否经过反代，但 DDNSTO 等内网穿透工具不会注入该头，导致检测逻辑失效，SSL/端口配置出错
- **影响：** 切换穿透工具后，外网访问再次出现"服务器不可用"
- **修复状态：** `已修复`（commit `e30beb7`）
- **修复方案：** 改为检测 Host 头是否含端口号（含端口=直连 HTTP，不含端口=经反代 HTTPS），对任意反代工具均成立，并保留 `X-Forwarded-Proto` 作为双重保险

---

### [BUG-40] loadSample.sh 工作空间重复创建时报 409 导致脚本中断
- **文件：** `docdoku-plm-sample-data/src/main/java/com/docdoku/loaders/SampleLoader.java`
- **根本原因：** `createWorkspace` 方法在工作空间已存在时服务器返回 HTTP 409（Conflict），但代码未处理该状态码，直接抛出异常中断脚本
- **影响：** `loadSample.sh` 不幂等，重复运行时报错退出，无法用于重置或补充数据
- **修复状态：** `已修复`（commit `d8a00ff`）
- **修复方案：** 捕获 409 响应并忽略（工作空间已存在视为成功）

---

*最后更新：2026-06-16*

---

## 十二、前端数值显示 Bug

### [BUG-41] 零件实例位置编辑框：极小浮点数科学计数法末尾被截断显示

- **文件：** `docdoku-plm-front/app/js/common-objects/views/part/cad_instance_view.js`
- **根本原因：** API 返回的 `tx`/`ty`/`tz`/`rx`/`ry`/`rz` 字段在 MATRIX 模式下来自 `RotationMatrix.getValues()`，CATIA 浮点运算会在理论为 0 的位置产生 `1e-14`～`1e-16` 量级的噪声值（如 `-9.8367310048985e-15`）。前端将该值直接填入固定宽度的 `<input>` 输入框，输入框宽度只能显示 `-9.8367` 等前几位，`e-15` 的科学计数法指数部分恰好被截断在可见区域之外，导致用户误以为该值是 `-9.8367 mm`，实为 `-9.8367 × 10⁻¹⁵ mm`（物理上为 0）。
- **影响：** 前端 BOM 编辑界面中，Translation (x y z) 和 Rotation (x y z) 输入框显示误导性数值，用户难以判断实际位置是否正确。
- **修复状态：** `已修复`
- **修复方案：** 在 `cad_instance_view.js` 的 `render()` 方法中，传给 Mustache 模板前先对 6 个坐标值做归零处理（`|v| < 1e-10` 时置为 0），仅影响显示层，不改动 model 存储的原始值和回写逻辑。同步修改了 `dist/product-structure/main.js` 和 `dist/product-management/main.js` 中的 minified 版本，并重建前端镜像。
  function clampNearZero(v, threshold) {
      threshold = threshold || 1e-10;
      return Math.abs(v) < threshold ? 0 : v;
  }
  ```

---

## 十三、3D 预览颜色 Bug

### [BUG-42] STEP 文件转换后 3D 预览颜色全部丢失，仅显示单一灰色

- **影响范围：** 所有通过 `.stp`/`.step` 上传的零件，在 3D 预览中颜色信息完全丢失，所有零件统一显示为灰色（`#cccccc`）
- **根本原因：** 颜色丢失跨三个阶段（详见历史记录）
- **修复状态：** `已修复（GLB 管线）`
- **修复内容（当前版本：STEP → GLB 单文件管线）：**
  1. **`convert_step_glb.py`**（替换旧 `convert_step_obj.py`）：使用 `cadquery-ocp`（OpenCASCADE 7.8）的 XDE `XCAFDoc_ColorTool` 在 headless 环境下读取 STEP 颜色；`BRepMesh_IncrementalMesh` 精度可控（相对弦差 5%）三角化；`pygltflib` 组装单一 `.glb` 文件（几何 + 材质颜色自包含）；多 solid 多色支持。关键修复：`read_step()` 必须将 `TDocStd_Document` 返回给调用方持有，否则 GC 会使所有 `TDF_Label` 失效（`shape.IsNull()` 返回 `true`，`collect_solid_colors` 返回 `[]`）。
  2. **`StepFileConverterImpl.java`**：调用 `convert_step_glb.py`，输出 `.glb`；修复 stdout/stderr 串行读取死锁（改为双线程并发消费，防止大文件 OS 管道缓冲区满时进程挂起）；完善 `pythonInterpreter=null` 时的错误提示；`InterruptedException` 后恢复线程中断标志。
  3. **`GeometryParser.java`**：扩展支持 GLB 包围盒解析（读取 glTF JSON chunk 中 accessor 的 `min`/`max` 字段聚合全局 AABB）；修复前包围盒全零导致 `InstancesWorker` 永远不加载几何（零件不可见）。
  4. **`GLTFLoader.js`**（新增）：Three.js r90 GLTFLoader 包装为 AMD 模块，放置于 `app/js/dmu/loaders/` 和 `dist/js/dmu/loaders/`。
  5. **`LoaderManager.js`**：替换 OBJLoader+MTLLoader 为 GLTFLoader，`parseFile()` 大幅简化；AMD factory 末尾必须有 `return`（遗漏会导致 `b is not a constructor` 运行时错误）。
  6. **`Dockerfile.jvm`**：基础镜像从已下架的 `openjdk:8-jre` 迁移到 `debian:bookworm-slim`，Python 从 2.7+FreeCAD 0.18 迁移到 3.11+cadquery-ocp；所有 wheels 离线打包进 repo（`wheels/` 目录）。
- **注意事项：**
  - 颜色颗粒度为 BREP solid 级别（整体色），face 级别多色暂不支持
  - Decimater LOD 降采样对 GLB 格式失效（仅支持 OBJ），日志出现 `Decimation failed`，不影响 LOD 0 正常显示
  - checkout 打断转换的问题已另行修复（见下方 BUG-43）

---

## 十四、转换回调被 checkout 状态打断

### [BUG-43] STEP 转换回调时零件已 checkin，几何写入被拒绝

- **影响范围：** 上传 STEP 后手动或自动 checkin，转换回调到达时 `isCheckedOut()=false`，几何和颜色数据全部丢弃，`conversion.succeed=false`
- **根本原因：** `ConverterBean.java:172` 的原始检查要求零件处于 checkout 状态才允许写入几何，逻辑上正确（防止覆盖已发布版本），但转换是异步的，用户或自动化流程在等待期间可能已 checkin
- **修复状态：** `已修复`
- **修复方案：** 若回调时零件未 checkout，先尝试自动 checkout（以当前用户身份）→ 写入几何 → 自动 checkin；若 checkout 因另一用户持锁而失败（`NotAllowedException`），则跳过写入并记录 WARN 日志（该情况极罕见，两用户同时操作同一零件版本）
- **修复文件：** `ConverterBean.java`（`handleConversionResultCallback` 方法，原 172 行附近）

---

## 十五、零件签出数据一致性 Bug

### [BUG-44] undoCheckOutPart 遗漏删除 BinaryResource DB 记录，导致再次签出报 CreationException

- **文件：** `docdoku-plm-server-ejb/.../ProductManagerBean.java`（`undoCheckOutPart` 方法，约第 415-438 行）
- **根本原因：**
  `undoCheckOutPart` 撤销签出时，会删除最新迭代（`partR.removeLastIteration()`）及其关联文件的存储数据（`storageManager.deleteData()`），但**遗漏了调用 `binaryResourceDAO.removeBinaryResource()`** 删除 `binaryresource` 表中对应的主键记录。
  导致文件路径形如 `{workspace}/parts/{partNumber}/{version}/{iteration}/nativecad/{fileName}` 的记录成为孤儿数据（`partiteration` 引用已删，`binaryresource` 记录残留）。
  下次签出时 `checkOutPart` 再次调用 `binaryResourceDAO.createBinaryResource()` 尝试插入同一主键，触发 PostgreSQL 唯一约束冲突：
  ```
  PSQLException: ERROR: duplicate key value violates unique constraint "binaryresource_pkey"
  ```
  该异常被 `CreationExceptionMapper` 捕获，前端收到 HTTP 400 `CreationException` 提示"创建对象时出错，该对象可能不唯一"。
- **影响：**
  - 受影响操作：对含 nativeCADFile 的零件执行"撤销签出" → 再次"签出"时必定报错
  - 装配体不受影响（无 nativeCADFile，不走该代码路径）
  - geometries / attachedFiles 同样存在相同 bug 模式，但路径包含迭代号，实际触发需特定条件
- **修复状态：** `已修复`（2026-06-16）
- **修复方案（代码）：** 在 `undoCheckOutPart` 中，对三类文件循环体内均补充 `binaryResourceDAO.removeBinaryResource(file)` 调用：
  ```java
  // geometries
  for (Geometry file : partIte.getGeometries()) {
      storageManager.deleteData(file);
      binaryResourceDAO.removeBinaryResource(file);  // 新增
  }
  // attachedFiles
  for (BinaryResource file : partIte.getAttachedFiles()) {
      storageManager.deleteData(file);
      binaryResourceDAO.removeBinaryResource(file);  // 新增
  }
  // nativeCADFile
  if (nativeCAD != null) {
      storageManager.deleteData(nativeCAD);
      binaryResourceDAO.removeBinaryResource(nativeCAD);  // 新增（根因所在）
  }
  ```
- **数据修复（已执行）：** 执行以下 SQL 清除存量孤儿记录（19 条）：
  ```sql
  DELETE FROM binaryresource
  WHERE fullname IN (
      SELECT br.fullname FROM binaryresource br
      LEFT JOIN partiteration pi ON pi.nativecadfile_fullname = br.fullname
      WHERE br.fullname LIKE '%/nativecad/%' AND pi.iteration IS NULL
  );
   ```

---

## 十六、FastAPI 后端迁移：DTO 对齐与权限校验 Bug

### [BUG-45] Pydantic `extra=forbid` + response_model 字段不匹配导致静默 500

- **文件：** `docdoku-plm-server-py/` 多处 `_*_dict` helper 与对应 schema
- **根本原因：**
  FastAPI 端点用带 `model_config = ConfigDict(extra='forbid')` 的 Pydantic schema 作 `response_model`，当 helper 返回的 dict 字段名/类型与 schema 不一致时，Pydantic 在响应序列化阶段抛 `ResponseValidationError` → HTTP 500，但 DB 事务可能已提交（数据已持久化，静默失败）。
- **影响：** 多个只读/写端点返回 500 或空数据，但操作实际已成功，前后端数据不一致。
- **修复状态：** `已修复`（2026-07-08，全部对齐 Payara Java DTO）
- **修复方案（7 项，铁律：以 Payara `docdoku-plm-server-rest/.../dto/*.java` 为准）：**
  1. **TaskDTO** — 删除 helper 多余键 `closingDate`（Payara 仅有 `closureDate`）`services/task_manager.py`
  2. **ACLDTO** — schema 由 `dict[str,str]` 改为 `List[ACLEntryDTO]`（{key,value}），对齐 Java `ACLDTO.java` 的 `userEntries`/`groupEntries`
  3. **WorkflowModelDTO** — 去掉 Payara 不存在的 `workspaceId`，改为实际字段 `reference`
  4. **TaskHolderDocDTO** — `tasks/{login}/documents` response_model 改为 `DocumentRevisionDTO`（Payara 返回精简版，`Tools.createLightDocumentRevisionDTO` 清空 tags/workflow）
  5. **ProductInstanceIterationDTO** — 删除 Payara 不存在的 `productBaselineId`（Payara 用嵌套 `basedOn`）
  6. **ProductInstanceMasterDTO** — 删除 Payara 不存在的 `workspaceId`
  7. **OrganizationDTO** — 补 Payara 实际存在的 `owner` 字段（`OrganizationResource` dozer 全量映射）
- **防御建议：** 新写 helper 前先查 Payara DTO 类，逐字段核对名称/类型/单复数；响应体 schema 慎用 `extra=forbid`。

---

### [BUG-46] check_write_access：acl_id=None 时未校验 workspace 写权限

- **文件：** `docdoku-plm-server-py/app/services/factory/acl_factory.py:75` 及 7 处调用点
- **根本原因：**
  `check_write_access` 在 `acl_id is None`（null ACL）时无条件 `return True`，任何 workspace 成员（含 readonly）都被视为有写权限。修复引入 `workspace_id` 参数后，仍有 7 处调用点未传该参数，null-ACL 场景权限绕过。
- **影响：** readonly 成员可对无 ACL 的文档/变更项/工作流模型执行写操作。
- **修复状态：** `已修复`（2026-07-08）
- **修复方案：** 补全所有调用点传 `workspace_id`：
  - `routers/milestones.py`、`routers/change_common.py`（helper 传 `item.workspace_id`）
  - `services/document_manager.py` delete_revision/checkout/checkin（传 `ws`）
  - `services/workflow_manager.py` `_check_write_access` 新增参数 + update_model/delete_model 传入
  - `services/change_manager.py` delete_item 一致性补全
- **验证：** pytest 176 passed / 1 skipped，线上 health ok，5 端点 200/204 无 500。

---

### [BUG-47] 零件迭代更新 500：实例属性跨迭代共享触发 FK 冲突

- **文件：** `docdoku-plm-server-py/app/services/product_manager.py`（`_copy_iteration_files` + `_sync_instance_attributes`）
- **根本原因（双层）：**
  1. 检出创建新迭代时（`_copy_iteration_files`），实例属性为**浅拷贝**——新迭代的 `partiteration_attribute` 关联复用旧迭代同一个 `instanceattribute` 行 id，未克隆底层行，导致多个迭代共享同一 `InstanceAttribute`（DB 实证 `GD50_Frame/A` 的 id 7352 被 iter1+iter2 共享）。
  2. 更新时（`_sync_instance_attributes`）无条件删除本迭代旧 `instanceattribute` 行，因另一迭代仍引用该共享行 → `ForeignKeyViolation fk_partiteration_attribute_instanceattribute_id`。
- **影响：** CATIA Copilot 同步更新带实例属性的零件（`PUT .../parts/{pn}-{ver}/iterations/{n}`）报 500，属性更新失败。
- **Java 比对：** Payara `ProductManagerBean.checkOutPart:553-560` 对每属性 `attr.clone()`+`createAttribute()`（persist 新行新 id）深拷贝独占；`PartIteration.java:130` `@OneToMany(orphanRemoval=true)` + 连接表以 ITERATION 为键，更新删除只影响当前迭代。确认修复方向正确。
- **修复状态：** `已修复`（2026-07-11）
- **修复方案：**
  - A（根治）：`_copy_iteration_files` 检出复制实例属性改为深克隆（`INSERT INTO instanceattribute ... SELECT ... WHERE id=:old RETURNING id` 复制全部值列，再用新 id 建关联）。
  - B（兜底 + 存量修复）：`_sync_instance_attributes` 删孤儿前先查是否仍被其它 `partiteration_attribute` 引用，共享则跳过删除；更新后该迭代切换到独立新行，存量坏数据自愈。
- **部署：** docker cp back-py + 重启，启动无导入错误。

---

### [BUG-48] 删除工作区遗漏 BinaryResource DB 行 + vault 磁盘文件，重建后上传 409

- **文件：** `docdoku-plm-server-py/app/routers/workspaces.py`（`delete_workspace`）
- **根本原因：**
  `delete_workspace` 只做按 `workspace_id` 的 DB 级联，遗漏两处二进制层：① `binaryresource` 表无 `workspace_id` 列（主键 `fullname` 路径），级联匹配不到，删除后残留（GD50 实测残留 102 行）；② 无任何 vault 磁盘文件删除，`vault/{ws}/` 文件夹整体保留。上传附件 `binary_storage.save_attached` 靠查 `BinaryResource.full_name` 是否存在判重 → 命中残留行抛 `FileAlreadyExistsException`（409）。
- **影响：** 删工作区→重建同名工作区→上传原有零件附件报 409 `文件已存在`。
- **Payara 比对：** `WorkspaceManagerBean.deleteWorkspace`（`@Asynchronous`）= `WorkspaceDAO.removeWorkspace`（DB，BinaryResource 靠 `PartIteration.nativeCADFile/attachedFiles/geometries` 的 JPA `orphanRemoval` 级联删除，DAO 内无显式 DELETE）+ `storageManager.deleteWorkspaceFolder`（`FileUtils.deleteDirectory(vaultPath/workspaceId)`）+ 删 ES 索引。
- **为何 Python 未自动删（精确表述）：** Python 模型**部分复刻**了 JPA 级联（`PartRevision.iterations`/`DocumentRevision.iterations`/`PathDataMaster.iterations`/`PartIteration.conversions` 均有 `cascade="all, delete-orphan"`），但**唯独未复刻 BinaryResource 的 orphanRemoval**——`part_iteration.py` 的 `native_cad_file`/`attached_files`/`geometries` 均无 `delete-orphan`，且后两者是 `secondary=` 多对多关系，SQLAlchemy 不允许在多对多上用 `delete-orphan`（删父只清中间表行，不删目标 BinaryResource）。加之 `delete_workspace` 走批量裸 SQL，完全绕过 ORM 工作单元，已复刻的级联也不触发。故须显式删 binaryresource + vault 以对齐 Payara 结果。
- **修复状态：** `已修复`（2026-07-11）
- **修复方案：**
  - A：级联末尾增 `DELETE FROM binaryresource WHERE fullname LIKE :p ESCAPE '\'`，前缀 `{ws}/%`，LIKE 转义（`_`→`\_`、`%`→`\%`）对齐 `WorkspaceDAO.java:130`。
  - B：`db.commit()` 后 `shutil.rmtree(VAULT_PATH/ws, ignore_errors=True)`，复刻 `deleteWorkspaceFolder`，失败仅记日志不回滚。
  - Python 保持同步删除（Payara 为 `@Asynchronous`）。
- **部署：** docker cp back-py + 重启；DB 校验转义 LIKE 精确匹配 GD50 的 102 行。

---

### [BUG-49] 删除文档 revision 的全局孤儿清理漏引用表 → 存在产品实例属性时 FK 500

- **文件：** `docdoku-plm-server-py/app/services/document_manager.py`（`delete_revision`）
- **根本原因：**
  删文档 revision 后做**全库全局**孤儿清理：`DELETE FROM instanceattribute WHERE id NOT IN (SELECT ... documentiteration_attribute) AND id NOT IN (SELECT ... partiteration_attribute)`。而 `instanceattribute.id` 实际被 **5 张表** FK 引用（全 `NO ACTION`）：`documentiteration_attribute`、`partiteration_attribute`、`prdinstiteration_attribute`、`pathdataiteration_attribute`、`attribute_namevalue`（LOV 子值反向 FK）。只排除前 2 张 → 当库中存在产品实例属性（`prdinstiteration_attribute` 有行）或路径数据属性时，删文档触发 `fk_prdinstiteration_attribute_instanceattribute_id`（或 pathdata/namevalue）FK 500。`documentlink` 同款全局 NOT-IN bug（被 4 张迭代表引用）。
- **影响：** 库中一旦有产品实例/路径数据属性，删任意文档（含无属性文档，因清理是全局的）即 500。批 4 smoke 暴露。
- **Payara 比对：** `DocumentManagerBean.deleteDocumentRevision:1226` → `DocumentRevisionDAO.removeRevision:155-171` → 逐迭代 `documentDAO.removeDoc → em.remove(pDoc)`；`DocumentIteration.java:104-116` 的 `instanceAttributes` 为 `@OneToMany(orphanRemoval=true, cascade=ALL)`，JPA **只级联删该迭代实体图内自己拥有的**属性（精确删除，非全局）；LOV 子值经 `InstanceListOfValuesAttribute.java:43-51` 的 `@ElementCollection(attribute_namevalue)` 随属性自动删。Python 的全局 NOT-IN 从设计上就偏离 Java 语义。
- **修复状态：** `已修复`（2026-07-12）
- **修复方案（方案B，与 Payara 语义对齐）：** 改为**精确删除**——收集本 revision 各迭代的 `instanceattribute_id`/`documentlink_id` → 删关联行 → 逐 id 检查无其它迭代仍引用才删本体；删 `instanceattribute` 前先删 LOV 子值 `attribute_namevalue`。彻底消除对 `prdinstiteration_attribute`/`pathdataiteration_attribute` 的误伤，并补上 `attribute_namevalue` 清理。`documentlink` 同法精确删除。
- **验证：** seed 一条产品实例属性（原 500 触发条件）+ 建带 text/LOV 属性+链接的文档 → `DELETE` **HTTP 204**（原 500）；DB 核文档自身属性+LOV namevalue+documentlink 已清，产品实例属性+关联**完整保留**。pytest 278 passed / 1 known-fail，无新增。commit 8457305。

---

*最后更新：2026-07-12*
