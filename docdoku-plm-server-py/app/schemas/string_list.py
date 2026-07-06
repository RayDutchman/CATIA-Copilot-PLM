"""DTO: StringListDTO — JSON 序列化为字符串数组。"""
from __future__ import annotations
from pydantic import RootModel
from typing import List


StringListDTO = RootModel[List[str]]
