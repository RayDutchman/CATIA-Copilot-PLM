

* 此处将生成目录（本行将被自动移除）。
{:toc}

# 概述

PLM（产品生命周期管理）是一种以创建和维护产品为目标的管理方法，贯穿从产品及相关服务规格制定到产品报废的整个生命周期。（来源：维基百科）

PLM 是一种允许企业共享产品数据的策略，使所有利益相关方（员工、供应商、客户等）能够协作参与产品开发。

除传统 PLM 功能外，DocDokuPLM 还支持在各类终端（PC、Mac、Linux、平板、智能手机）上直接通过浏览器查看和协作数字模型（Catia、Inventor、AutoCAD、STEP、IFC、COLLADA、OBJ 等），无需安装任何软件或插件。

此外，DocDokuPLM 还提供细粒度访问权限管理、文档模板、以及通过图形化工作流编辑器实现的开箱即用 BPM（业务流程管理）等高级功能。

DocDokuPLM 是一款界面友好、操作符合人体工程学的工具。

本用户手册全面描述和解释了软件的使用方法，适合所有终端用户参考。

# 用户管理

要登录系统，每位用户都需要一个以登录名标识、密码保护的账户。

每位用户作为系统参与者，在其所属的每个工作区内拥有特定的访问权限，同时也可以参与业务流程。

## 创建用户

要创建账户，请点击首页上的"注册！"链接。

{% image /assets/images/documentation/en/register.png "注册链接"%}

第一步是填写注册信息，所有字段均为必填。

{% image /assets/images/documentation/2.0/en/register2.png "创建用户"%}

## 编辑用户

{% image /assets/images/documentation/2.0/en/settings.png "账户管理"%}

除用户 ID（不可修改）外，所有设置均可更改。

账户编辑页面可通过"我的账户"子菜单访问，该菜单同时提供密码重置功能。时区设置用于显示时间。

{% image /assets/images/documentation/2.0/en/edition.png "账户编辑"%}

# 工作区管理

## 创建工作区

账户创建完成后，即可创建新的工作区。

{% image /assets/images/documentation/en/creation.png "创建工作区"%}

工作区是汇聚文档、零件、业务流程和产品的顶层上下文对象，初始工作区管理员为创建者本人。

若不希望其他用户修改目录结构，请勾选"仅允许工作区管理员修改文件夹结构"选项。

## 工作区设置

要编辑工作区属性，请点击"工作区管理"。

{% image /assets/images/documentation/2.0/en/settings.png "账户管理"%}

然后选择要编辑的工作区。

{% image /assets/images/documentation/en/workspace.png "管理工作区"%}

您可以在用户级别管理工作区访问权限，也可以通过创建群组来管理。访问权限管理详见下一章节。

### 仪表盘

仪表盘提供工作区的统计信息（磁盘空间、文档和零件数量、每位用户的签出/签入情况等）。

{% image /assets/images/documentation/en/dashboard.png "Airplane-T01 工作区仪表盘"%}

## 协作消息

同一工作区内的所有用户可通过内置通信模块进行实时通信。该模块支持即时发起文字聊天或视频会议，用户可方便地交流零件和文档信息，从而加速产品开发流程。

协作者菜单列出当前在线用户（绿色）及其他用户，点击摄像机图标即可发起视频通话。

{% image /assets/images/documentation/en/coworkers.png "协作者菜单"%}

{% image /assets/images/documentation/en/videochat.png "视频通话邀请"%}

除协作者菜单外，当应用内出现蓝色用户名时，点击即可弹出上下文菜单。通过此方式发起的对话会将当前上下文（文档、零件）传递给对方，使其了解沟通主题。

{% image /assets/images/documentation/2.0/en/conversation.png "协作者上下文对话菜单"%}

# 访问权限控制

## 工作区访问权限

### 用户访问管理

工作区管理员可为用户设置完全访问或只读访问权限，也可以禁用用户（禁止其登录）。

{% image /assets/images/documentation/en/user_management.png "工作区用户管理"%}

此外，用户可被分配到持有权限的群组中。

完全访问用户可以：

* 创建、修改或删除文档和零件，
* 修改文件夹结构（若未限制为仅管理员可操作），
* 在文件夹间移动文档，
* 签出/签入文档和零件。

只读用户可以：

* 查看文档和零件，
* 查看产品结构和数字样机。

已禁用用户无法执行任何操作。

要更新用户或群组访问权限，勾选对应复选框后点击列表下方的操作按钮（移除、禁用、启用等）。

### 管理群组

当用户数量较多时，群组管理非常实用，可为群组统一设置权限。

点击群组名称即可打开详情视图，在此可添加或移除群组成员。

{% image /assets/images/documentation/en/group_user_management.png "群组用户管理"%}

## 访问控制列表

### 文档和零件

新创建的文档和零件默认遵循工作区级别的权限设置，但可通过"ACL"选项卡进行覆盖。在该面板中，您可以针对特定项（文档或零件）为工作区内的任意用户或群组升级或降级访问权限。最低级别为"禁止"，表示该用户或群组将无法看到该项。

{% image /assets/images/documentation/2.0/en/document_creation.png "文档创建 - ACL 选项卡"%}

只有工作区管理员和作者才能修改已有项的权限。选中项后，顶部横幅将出现以下图标：

{% image /assets/images/documentation/en/permissions.png%}

之后可按创建时的方式修改权限。

持有特定权限的项在行末显示禁止符号：绿色表示完全访问，黄色表示只读访问。

{% image /assets/images/documentation/2.0/full_access.png "完全访问"%}
{% image /assets/images/documentation/2.0/read_only.png "只读"%}

### 模板、工作流、配置、可交付成果

若您对已创建的模板拥有完全访问权限，可为工作区内的任意用户或群组修改其权限。设置只读权限后，用户或群组只能使用该模板；设置禁止权限后，用户或群组将无法看到该模板。

## 组合访问权限

重要概念：

* 访问权限优先级顺序：
  1. 用户对文档/零件的权限
  2. 群组对文档/零件的权限
  3. 用户对工作区的权限
  4. 群组对工作区的权限
  5. 最宽松群组的权限
* 在工作区被禁用的用户，访问权限设置无效。
* 工作区管理员的权限高于上述所有权限。

以下为各种组合情况的汇总表。

### 用户属于单个群组

| 群组权限 | 用户工作区权限 | 实际权限 |
| -------- | -------------- | -------- |
| 完全访问 | 只读           | 只读     |
| 完全访问 | 完全访问       | 完全访问 |
| 只读     | 只读           | 只读     |
| 只读     | 完全访问       | 完全访问 |

### 用户属于多个群组

| 群组 I 权限 | 群组 II 权限 | 实际权限 |
| ----------- | ------------ | -------- |
| 完全访问    | 完全访问     | 完全访问 |
| 完全访问    | 只读         | 完全访问 |
| 完全访问    | 禁用         | 完全访问 |
| 只读        | 禁用         | 只读     |
| 只读        | 只读         | 只读     |

### 用户对文档/零件的访问权限

| 用户工作区权限 | 用户对文档/零件的权限 | 实际权限 |
| -------------- | --------------------- | -------- |
| 完全访问       | 完全访问              | 完全访问 |
| 完全访问       | 只读                  | 只读     |
| 完全访问       | 禁止                  | 禁止     |
| 只读           | 完全访问              | 完全访问 |
| 只读           | 只读                  | 只读     |
| 只读           | 禁止                  | 禁止     |

### 群组对文档/零件的访问权限

| 群组工作区权限 | 群组对文档/零件的权限 | 实际权限 |
| -------------- | --------------------- | -------- |
| 完全访问       | 完全访问              | 完全访问 |
| 完全访问       | 只读                  | 只读     |
| 完全访问       | 禁止                  | 禁止     |
| 只读           | 完全访问              | 完全访问 |
| 只读           | 只读                  | 只读     |
| 只读           | 禁止                  | 禁止     |

# 文档管理

DocDokuPLM 提供完整的文档管理模块，包含全面的版本控制系统（主版本、修订版和迭代版）、文档共享与发布、树形视图与标签组织、ACL 配置等功能。以下将详细介绍各项功能。

{% image /assets/images/documentation/2.0/en/image00.png "文档管理菜单"%}

## 文档模板

### 创建文档模板

您可以创建用于实例化文档的模板，并通过填写掩码格式来限制文档命名规则。可用字符如下：

* 字母数字字符，
* '#' 代表任意有效数字，
* '*' 代表任意字符。

勾选标识符自动生成选项后，使用该模板创建的文档将自动生成标识符。若掩码中包含数字，标识符将自动递增。

{% image /assets/images/documentation/2.0/en/image25.png "文档模板创建表单"%}

### 添加工作流

为模板应用工作流后，以该模板实例化的新文档将自动套用该工作流。

### 添加文件和属性

您可以在模板中定义属性类型并附加文件。以相同模板创建的所有文档将拥有相同的属性集和附加文件。属性值可在各文档中分别设置，附加文件也将独立演进。

{% image /assets/images/documentation/2.0/en/image42.png "向模板附加文件"%}

## 创建文档

每个文档必须归属于某个文件夹。要在特定目录下创建新文档，需先选中该目录，再点击"新建文档"按钮。

{% image /assets/images/documentation/2.0/en/image09.png "文档创建表单"%}

创建文档时，可添加属性、指定工作流并设置特定访问权限。注意：创建流程完成前，无法上传文件或建立文档链接。

文档创建后，可执行以下操作：

* 签入/撤销签出/签出，
* 删除，
* 订阅文档状态变更通知（其他用户修改文档时，您将收到邮件提醒），
* 订阅迭代变更通知（有新迭代时收到通知），
* 为文档添加标签（如将文档标记为重要），
* 访问权限管理，
* 创建新版本，
* 公开或私密发布文档。

## 移动文档

点击下方图标可将文档移动到其他目录，将文档从图标处拖放到目标文件夹即可完成移动。

{% image /assets/images/documentation/2.0/document_move.png "移动按钮"%}

## 修改文档

要修改文档，必须先将其签出。点击列表中文档的标题即可打开文档修改窗口。

窗口左下角的箭头可浏览各历史迭代版本的变更记录。

点击"文件夹"信息链接可打开文档所在目录。

{% image /assets/images/documentation/2.0/en/image10.png "文档详情窗口"%}

### 文件选项卡

此选项卡用于关联文件。

{% image /assets/images/documentation/2.0/en/image52.png "文件视图"%}

DocDokuPLM 可从文档附件中生成 PDF 文件，支持大多数文字处理格式。

生成后，PDF 文件可通过永久链接打开，并自动添加包含以下信息的封面页：

{% image /assets/images/documentation/2.0/en/image61.png "自动生成的页面块标题"%}

支持的格式完整列表：odt、ods、odp、odg、odc、odf、odb、odi、odm、doc、docx、ppt、pps、txt、csv、xls、pdf、html、htm、xml、rtf、msg。

### 引用者选项卡

此视图列出将当前文档作为链接的所有文档和零件。

{% image /assets/images/documentation/2.0/en/image68.png "引用者视图"%}

## "已签出"和"任务"快捷链接

左侧菜单提供两个快捷链接，以便快速访问相关文档：

* 已签出：显示当前用户签出的所有文档。
* 任务：显示当前用户通过工作流直接参与的所有文档。

# 产品管理

DocDokuPLM 是面向协作产品开发的管理系统，旨在帮助同一组织的成员创建和交流产品相关数据。

产品管理模块提供以下主要功能：

* 配置管理，
* 产品结构浏览，
* 3D 数字样机可视化，
* 零件元数据管理，
* 零件-文档链接。

零件和产品的创建方法详见以下内容。

## 零件

产品的组成部分称为零件，由其他零件构成的零件称为装配体。在 DocDokuPLM 中，零件可从头创建，也可从 CAD 工具导入。

### 创建零件模板

有时需要确保零件始终包含预定义属性（工作流、CAD 文件、属性）或其编号遵循特定格式，此时需通过模板创建零件。

### 创建零件

如上所述，零件创建面板有可选的模板属性，还包括名称、描述、属性、工作流（见下方章节）和 ACL（访问控制列表）等输入字段。

{% image /assets/images/documentation/2.0/en/part.png "零件创建"%}

新创建的零件将添加到列表中。

{% image /assets/images/documentation/2.0/en/part_list.png "零件列表"%}

在列表中点击零件编号可打开详情窗口。在该窗口中（签出零件后），可修改属性、CAD 文件和文档链接。

选中零件后，可执行以下操作：

* 签出/撤销签出/签入，
* 删除，
* 为零件添加标签（如将零件标记为重要），
* 访问权限管理，
* 创建新版本，
* 发布，
* 设为废弃状态以冻结零件迭代（零件必须已发布）。

{% image /assets/images/documentation/2.0/obsolete_icon.png "废弃图标"%}

### 零件文件

此选项卡用于附加文件并为零件关联 CAD 文件。若选择新 CAD 文件时已有旧文件，旧文件将自动被替换。

{% image /assets/images/documentation/2.0/en/image51.png "文件视图"%}

DocDokuPLM 需将 CAD 文件转换为 obj 格式以支持 3D 可视化，添加 CAD 文件后将自动触发转换。若转换失败，可手动重试。

支持的格式完整列表：dxf、obj、off、ply、stl、3ds、wrl。

还可通过添加 png 或 jpg 格式的附加文件来添加纹理，纹理将在 3D 视图中显示。

### 零件装配

修改零件时，可编辑装配组成。装配体由其他零件（子零件）构成。

{% image /assets/images/documentation/2.0/en/part_assembly.png "零件装配"%}

子零件可以是可选的，并可设置替代件。要为子零件添加替代件，进入其视图后将出现新操作：创建新零件作为替代件或添加已有零件。

{% image /assets/images/documentation/2.0/en/image59.png "添加替代零件"%}

添加后，替代件将如下图所示出现在子零件视图中。

{% image /assets/images/documentation/2.0/en/image60.png "已添加替代件"%}

### 通知

子零件的变更有时会影响装配体。装配体零件窗口中的"通知"选项卡提供子零件变更日志概览，帮助您管理潜在影响。

{% image /assets/images/documentation/2.0/en/image66.png "通知视图"%}

点击以下图标可直接打开零件详情窗口的"通知"选项卡。

{% image /assets/images/documentation/2.0/notifications_icon.png "通知快速访问"%}

要将某条修改通知标记为已处理，点击其旁边的"标记为已核实"链接。

{% image /assets/images/documentation/2.0/en/image67.png "已核实通知"%}

注意：清空列表的唯一方式是为装配体零件创建新迭代。

### 引用者

此视图列出：

* 将该零件作为子组件（组件或替代件）的装配体，
* 将该零件作为子组件（根零件、节点或叶节点）的产品和可交付成果。

{% image /assets/images/documentation/2.0/en/image69.png "引用者视图"%}

### 查询构建器

若需显示自定义零件列表，可通过以下按钮进入查询构建器：

{% image /assets/images/documentation/2.0/query_builder.png "查询构建器按钮"%}

在显示的视图中，您可以：

* 按产品和/或可交付成果筛选零件列表，
* 选择要显示的字段（如零件编号、零件名称、属性等），
* 通过 where 子句包含或排除零件（至少定义一条），
* 对结果列表中的零件进行排序和分组。

{% image /assets/images/documentation/2.0/en/image80.png "查询构建器"%}

保存查询并选中后，可将结果导出为 Excel 文件，该功能非常适用于获取物料清单。

#### 筛选器

筛选器分为两种：

* 零件筛选器，
* 上下文筛选器。

零件筛选器用于按零件主版本/修订版数据进行筛选，包括：

* 零件编号，
* 零件名称，
* 作者，
* 零件迭代属性，
* 及其他零件相关数据。

上下文筛选器仅在 select 子句中添加了可交付成果上下文时出现。

这些筛选器用于在可交付成果数据属性范围内筛选结果列表，作为二次筛选（后置筛选），与零件筛选器形成"AND"条件关系。

注意：仅当存在带属性的可交付成果数据时，上下文筛选器才会出现。

您可以不使用任何筛选器（匹配所有查询），也可以只使用其中一种。

#### 运算符属性

不同属性类型对应不同的可用运算符。

##### 文本属性

文本属性支持以下运算符：

* 等于/不等于，
* 包含/不包含，
* 以...开头/不以...开头，
* 以...结尾/不以...结尾。

##### 数字属性

数字属性支持以下运算符：

* 等于/不等于，
* 小于/小于等于，
* 大于/大于等于，
* 介于。

##### 日期属性

日期属性支持以下运算符：

* 等于/不等于，
* 小于/小于等于，
* 大于/大于等于，
* 介于。

##### 长文本属性

长文本属性支持以下运算符：

* 等于/不等于，
* 包含/不包含，
* 以...开头/不以...开头，
* 以...结尾/不以...结尾。

##### 布尔属性

布尔属性支持以下运算符：

* 等于/不等于。

##### 零件编号属性

零件编号属性支持以下运算符：

* 等于/不等于，
* 包含/不包含，
* 以...开头/不以...开头，
* 以...结尾/不以...结尾。

##### 值列表属性

值列表属性支持以下运算符：

* 等于/不等于。

##### URL 属性

URL 属性支持以下运算符：

* 等于/不等于，
* 包含/不包含，
* 以...开头/不以...开头，
* 以...结尾/不以...结尾。

#### 高级筛选器用法

您可以组合使用多个筛选器，组合数量不受限制。

每条规则有两个按钮：

{% image /assets/images/documentation/2.5/en/qb-buttons.png "查询构建器规则按钮"%}

点击第一个按钮在当前规则组中添加规则，点击第二个按钮在当前规则组中添加规则组。

{% image /assets/images/documentation/2.5/en/complex-query.png "查询构建器复合查询"%}

#### 保存和导出查询

##### 保存查询

点击查询构建器底部的保存按钮可保存当前视图。查询无效时无法保存。保存后，工作区内所有用户均可见。

这些查询将出现在查询构建器顶部的下拉菜单中，从列表中选择查询后，所有字段将自动填充。

点击删除查询按钮可删除查询。

##### 导出查询

点击查询构建器底部的导出按钮可导出当前视图，将自动下载 .xls 文件。

点击查询下拉菜单旁边的导出按钮可导出已保存的查询（不考虑当前视图）。

### 快捷链接

左侧菜单提供已签出零件的快速访问入口。

{% image /assets/images/documentation/2.0/en/image50.png "链接区域"%}

## 产品

### 创建产品

创建产品需提供标识符和零件编号，描述为可选项。

零件编号指定产品的根零件，可以是单个零件或零件装配体。

{% image /assets/images/documentation/2.0/en/product_creation.png "产品创建表单"%}

新产品将添加到产品列表中。从列表中选择某项后，可执行删除和创建基线两种操作。

### 配置

配置是针对特定产品的装配选项列表，您可以：

* 在某个零件及其替代件之间进行选择，
* 若零件为可选项，则选择不包含该零件。

{% image /assets/images/documentation/2.0/en/image64.png "配置创建表单"%}

提供两种配置类型：

* 最新签入版，自动包含各相关零件的最新签入迭代版，
* 最新发布版，自动包含各相关零件的最新发布版本。

{% image /assets/images/documentation/2.0/en/image65.png "选择示例：无"%}

### 基线

基线是特定时间点整个产品结构的快照，用于管理同一产品的不同版本。

{% image /assets/images/documentation/2.0/en/image40.png "基线创建表单"%}

若选择的配置类型为"最新发布版"且存在多个版本，"版本"选项卡允许您选择较旧的版本。

{% image /assets/images/documentation/2.0/baseline_versions.png "版本选择"%}

此外，"配置"选项卡允许您选择特定配置，系统将自动填充所有配置选项，您也可以在"选项"选项卡中手动编辑。

{% image /assets/images/documentation/2.0/en/image58.png "选项选择"%}

### 用户自定义函数

您可能需要对产品或基线中的每个零件进行计算，例如计算总价格。点击以下按钮即可使用此功能：

{% image /assets/images/documentation/2.0/user_function_button.png "用户自定义函数按钮"%}

计算方式可以是求和或求平均值。您选择用于计算的属性（如重量），若某零件未定义该属性，则忽略该零件。

{% image /assets/images/documentation/2.0/en/image78.png "用户自定义函数视图"%}

### 可交付成果

可交付成果是基于产品基线、以序列号标识的产品实例。

创建可交付成果时可添加属性并设置特定访问权限。注意：创建流程完成前，无法上传文件或建立文档链接。

{% image /assets/images/documentation/2.0/en/image62.png "可交付成果创建表单"%}

要保留可交付成果的不同版本，可通过点击"重新基线"按钮创建新迭代，该按钮也允许您在确实需要时更改基线。

{% image /assets/images/documentation/2.0/en/image63.png "重新基线可交付成果"%}

### 导出文件为 ZIP

要与外部用户共享产品文件或在本地保存副本，可在产品/基线/可交付成果列表项中找到此实用功能。

{% image /assets/images/documentation/2.0/en/image79.png "导出文件"%}

您可以选择：

* 仅导出 CAD 文件，
* 仅导出关联文档中的文件，
* 导出零件及关联文档中的所有文件。

导出产品文件时，将获得各零件和文档最新迭代版中的附件；否则，将获得基线迭代版中的附件。

## 产品结构浏览器

点击上方图标可显示产品/基线/可交付成果的结构。

{% image /assets/images/documentation/2.0/product_structure.png "产品结构图标"%}

产品结构以分解形式展示产品的各组成部分，以树形视图呈现，每个节点代表一个可展开的装配体。

{% image /assets/images/documentation/2.0/tree_structure.png "产品树形结构"%}

点击节点本身可将其子零件以列表形式显示，点击节点右侧图标可打开节点的主要属性。

树形视图可用操作：

{% image /assets/images/documentation/2.0/refresh_tree.png "刷新树"%}
{% image /assets/images/documentation/2.0/toggle_comments.png "切换注释"%}

零件可用信息：

{% image /assets/images/documentation/2.0/optional.png "可选项"%}
{% image /assets/images/documentation/2.0/has_substitutes.png "有替代件"%}
{% image /assets/images/documentation/2.0/is_substitute.png "是替代件"%}

### 配置规格

您可以更改浏览器规格。查看搜索栏下方左上角菜单，提供 3 种浏览模式：

* "最新版本"：查看产品结构，子菜单可选择不同零件状态（进行中、最新签入版和最新发布版）。

{% image /assets/images/documentation/2.0/en/image70.png "产品模式示例"%}

* "基线"：查看基线结构，子菜单可选择指定产品的基线。

{% image /assets/images/documentation/2.0/tree_conf_baseline.png "基线模式示例"%}

* "序列号"：查看可交付成果结构，子菜单可选择可交付成果。

{% image /assets/images/documentation/2.0/en/image71.png "可交付成果模式示例"%}

### 路径数据

您可能需要为可交付成果零件关联特定数据（如序列号属性）。该功能可通过可交付成果结构浏览器访问，勾选零件旁边的复选框后将出现以下按钮：

{% image /assets/images/documentation/2.0/en/image72.png "路径数据按钮"%}

{% image /assets/images/documentation/2.0/en/image73.png "路径数据创建视图 - 属性选项卡"%}

编辑路径数据时可管理属性、文件和文档链接。若需保留变更历史，可点击"冻结当前迭代"按钮冻结当前迭代并创建新的可编辑迭代。

{% image /assets/images/documentation/2.0/en/image74.png "路径数据编辑视图 - 冻结迭代"%}

若零件已定义可交付成果数据，树形视图中该零件旁将出现以下图标：

{% image /assets/images/documentation/2.0/has_path_data.png "有路径数据"%}

### 类型化链接

在产品中，有时需要以特定方式链接零件，此时可使用类型化链接。这些链接有助于为产品定义新的结构，例如突出显示零件之间的电气连接。

在产品结构中勾选 2 个不同零件，将出现以下按钮：

{% image /assets/images/documentation/2.0/en/image75.png "类型化链接按钮"%}

点击该按钮后，可使用现有类型或新建类型来定义链接，该类型随后将用于显示新定义的产品连接：

{% image /assets/images/documentation/2.0/en/image76.png "类型选择"%}

任意链接均可编辑和删除。

### 零件搜索栏

对于复杂产品，在树形结构中定位零件可能较为繁琐。左上角的搜索栏允许您通过零件编号或名称快速找到零件。

{% image /assets/images/documentation/en/search_bar.png "搜索栏"%}

作为替代方案，也可以直接在 3D 场景中选择零件。

## 产品 3D 场景

点击上方图标可显示产品/基线/可交付成果的 3D 场景。

{% image /assets/images/documentation/2.0/3d_scene.png "3D 场景图标"%}

点击 3D 对象后，左侧面板中的结果将被选中，相关零件及其所有祖先节点将以黄色高亮显示，同时右侧面板将展示零件属性。当用户需要查找不知道编号的零件时，此功能非常实用。

{% image /assets/images/documentation/2.0/en/visualization.png "3D 模型可视化"%}

在树形视图中将零件切换为开/关状态，可在场景视图中显示/隐藏该零件。

{% image /assets/images/documentation/2.0/on_switch_button.png "切换按钮 - 开启状态"%}

3D 可视化模式下的可用操作：

* 创建标记（例如报告设计问题），
* 创建包含一组标记的图层，
* 导出零件的 3D 可视化（生成可嵌入其他网页的 HTML 代码，类似 YouTube 或 Google Maps），
* 测量两点间的距离。

# 工作流管理

工作流是需要完成的各项任务及其相互关系的可视化表示。这些操作被分配给同一工作区内的不同用户，并与特定的文档或零件关联。

## 角色

DocDokuPLM 工作流基于角色设计。为提高工作流模型的通用性，任务负责人不直接以用户名表达，而是通过角色来指定。

{% image /assets/images/documentation/2.0/edit_roles.png "角色按钮"%}

因此，创建工作流的第一步是定义工作区内使用的角色。这些角色可选择性地映射到默认用户或群组负责人。无论如何，当工作流模型被实例化并附加到文档或零件时，都有机会进一步细化这些映射关系。

{% image /assets/images/documentation/2.5/en/image32.png "角色定义面板"%}

## 工作流

### 工作流模板

工作流模板（或模型）列出从初始状态到最终状态的若干活动。每个活动包含标识其中间状态的标签和一组待完成任务，这些任务可以顺序执行或并行执行。

{% image /assets/images/documentation/2.0/add_workflow.png "工作流按钮"%}

顺序活动中，任务按序执行，若某任务被拒绝，当前活动将停止。

并行活动中，所有任务同时开启，可以任意顺序完成。被拒绝的任务不一定导致当前活动停止。并行活动有一个额外属性：推进到下一活动所需的已完成任务数，范围从 1 到任务总数。

验证活动将启动下一个活动；使活动无效将导致整个工作流挂起。

若活动未被验证且预先定义了恢复活动，工作流将进入恢复活动。

工作流模板可随时修改，不影响已实例化的工作流。

{% image /assets/images/documentation/2.0/en/image12.png "工作流模板创建"%}

编辑工作流时，可点击以下按钮进行复制：

{% image /assets/images/documentation/2.0/duplicate_workflow.png "复制工作流"%}

然后为新复制的工作流输入名称。

{% image /assets/images/documentation/2.0/en/image77.png "工作流复制"%}

### 工作流实例

创建文档或零件时，作者可选择要应用的工作流模板，并可重新指定所有相关角色。

{% image /assets/images/documentation/2.5/en/image41.png "文档创建时的角色定义"%}

文档或零件创建完成后，关联的工作流（如有）将在第一个活动启动。任务开启后，系统将向当前任务负责用户发送邮件，以便其批准、拒绝并签署。若任务分配给群组，邮件将发送给群组内所有用户。

### 生命周期状态

活动启动后，每位任务负责人将收到包含待完成任务完整描述的邮件。

{% image /assets/images/documentation/2.5/en/image46.png "在文档上实例化的工作流"%}

满足以下条件时，运行中的任务可被标记为已完成或已拒绝：

* 任务负责人至少下载过一次关联文件，
* 文档或零件已发布（未被签出）。

点击"签署"链接可添加签名块。

所有订阅了状态变更通知的用户将通过邮件收到通知。

无法更新或重置已分配到某项目的已停止工作流，重新启动的唯一方式是创建该项目的新版本并重新分配相同工作流。

## 里程碑

里程碑允许您为进行中的工作设置截止日期。

{% image /assets/images/documentation/2.0/en/image81.png "里程碑创建"%}

## 问题

此页面允许您按优先级报告项目中的问题。问题修复可以：

* 分配给某位用户，
* 关联在"受影响项"选项卡中添加的文档和/或零件，
* 归属于某个类别。

可用类别列表：适应性、纠正性、完善性、预防性。

{% image /assets/images/documentation/2.0/en/image82.png "问题创建"%}

## 变更请求

变更请求的操作方式与问题完全相同，此外还可关联问题。

{% image /assets/images/documentation/2.0/en/image83.png "请求创建"%}

## 变更单

变更单的操作方式与问题完全相同，此外还可关联变更请求。

{% image /assets/images/documentation/2.0/en/image84.png "变更单创建"%}

# 签出/签入

要锁定文档/零件以防止他人修改，选中后点击签出按钮即可，系统将创建一个新的迭代版本。可同时选择多个项以加快操作。

{% image /assets/images/documentation/image14.png "签出/撤销签出/签入按钮"%}

签出的项目不可被其他用户编辑，对他们显示为已锁定。要确认修改，需执行签入操作；也可通过撤销签出操作取消所有更改。

在签入（发布）项目时，可选择输入修订备注。若不需要填写备注，点击"忽略"按钮即可。

{% image /assets/images/documentation/2.0/en/image19.png "修订备注窗口"%}

所有这些操作也可在项目详情窗口的"迭代"选项卡中执行。

{% image /assets/images/documentation/2.0/en/image49.png "签入和取消签出按钮"%}

修订日期表示签入日期（若已签入）或签出日期（若已签出），修改日期则显示项目最后被修改的时间（包括修订备注）。

{% image /assets/images/documentation/2.0/status.png "已签出/已锁定/已签入状态"%}

# 值列表

DocDokuPLM 允许您预定义属性值（称为值列表），可将其用作文档、零件或模板的属性。要创建或编辑值，点击模板页面上的以下图标：

{% image /assets/images/documentation/2.0/edit_lov.png "值列表按钮"%}

例如，可为颜色创建专用属性值。

{% image /assets/images/documentation/2.0/en/image56.png "值列表窗口"%}

保存后，该列表可通过模板/项目详情窗口的"属性"选项卡访问。为模板/项目分配值列表时，将创建该列表的新实例。

{% image /assets/images/documentation/2.0/en/image57.png "值列表选择"%}

以下操作不被允许：

* 删除存在实例的值列表，
* 编辑值列表的实例。

# 查看器或永久链接

每个文档/零件都提供显示其最新修订版详情的永久链接。只需点击项目窗口的标题即可访问。

{% image /assets/images/documentation/en/image22.png %}

您可以浏览项目的所有属性并查看其附件。查看器支持多种格式：pdf、jpg、mp4、doc 等。查看器不支持的格式将直接下载。

{% image /assets/images/documentation/en/image02.png "文档永久链接"%}

# 文件管理

点击以下图标可打开文档/零件或模板详情窗口的"文件"选项卡。

{% image /assets/images/documentation/2.0/file_icon.png "文件快速访问"%}

点击小铅笔图标可重命名任意项目或模板关联的文件，点击确认按钮后新标题才会保存。

{% image /assets/images/documentation/2.0/file_rename.png "文件重命名"%}

点击文件名可下载文件，勾选相关复选框可删除文件。

{% image /assets/images/documentation/2.0/file_delete.png "文件删除"%}

请记得点击弹窗中的保存按钮以确认修改。

# 文档链接管理

在零件/文档编辑时，可方便地添加文档引用。链接可在项目修改窗口的"链接"选项卡中管理。

{% image /assets/images/documentation/2.0/en/image53.png "链接管理"%}

点击小铅笔图标可为文档链接添加注释，点击确认按钮后注释才会保存。

{% image /assets/images/documentation/2.0/en/image54.png "为链接添加注释"%}

# 标签

您可以为文档、零件、问题、变更请求和变更单添加标签。选中一个或多个项目后，点击标签图标：

{% image /assets/images/documentation/en/image27.png %}

在标签管理窗口中，可添加已有标签或新建标签。

{% image /assets/images/documentation/2.0/en/image34.png "标签窗口"%}

要显示与特定标签关联的项目，从左侧菜单选择该标签即可。

{% image /assets/images/documentation/en/image37.png "标签选择"%}

要删除标签，点击标签区域右侧箭头，然后点击"删除"。标签将被移除，但关联项目不受影响。

{% image /assets/images/documentation/en/image39.png "标签删除"%}

# 搜索

搜索分为两种类型：快速搜索和高级搜索。

## 快速搜索

快速搜索栏位于文档/零件列表顶部，可通过名称、类型、标识符、版本、作者、创建日期、修改日期、属性、文件内容快速找到项目。

{% image /assets/images/documentation/en/image08.png "快速搜索栏"%}

## 高级搜索

访问高级搜索有两种方式：

* 通过左侧菜单的"搜索"链接（仅限文档），
* 通过快速搜索栏的小箭头。

高级搜索允许通过以下多个文本输入项查找项目：

* 名称，
* 类型，
* 标识符，
* 版本，
* 作者，
* 创建或修改日期，
* 属性，
* 文件内容。

{% image /assets/images/documentation/2.0/en/image30.png "高级搜索"%}

# 分享与发布

## 发布

每个文档/零件均可发布。点击项目列表行右侧的图标即可。

{% image /assets/images/documentation/en/publish.png %}

将出现以下窗口：

{% image /assets/images/documentation/2.0/en/image21.png "发布窗口"%}

启用公开分享后，该项目将可通过互联网公开访问。

## 私密访问

您也可以生成一个可选择性地设置密码或过期日期的私密链接。填写密码和/或过期日期后点击分享按钮即可。

{% image /assets/images/documentation/en/image07.png "私密分享"%}

生成的链接经过混淆处理，无法被猜测。

{% image /assets/images/documentation/en/image48.png "生成的链接"%}
