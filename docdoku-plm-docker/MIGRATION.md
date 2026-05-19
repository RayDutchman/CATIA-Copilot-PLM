# 数据迁移说明

## 数据存储方式对比

本项目不同数据采用不同的存储策略，原因如下：

### Named Volume vs Bind Mount

| | Named Volume | Bind Mount |
|---|---|---|
| 数据位置 | Docker 内部管理（`/var/lib/docker/volumes/`） | 宿主机指定目录（如 `./data/vault`） |
| 直接访问 | 不能，需通过容器 | 可以，就是普通文件夹 |
| 权限管理 | Docker 自动处理 | 容器内外 UID 可能不匹配 |
| 备份方式 | 需借助临时容器导出 | 直接 `cp` / `tar` |
| 适合场景 | 数据库等权限敏感服务 | 普通文件、需要直接访问的场景 |
| 性能 | 略好（Linux overlay2） | 略差（有宿主机 I/O 开销） |
| 迁移可靠性 | 高（数据库用 dump/restore） | 取决于文件是否有格式绑定 |

### 本项目的选择

| 数据 | 存储方式 | 原因 |
|---|---|---|
| **PostgreSQL（db-volume）** | Named Volume | PG 对文件权限极敏感；正确迁移方式永远是 `pg_dump`，与存储位置无关；直接复制原始文件跨版本会损坏 |
| **文件库 vault（./data/vault）** | Bind Mount | 内容是普通文件（CAD、PDF 等），无格式绑定；挂外面方便直接查看和备份 |
| **Elasticsearch（es-volume）** | Named Volume | 索引可重建，不是关键数据；named volume 省事 |
| **转换缓存（conversion-volume）** | Named Volume | 缓存数据，可丢弃，无需管理 |

---

## 目录结构

```
docdoku-plm-docker/
├── data/
│   └── vault/    # 上传文件库（bind mount，不入 git）
├── migrate.sh    # 迁移工具脚本
└── docker-compose.yml
```

数据库在 Docker named volume `docdoku-plm-docker_db-volume` 中，`data/` 目录已加入 `.gitignore`。

---

## 场景一：全新部署

无需任何额外操作，直接启动：

```bash
docker compose up -d
```

Docker 自动创建 named volume 和 `./data/vault/` 目录，PostgreSQL 首次启动自动初始化。

---

## 场景二：迁移到新机器

### 第一步：在旧机器上导出

```bash
cd docdoku-plm-docker
./migrate.sh export
```

生成两个文件：
- `backup_db.sql` — 数据库转储（文本格式，跨 PG 版本兼容）
- `backup_vault.tar.gz` — 文件库压缩包

### 第二步：传输到新机器

```bash
# 传整个项目目录（推荐）
scp -r docdoku-plm-docker/ user@new-machine:/path/to/

# 或者只传备份文件（新机器已有代码时）
scp backup_db.sql backup_vault.tar.gz user@new-machine:/path/to/docdoku-plm-docker/
```

### 第三步：在新机器上导入

```bash
cd docdoku-plm-docker
./migrate.sh import
```

---

## 日常备份

```bash
# 备份数据库
docker compose exec db pg_dump -U changeit docdokuplm > backup_$(date +%Y%m%d).sql

# 备份文件库（vault 是 bind mount，直接压缩）
tar czf vault_$(date +%Y%m%d).tar.gz -C data vault/

# 恢复数据库（先停服务）
docker compose down
docker compose up -d db && sleep 5
docker compose exec -T db psql -U changeit docdokuplm < backup_20260101.sql
docker compose up -d
```

---

## migrate.sh 命令说明

```bash
./migrate.sh export        # 导出数据库 + 文件库到当前目录
./migrate.sh import        # 从备份文件导入并启动服务
./migrate.sh from-volumes  # 一次性：将旧 named volume 数据迁入 ./data/vault
```
