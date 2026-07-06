"""HashUtils — 哈希工具。"""
import hashlib

def md5_hex(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()
