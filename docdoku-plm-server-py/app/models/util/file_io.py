"""FileIO — 文件 IO 工具。"""
import os

def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()
