# STEP → glTF/GLB 迁移方案

> **状态：已完成（2026-06-13）**
>
> 本文档为迁移过程中的设计规划，实际实施结果见 [`3d-preview-pipeline.md`](./3d-preview-pipeline.md)。
> 与规划的主要差异：Python 库从 `pythonocc-core`（apt）改为 `cadquery-ocp`（离线 wheels），基础镜像从 bullseye 改为 bookworm。

> 目标：用 glTF/GLB 替换现有的 OBJ+MTL 转换管线，解决几何精度不足（三角面粗糙）和颜色丢失两个问题。

---

## 背景与问题

### 当前管线的缺陷

| 问题 | 根因 |
|------|------|
| 几何精度差（面片粗糙） | `Mesh.export()` 使用固定偏差值三角化，无法控制精度 |
| 颜色丢失 | FreeCAD 0.18 headless 下 `ViewObject` 为 None，无法读颜色；OBJ+MTL 路径推断机制脆弱 |
| MTL 文件堆积 | 每次重新转换生成新 UUID 的 MTL，附件越来越多 |
| OBJ+MTL 两文件配对 | UUID 需前端推断，受鉴权 / XHR 拦截影响，容易失效 |

### glTF/GLB 的优势

- **单文件**（GLB）：几何 + 材质 + 颜色全部内嵌，前端只需请求一次
- **PBR 材质**：Three.js 的 `GLTFLoader` 原生支持，光照效果远优于 `MeshPhongMaterial`
- **可控精度**：pythonocc 三角化时可以设置弦差（chord deflection）和角度偏差，精度可调
- **OCC App 层颜色**：pythonocc 通过 `XDE`（`XCAFDoc_ColorTool`）在 headless 下直接读取 STEP 颜色，不依赖 GUI

---

## 技术选型

### 转换工具：pythonocc-core（Python OpenCASCADE 绑定）

- 底层是 OpenCASCADE 7.x，和 FreeCAD/build123d 用同一内核，但 Python 绑定直接暴露 OCC C++ API
- **颜色读取**：通过 `XCAFDoc_ColorTool` 读取 STEP AP214/AP242 的 face/solid 颜色，headless 完全可行
- **三角化精度控制**：`BRepMesh_IncrementalMesh(shape, deflection, isRelative, angular_deflection)` 可精确控制
- **GLB 导出**：通过 `pygltflib`（轻量级 glTF 序列化库）组装几何 + 材质输出 `.glb`
- Debian bullseye 的 apt 有 `python3-pythonocc-core`（OCC 7.5），或者 pip 安装

### Three.js GLTFLoader：r90 兼容版本

Three.js r90 官方仓库中有 `GLTFLoader`（`examples/js/loaders/GLTFLoader.js`），支持：
- glTF 2.0 基础几何
- `pbrMetallicRoughness` 材质（漫反射颜色 `baseColorFactor`）
- GLB 二进制格式

不需要升级 Three.js 版本。

---

## 架构变化对比

### 当前架构

```
STEP → FreeCAD Mesh.export() → .obj
                             → .mtl (新增，uuid 随机)
     → partiteration_geometry (存 .obj 路径)
     → binaryresource attachedfiles (存 .mtl 路径)

前端：
  OBJLoader(.obj) + MTLLoader(推断 .mtl URL) → mesh
  推断路径：geometry URL 去掉扩展名 + '.mtl'（不可靠）
```

### 目标架构

```
STEP → pythonocc XDE 读颜色
     → BRepMesh 三角化（可控精度）
     → pygltflib 组装 → .glb（单文件，含颜色）
     → partiteration_geometry (存 .glb 路径)
     → binaryresource dtype='Geometry' (存 .glb)

前端：
  GLTFLoader(.glb) → mesh + 颜色（无需推断，无需 MTL）
```

---

## 实施步骤

### Phase 1：服务端转换脚本替换

**文件**：`docdoku-plm-conversion-service/conversion-service/src/main/resources/.../step/convert_step_obj.py`

重写为 `convert_step_glb.py`（同路径，同命名，Java 侧无感知），核心逻辑：

```python
# 伪代码
from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
from OCC.Core.XCAFDoc import XCAFDoc_ColorTool, XCAFDoc_ShapeTool
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
import pygltflib

# 1. 读 STEP + 颜色
reader = STEPCAFControl_Reader()
reader.ReadFile(input_file)
reader.Transfer(doc)
color_tool = XCAFDoc_ColorTool.ColorTool_s(doc.Main())
shape_tool = XCAFDoc_ShapeTool.ShapeTool_s(doc.Main())

# 2. 三角化（精度可调）
mesh = BRepMesh_IncrementalMesh(shape, deflection=0.05, isRelative=True, angDeflection=0.5)
mesh.Perform()

# 3. 提取三角面 + 法线
# 遍历 face → Poly_Triangulation → 顶点/法线/索引

# 4. 每个 solid 查颜色
color = Quantity_Color()
color_tool.GetColor(shape, XCAFDoc_ColorSurf, color)  # R, G, B in [0,1]

# 5. pygltflib 组装 GLB
# 每个 solid 一个 mesh primitive，材质用 pbrMetallicRoughness.baseColorFactor
gltf = pygltflib.GLTF2(...)
gltf.save_binary(output_file)
```

**精度参数**：
- `deflection=0.05`（弦差 5%，相对模型尺寸）：平滑曲面
- `angDeflection=0.3`（角度偏差 ~17°）：减少平面处的多余三角面

与旧脚本的接口完全相同（`-l -i -o` 参数），Java 侧 `StepFileConverterImpl.java` 无需改动。

### Phase 2：StepFileConverterImpl.java 小改

唯一改动：去掉 MTL 检测逻辑，因为 GLB 自包含，不再有伴随文件：

```java
// 删除：
// if (Files.exists(tmpMTLFile) && Files.size(tmpMTLFile) > 0) {
//     materials.add(tmpMTLFile);
// }

// 改回：
return new ConversionResultProxy(tmpOBJFile);
// tmpOBJFile 实际上是 .glb 文件，Java 只看路径不关心扩展名
```

### Phase 3：前端 GLTFLoader 替换

**3a. 添加 GLTFLoader**

从 Three.js r90 官方仓库提取 `GLTFLoader.js`，放到：
```
app/js/dmu/loaders/GLTFLoader.js
```

**3b. 注册别名（product-structure/main.js）**

```js
gltfloader: '../../js/dmu/loaders/GLTFLoader',
```

**3c. 重写 LoaderManager.js**

```js
define(['threecore', 'gltfloader', 'views/progress_bar_view'],
function (THREE, GLTFLoader, ProgressBarView) {

    parseFile: function (filename, texturePath, callbacks) {
        var loader = new GLTFLoader();
        loader.load(filename, function (gltf) {
            var object = gltf.scene;
            setShadows(object);
            callbacks.success(object);
        }, undefined, function (err) {
            callbacks.error && callbacks.error(err);
        });
    }
});
```

去掉 `updateMaterial`（GLB 自带材质，不需要 fallback 灰色）、去掉 MTL 推断逻辑。代码反而更少。

**3d. 更新 dist/product-structure/main.js**

同步修改 minified 版本中对应的 define 调用和 parseFile 函数。

### Phase 4：Dockerfile 换基础镜像安装 pythonocc

**当前**：`debian:buster-slim` + `freecad` + Python 2.7

**目标**：`debian:bullseye-slim` + `python3-pythonocc-core` + `python3-pygltflib`

Debian bullseye（11）：
- apt 有 `python3-pythonocc-core`（OCC 7.5 绑定）
- openjdk-11-jre-headless 同样可用
- assimp-utils 同样可用

Dockerfile 变化：
```dockerfile
FROM debian:bullseye-slim

RUN echo "deb http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list \
 && apt-get update -qqy \
 && apt-get install -qqy --no-install-recommends \
      openjdk-11-jre-headless \
      python3 \
      python3-pythonocc-core \
      python3-pip \
      assimp-utils \
      wget unzip \
 && pip3 install --no-cache-dir pygltflib \
 && rm -rf /var/lib/apt/lists/*
```

脚本改用 `python3` 调用（`conf.properties` 里的 `pythonInterpreter` 改为 `python3`，`freeCadLibPath` 参数不再需要，可留空或移除）。

### Phase 5：重建镜像 + 重新触发转换

```bash
# 构建新镜像
cd docdoku-plm-conversion-service
mvn package -DskipTests
docker build -f Dockerfile.jvm -t docdoku/docdoku-plm-conversion-service:2.6.2 .

# 重建前端镜像
cd docdoku-plm-front
docker build -f docker/Dockerfile -t docdoku/docdoku-plm-front:2.6.2 .

# 重新部署
cd docdoku-plm-docker
docker compose up --force-recreate --no-deps -d conversion front
```

重新上传 STEP 文件后触发转换，新管线生效。

---

## 风险与注意事项

| 风险 | 缓解措施 |
|------|---------|
| pythonocc-core 在 bullseye apt 中不存在 | 先验证：`docker run --rm debian:bullseye-slim apt-cache show python3-pythonocc-core` |
| GLTFLoader r90 版本不支持某些 glTF 2.0 特性 | 只使用基础几何 + `pbrMetallicRoughness`，不用动画/蒙皮等高级特性 |
| 三角化精度参数需调优 | 先用默认值测试，视实际效果调整 `deflection` |
| `canConvertToOBJ` 方法名误导性 | 方法名不影响功能，可以不改；或重命名为 `canConvert` |
| `conf.properties` 里的 `freeCadLibPath` 废弃 | 新脚本不使用 `-l` 参数，Java 侧传入空字符串即可，不影响流程 |

---

## 执行顺序

```
Phase 1: 验证 pythonocc bullseye 可用性（1条docker命令确认）
   ↓
Phase 4: 更新 Dockerfile（换 bullseye + pythonocc）
   ↓
Phase 1: 编写 convert_step_glb.py 并在容器内测试
   ↓
Phase 2: StepFileConverterImpl.java 移除 MTL 逻辑
   ↓
Phase 3: 添加 GLTFLoader + 重写 LoaderManager.js
   ↓
Phase 5: 重建两个镜像，部署，测试
```

---

## 不在本次范围内

- `ConverterBean.java:172` 的 checkout 检查问题（独立 bug，与颜色/精度无关）
- 其他格式（DAE/IFC）的转换，不受影响
- `partiteration_geometry` 表结构，无需改动

---

*计划创建时间：2026-06-13*
