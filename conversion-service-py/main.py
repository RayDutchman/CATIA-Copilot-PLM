#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — Python-only 转换服务编排层

替代原有的 Java/Quarkus 编排层（App.java 等 10 个文件）。

职责：
  1. 通过 aiokafka 消费 Kafka topic CONVERT 的 ConversionOrder JSON 消息
  2. 从 vault 读取 STEP 文件，在进程内直接调用 convert() 进行 STEP→GLB 转换
  3. 通过 httpx 将 ConversionResultDTO 回调后端 REST API
  4. 显式手动 offset 提交（处理完成后才 commit）

关键配置（全部通过环境变量注入）：
  KAFKA_BOOTSTRAP_SERVERS   Kafka 地址（默认 kafka:9092）
  KAFKA_TOPIC               Kafka topic（默认 CONVERT）
  KAFKA_GROUP_ID            消费组 ID（默认 conversions_group）
  VAULT_PATH                vault 根目录（默认 /data/vault）
  CONVERSIONS_PATH          临时转换目录（默认 /data/conversions）
  ENDPOINT                  后端 REST API 根地址（默认 http://back:8080/docdoku-plm-server-rest/api）
"""

import asyncio
import json
import logging
import os
import shutil
import uuid
from pathlib import Path

import httpx
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from converter import ConversionError, convert, unaccent, ALL_EXTENSIONS

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("conversion-service")

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC     = os.environ.get("KAFKA_TOPIC",             "CONVERT")
KAFKA_GROUP_ID  = os.environ.get("KAFKA_GROUP_ID",          "conversions_group")
VAULT_PATH      = os.environ.get("VAULT_PATH",              "/data/vault")
CONVERSIONS_PATH = os.environ.get("CONVERSIONS_PATH",       "/data/conversions")
ENDPOINT        = os.environ.get("ENDPOINT",                "http://back:8080/docdoku-plm-server-rest/api")

# ---------------------------------------------------------------------------
# vault 路径构建（对齐 Java Tools.unAccent() 修复后行为）
# ---------------------------------------------------------------------------

def get_virtual_path(full_name: str) -> str:
    """
    复现 Java FileStorageProvider.getVirtualPath() 逻辑：
      vault_path + "/" + Tools.unAccent(fullName)

    full_name 示例：
      "GD50/parts/Outer Plate 2010/A/2/nativecad/Outer Plate 2010.stp"
    返回：
      "/data/vault/GD50/parts/Outer Plate 2010/A/2/nativecad/Outer Plate 2010.stp"
    """
    return VAULT_PATH + "/" + unaccent(full_name)


# ---------------------------------------------------------------------------
# 回调后端
# ---------------------------------------------------------------------------

async def send_result(token: str, workspace_id: str, part_number: str,
                      part_version: str, payload: dict) -> None:
    """
    PUT {ENDPOINT}/workspaces/{workspaceId}/parts/{partNumber}-{partVersion}/conversion
    Authorization: Bearer {token}
    Content-Type: application/json

    payload 对应 ConversionResultDTO 字段（见后端 ConverterBean 期望的契约）。
    """
    url = f"{ENDPOINT}/workspaces/{workspace_id}/parts/{part_number}-{part_version}/conversion"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.put(url, json=payload, headers=headers)
        if resp.status_code in (401, 403):
            # JWT expiry is a known risk — token is from upload session, may expire during long conversion.
            # Root fix: backend should provide service-to-service auth for conversion callbacks.
            raise RuntimeError(
                f"Callback auth failed HTTP {resp.status_code} (JWT may have expired): "
                f"{resp.text[:200]}"
            )
        if resp.status_code not in (200, 204):
            raise RuntimeError(
                f"Callback failed HTTP {resp.status_code}: {resp.text[:200]}"
            )
    logger.info("Callback OK: %s-%s", part_number, part_version)


async def send_error(token: str, workspace_id: str, part_number: str,
                     part_version: str, error_msg: str) -> None:
    """Send error result to backend to mark conversion as failed."""
    payload = {"errorOutput": error_msg}
    try:
        await send_result(token, workspace_id, part_number, part_version, payload)
    except Exception as e:
        logger.error("Error callback also failed: %s", e)


# ---------------------------------------------------------------------------
# 处理单条转换消息
# ---------------------------------------------------------------------------

async def handle_order(order: dict) -> None:
    """
    处理一条 ConversionOrder 消息。

    order 字段（对应 Java ConversionOrder.java）：
      partIterationKey.workspaceId
      partIterationKey.partMasterNumber
      partIterationKey.partRevisionVersion
      partIterationKey.iteration
      binaryResource.fullName   （vault 相对路径）
      binaryResource.name       （文件名）
      userToken                 （JWT）
    """
    try:
        key    = order["partIterationKey"]
        ws     = key["workspaceId"]
        number = key["partMasterNumber"]
        ver    = key["partRevisionVersion"]
    except (KeyError, TypeError) as e:
        logger.error("ConversionOrder missing required fields, skipped: %s", e)
        return

    token = order.get("userToken", "")
    if not token:
        logger.error("Missing userToken, skipping %s-%s", number, ver)
        return

    binary = order.get("binaryResource", {})
    full_name = binary.get("fullName", "")
    file_name = binary.get("name", "")

    ext = Path(file_name).suffix.lstrip(".").lower()
    if ext not in ALL_EXTENSIONS:
        logger.warning("Unsupported file type %s, skipping %s-%s", ext, number, ver)
        return

    input_path = get_virtual_path(full_name)
    if not os.path.exists(input_path):
        msg = f"Vault file not found: {input_path}"
        logger.error(msg)
        await send_error(token, ws, number, ver, msg)
        return

    # 创建独立临时目录（UUID 命名，对齐 Java App.java 逻辑）
    temp_uuid = str(uuid.uuid4())
    temp_dir  = Path(CONVERSIONS_PATH) / temp_uuid
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Conversion started: %s-%s  tempDir=%s", number, ver, temp_uuid)

    glb_uuid     = str(uuid.uuid4())
    glb_filename = glb_uuid + ".glb"
    glb_path     = str(temp_dir / glb_filename)

    try:
        result = convert(input_path, glb_path)
        logger.info(
            "LOD 0 done: %s-%s  solid=%d  bbox=%s",
            number, ver, result["solid_count"],
            [round(v, 2) for v in result["bbox"]],
        )
    except ConversionError as e:
        err_str = str(e)
        # 空几何体视为成功跳过（对齐后端 ConverterBean 逻辑）
        if "no geometry generated" in err_str.lower():
            logger.info("Empty geometry, marking succeed=true: %s-%s", number, ver)
            await send_result(token, ws, number, ver, {
                "tempDir":           temp_uuid,
                "convertedFileLODs": {},
                "errorOutput":       "no geometry generated",
            })
            # 空几何体无 GLB 文件，直接清理空临时目录
            shutil.rmtree(str(temp_dir), ignore_errors=True)
        else:
            logger.error("Conversion failed: %s-%s  error=%s", number, ver, err_str)
            await send_error(token, ws, number, ver, err_str)
        return
    except Exception as e:
        logger.exception("Conversion exception: %s-%s", number, ver)
        await send_error(token, ws, number, ver, str(e))
        return

    bbox = result["bbox"]

    # LOD 生成（对齐 Java Decimater.java 三级细节设计，通过 deflection 控制三角化精度）
    # LOD 0: deflection=0.05（已完成，最高精度）
    # LOD 1: deflection=0.30（中等，远景查看）
    # LOD 2: deflection=1.00（低精度，缩略图/大场景）
    # 单个 LOD 失败不阻塞主流程，降级为已有 LOD 集合
    converted_lods: dict = {"0": glb_filename}
    LOD_SPECS = [("1", 0.30), ("2", 1.00)]
    for lod_key, lod_deflection in LOD_SPECS:
        lod_uuid = str(uuid.uuid4())
        lod_filename = lod_uuid + ".glb"
        lod_path = str(temp_dir / lod_filename)
        try:
            convert(input_path, lod_path, deflection=lod_deflection, angular=0.5)
            lod_size = os.path.getsize(lod_path)
            logger.info(
                "LOD %s done: %s-%s  deflection=%.2f  size=%dKB",
                lod_key, number, ver, lod_deflection,
                lod_size // 1024,
            )
            converted_lods[lod_key] = lod_filename
        except Exception as lod_err:
            logger.warning("LOD %s generation failed, degraded: %s", lod_key, lod_err)

    # 构造 ConversionResultDTO payload（与后端 Dozer 反序列化契约对齐）
    # - tempDir:           仅 UUID 目录名，后端会用 serverConfig.conversionsPath 拼成绝对路径
    # - convertedFileLODs: {"0": "xxx.glb", "1": "...", "2": "..."}（key=质量等级，与 Java 版一致）
    # - box:               [xMin, yMin, zMin, xMax, yMax, zMax]
    payload = {
        "tempDir":           temp_uuid,
        "convertedFileLODs": converted_lods,
        "box":               bbox,
    }

    try:
        await send_result(token, ws, number, ver, payload)
        # 回调成功后清理临时目录（后端已完成文件读取并存入 vault）
        try:
            shutil.rmtree(str(temp_dir), ignore_errors=True)
            logger.info("Temp dir cleaned: %s", temp_uuid)
        except Exception as e:
            logger.warning("Failed to clean temp dir: %s", e)
    except Exception as e:
        # 保留 temp_dir：callback 失败时后端未读取文件，保留供 PendingConversionsCleaner 或手工补救
        logger.error("Callback failed: %s-%s  %s", number, ver, e)


# ---------------------------------------------------------------------------
# Kafka 消费主循环
# ---------------------------------------------------------------------------

async def main_loop() -> None:
    logger.info(
        "Starting conversion service  bootstrap=%s  topic=%s  group=%s",
        KAFKA_BOOTSTRAP, KAFKA_TOPIC, KAFKA_GROUP_ID,
    )
    logger.info("VAULT_PATH=%s  CONVERSIONS_PATH=%s  ENDPOINT=%s",
                VAULT_PATH, CONVERSIONS_PATH, ENDPOINT)

    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=KAFKA_GROUP_ID,
        # 手动提交 offset：消息处理完才 commit，避免"消费但不处理"
        enable_auto_commit=False,
        # 仅首次加入（无已提交 offset）时从最新消息开始
        auto_offset_reset="latest",
        # 每次最多取 1 条，避免大批量消息超时问题（对齐旧方案单条处理）
        max_poll_records=1,
        # value 保留原始 bytes，由我们手动 JSON 解析
        value_deserializer=None,
        # 防止同步转换阻塞导致心跳超时 → session 过期 → commit 失败 → infinite loop
        session_timeout_ms=60000,       # 默认 10s → 60s（转换耗时 ~31s）
        heartbeat_interval_ms=10000,    # 默认 3s → 10s
        max_poll_interval_ms=300000,    # 显式声明（默认即为 5min）
    )

    await consumer.start()
    logger.info("Kafka consumer started, waiting for messages...")
    try:
        async for msg in consumer:
            logger.info(
                "Message received  partition=%s  offset=%s",
                msg.partition, msg.offset,
            )
            try:
                order = json.loads(msg.value.decode("utf-8"))
            except Exception as e:
                logger.error("JSON parse failed, skipped  offset=%s  error=%s", msg.offset, e)
                try:
                    await consumer.commit()
                except Exception:
                    pass
                continue

            try:
                await handle_order(order)
            except Exception:
                logger.exception("Unhandled exception in handle_order  offset=%s", msg.offset)
            finally:
                # 无论处理是否成功，提交 offset 避免无限重试同一条损坏消息。
                # commit() 失败（如 Kafka 临时不可用）只记录警告，不终止消费循环。
                try:
                    await consumer.commit()
                except Exception as commit_err:
                    logger.warning(
                        "Offset commit failed (retry on next poll)  offset=%s  error=%s",
                        msg.offset, commit_err,
                    )
    finally:
        await consumer.stop()


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 确保 CONVERSIONS_PATH 存在
    os.makedirs(CONVERSIONS_PATH, exist_ok=True)
    asyncio.run(main_loop())
