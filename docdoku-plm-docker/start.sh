#!/bin/sh
#
# 本脚本用于首次部署初始化，以及后续的容器启动。
#
# 功能：
#   - 创建 data 目录（用于存储上传的文件，映射到 docdoku-plm-server-volume）
#   - 生成密钥库文件（Keystore，Payara 应用服务器所需）
#   - 启动全部容器
#
# 前置要求：
#   前端和后端 Docker 镜像必须已提前本地构建，请参见根目录的
#   WSL2-Docker-Engine-Deployment-Guide.md 完成第八步和第九步。
#
#   ⚠️  本脚本不会从 DockerHub 拉取镜像。若需要拉取（通常不需要），
#       请手动执行 docker compose pull，但这会覆盖你本地构建的镜像。
#
# 用法：
#   cd /path/to/CATIA-Copilot-PLM/docdoku-plm-docker
#   bash start.sh
#
# 后续重启（不需要重新初始化时）：
#   docker compose up -d
#

# 出错即退出
set -e

# ── 密钥库参数（生产环境请修改）──────────────────────────────
STOREPASS=changeit
KEYPASS=changeit
KEYALIAS=mykeyalias
STORETYPE=PKCS12
KEYALG=AES
KEYSIZE=256

# ── 创建 data 目录并绑定 Docker 卷 ──────────────────────────
if [ -d data ]; then
    echo '[ok] data 目录已存在'
else
    echo '[init] 创建 data 目录...'
    mkdir data
fi

# 若卷不存在则创建（绑定到 ./data，使上传文件对宿主机可见）
if docker volume inspect docdoku-plm-server-volume > /dev/null 2>&1; then
    echo '[ok] docdoku-plm-server-volume 已存在'
else
    echo '[init] 创建 docdoku-plm-server-volume...'
    docker volume create --driver local \
        --opt type=none \
        --opt device="$(pwd)/data" \
        --opt o=bind \
        docdoku-plm-server-volume
fi

# ── 生成密钥库（如已存在则跳过）────────────────────────────
if [ -f keystore ]; then
    echo '[ok] 密钥库文件已存在'
elif [ -d keystore ]; then
    echo '[ok] 密钥库目录已存在（可使用空目录挂载，跳过生成）'
else
    echo '[init] 生成密钥库...'
    keytool \
        -genseckey \
        -keystore "$(pwd)/keystore" \
        -storetype ${STORETYPE} \
        -alias ${KEYALIAS} \
        -keyalg ${KEYALG} \
        -keysize ${KEYSIZE} \
        -storepass ${STOREPASS} \
        -keypass ${KEYPASS}
fi

# ── 启动全部容器 ─────────────────────────────────────────────
echo '[start] 启动所有容器...'
docker compose up -d --force-recreate --remove-orphans

echo ''
echo '✅ 启动完成。后端冷启动约需 1-3 分钟，可用以下命令查看进度：'
echo '   docker compose logs -f back'
echo ''
echo '   前端地址：http://localhost:8000'