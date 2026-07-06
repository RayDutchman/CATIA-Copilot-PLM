"""StorageProvider: 二进制资源存储抽象接口。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, BinaryIO


class StorageProvider(ABC):
    """对标 Java com.docdoku.plm.server.storage.StorageProvider 接口。"""

    @abstractmethod
    def get_binary_resource_stream(self, binary_resource) -> BinaryIO: ...

    @abstractmethod
    def get_binary_resource_file(self, binary_resource) -> str: ...

    @abstractmethod
    def get_binary_resource_output_stream(self, binary_resource) -> BinaryIO: ...

    @abstractmethod
    def copy_data(self, source_bin, target_bin) -> None: ...

    @abstractmethod
    def del_data(self, binary_resource) -> None: ...

    @abstractmethod
    def get_external_uri(self, binary_resource) -> Optional[str]: ...

    @abstractmethod
    def get_shorten_external_uri(self, binary_resource) -> Optional[str]: ...

    @abstractmethod
    def delete_workspace_folder(self, workspace_id: str) -> None: ...

    @abstractmethod
    def rename_data(self, file, new_name: str) -> None: ...

    @abstractmethod
    def exists(self, binary_resource, generated_name: str) -> bool: ...

    @abstractmethod
    def get_last_modified(self, binary_resource, generated_name: str) -> datetime: ...

    @abstractmethod
    def get_generated_file_stream(self, binary_resource, generated_name: str) -> BinaryIO: ...

    @abstractmethod
    def get_generated_file_output_stream(self, binary_resource, generated_name: str) -> BinaryIO: ...

    @abstractmethod
    def copy_file(self, file, target_bin) -> str: ...
