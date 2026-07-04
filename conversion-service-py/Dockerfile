# conversion-service-py Dockerfile
#
# ⚠️  通过 build.sh 或直接 docker build 均可，所有材料已在本目录：
#   bash build.sh [docdoku/docdoku-plm-conversion-service:2.7.0-py]
#   或：docker build -t docdoku/docdoku-plm-conversion-service:2.7.0-py .
#
# Python-only 转换服务，替代原 Java/Quarkus 编排层。
#
# 使用 Python 3.11（与 wheels/ 目录中的 cp311 wheel 版本匹配）。
# 升级 Python 版本时需重新生成 cadquery-ocp 等大型 wheels。

FROM python:3.11-slim-bookworm

ARG CONVERTER_WHEELHOUSE_URL=""
ARG CONVERTER_PIP_INDEX_URL=""
ARG CONVERTER_PIP_EXTRA_INDEX_URL=""

# OCC 运行时所需共享库
RUN apt-get update -qqy \
 && apt-get install -qqy --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libxrender1 \
      libsm6 \
      libxt6 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件和安装脚本
COPY requirements.txt /tmp/requirements.txt
COPY install-python-deps.sh /tmp/install-python-deps.sh

# 复制预构建 wheels（cadquery-ocp 等离线安装，cp311 ABI）
COPY wheels/ /tmp/wheels/

# 步骤1：离线安装 OCC 核心依赖（来自 wheels/）
# 步骤2：从 PyPI 安装轻量级依赖（aiokafka/httpx/trimesh/pycollada/ifcopenshell）
RUN chmod +x /tmp/install-python-deps.sh \
 && if [ "$(ls /tmp/wheels/*.whl 2>/dev/null | wc -l)" -gt "0" ]; then \
      echo "[deps] 离线安装 OCC 核心依赖 (from wheels/)"; \
      python3 -m pip install --no-cache-dir \
        --no-index --find-links /tmp/wheels/ \
        cadquery-ocp vtk matplotlib pygltflib numpy; \
    else \
      CONVERTER_WHEELHOUSE_URL="${CONVERTER_WHEELHOUSE_URL}" \
      CONVERTER_PIP_INDEX_URL="${CONVERTER_PIP_INDEX_URL}" \
      CONVERTER_PIP_EXTRA_INDEX_URL="${CONVERTER_PIP_EXTRA_INDEX_URL}" \
      /tmp/install-python-deps.sh /tmp/requirements.txt; \
    fi \
 && echo "[deps] 在线安装编排依赖 (aiokafka, httpx, trimesh, pycollada, ifcopenshell)" \
 && python3 -m pip install --no-cache-dir \
      aiokafka==0.10.0 \
      httpx==0.27.2 \
      trimesh==4.4.3 \
      pycollada==0.9.3 \
      ifcopenshell==0.8.5 \
 && rm -rf /tmp/install-python-deps.sh /tmp/requirements.txt /tmp/wheels/

# 创建数据目录
RUN mkdir -p /data/vault /data/conversions

# 复制所有服务代码（均位于本目录，无外部依赖）
COPY main.py convert_step_glb.py converter.py convert_mesh.py ./

# 运行时环境变量（可被 docker-compose env_file 覆盖）
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092
ENV KAFKA_TOPIC=CONVERT
ENV KAFKA_GROUP_ID=conversions_group
ENV VAULT_PATH=/data/vault
ENV CONVERSIONS_PATH=/data/conversions
ENV ENDPOINT=http://back:8080/docdoku-plm-server-rest/api

VOLUME ["/data/vault", "/data/conversions"]
# 注意：此服务是纯 Kafka 消费者，不监听任何 TCP 端口，无 HTTP 端点。

ENTRYPOINT ["python3", "main.py"]
