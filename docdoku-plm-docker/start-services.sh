#!/bin/bash
# 按正确顺序启动 PLM 生产服务，跳过 back（Payara 已停用）和 kibana（按需手动启）
set -e
cd /home/chenweibo/CATIA-Copilot-PLM/docdoku-plm-docker

echo "[PLM] Starting zookeeper..."
docker compose up -d --no-deps zookeeper

echo "[PLM] Starting db, es, smtp..."
docker compose up -d --no-deps db es smtp

echo "[PLM] Waiting for zookeeper (up to 30s)..."
for i in $(seq 1 15); do
  docker exec docdoku-plm-docker-zookeeper-1 bash -c 'echo ruok | nc localhost 2181 2>/dev/null | grep -q imok' 2>/dev/null && echo "[PLM] zookeeper OK" && break || true
  sleep 2
done

echo "[PLM] Starting kafka..."
docker compose up -d --no-deps kafka

echo "[PLM] Starting front, back-py, conversion, adminer, ssl-proxy..."
docker compose up -d --no-deps front back-py adminer ssl-proxy

# conversion 依赖 kafka healthy，单独最后启
echo "[PLM] Starting conversion..."
docker compose up -d --no-deps conversion

echo "[PLM] All production services started. back(Payara) and kibana are intentionally skipped."
