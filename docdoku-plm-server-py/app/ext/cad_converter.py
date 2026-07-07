"""CAD 转换器抽象基类（对标 CADConverter）。

插件式转换框架：子类实现 convert()，通过 type/capabilities 描述能力。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversionInput:
    """转换输入参数。"""
    workspace_id: str
    part_number: str
    version: str
    iteration: int
    source_path: str          # vault 中源文件路径
    output_format: str = "glb"


@dataclass
class ConversionOutput:
    """转换输出结果。"""
    success: bool
    output_path: str | None = None
    error_message: str | None = None
    quality: str = "LOW"
    metadata: dict[str, Any] = field(default_factory=dict)


class CADConverter(ABC):
    """CAD 格式转换器抽象基类。

    子类需实现：
    - type: 转换器类型标识
    - capabilities: 支持的输入/输出格式
    - convert(): 执行转换
    """

    @property
    @abstractmethod
    def type(self) -> str:
        ...

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """支持的输入扩展名列表（如 ['stp', 'step', 'igs']）。"""
        ...

    @abstractmethod
    def convert(self, input: ConversionInput) -> ConversionOutput:
        """执行 CAD 格式转换。"""
        ...
