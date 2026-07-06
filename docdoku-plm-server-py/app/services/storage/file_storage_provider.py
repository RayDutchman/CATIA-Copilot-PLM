"""FileStorageProvider: 文件系统存储实现。"""
from __future__ import annotations
import os
import shutil
import logging
from datetime import datetime
from typing import Optional, BinaryIO
from app.services.storage.storage_provider import StorageProvider

logger = logging.getLogger(__name__)


class FileStorageProvider(StorageProvider):
    """对标 Java com.docdoku.plm.server.storage.filesystem.FileStorageProvider。"""

    def __init__(self, vault_path: str):
        self._vault_path = vault_path

    def _virtual_path(self, bin_resource) -> str:
        return os.path.join(self._vault_path, bin_resource.fullName)

    def _generated_folder(self, bin_resource) -> str:
        vp = self._virtual_path(bin_resource)
        return os.path.join(os.path.dirname(vp), "_" + os.path.basename(vp))

    def get_binary_resource_stream(self, bin_resource) -> BinaryIO:
        path = self._virtual_path(bin_resource)
        if os.path.isfile(path):
            return open(path, "rb")
        raise FileNotFoundError(path)

    def get_binary_resource_file(self, bin_resource) -> str:
        path = self._virtual_path(bin_resource)
        if os.path.isfile(path):
            return path
        raise FileNotFoundError(path)

    def get_binary_resource_output_stream(self, bin_resource) -> BinaryIO:
        path = self._virtual_path(bin_resource)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return open(path, "wb")

    def copy_data(self, source_bin, target_bin) -> None:
        src = self._virtual_path(source_bin)
        if os.path.isfile(src):
            dst = self._virtual_path(target_bin)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        else:
            raise FileNotFoundError(src)

    def copy_file(self, file, target_bin) -> str:
        path = str(file) if not isinstance(file, str) else file
        if os.path.isfile(path):
            dst = self._virtual_path(target_bin)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(path, dst)
            return dst
        raise FileNotFoundError(path)

    def del_data(self, bin_resource) -> None:
        path = self._virtual_path(bin_resource)
        if os.path.isfile(path):
            os.remove(path)
        gen = self._generated_folder(bin_resource)
        if os.path.isdir(gen):
            shutil.rmtree(gen)
        self._clean_remove(os.path.dirname(path))

    def _clean_remove(self, folder: str) -> None:
        if folder != self._vault_path:
            try:
                if not os.listdir(folder):
                    os.rmdir(folder)
                    self._clean_remove(os.path.dirname(folder))
            except OSError:
                pass

    def get_external_uri(self, bin_resource) -> Optional[str]:
        return None

    def get_shorten_external_uri(self, bin_resource) -> Optional[str]:
        return None

    def delete_workspace_folder(self, workspace_id: str) -> None:
        if workspace_id:
            path = os.path.join(self._vault_path, workspace_id)
            if os.path.isdir(path):
                shutil.rmtree(path)

    def rename_data(self, file, new_name: str) -> None:
        path = str(file) if not isinstance(file, str) else file
        if os.path.isfile(path):
            os.rename(path, os.path.join(os.path.dirname(path), new_name))
        else:
            raise FileNotFoundError(path)

    def exists(self, bin_resource, generated_name: str) -> bool:
        return os.path.isfile(os.path.join(self._generated_folder(bin_resource), generated_name))

    def get_last_modified(self, bin_resource, generated_name: str) -> datetime:
        path = os.path.join(self._generated_folder(bin_resource), generated_name)
        if os.path.isfile(path):
            return datetime.fromtimestamp(os.path.getmtime(path))
        raise FileNotFoundError(path)

    def get_generated_file_stream(self, bin_resource, generated_name: str) -> BinaryIO:
        path = os.path.join(self._generated_folder(bin_resource), generated_name)
        if os.path.isfile(path):
            return open(path, "rb")
        raise FileNotFoundError(path)

    def get_generated_file_output_stream(self, bin_resource, generated_name: str) -> BinaryIO:
        path = os.path.join(self._generated_folder(bin_resource), generated_name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return open(path, "wb")
