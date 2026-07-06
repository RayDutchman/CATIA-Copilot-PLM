"""CryptoConverter: database column-level AES-CBC encryptor/decryptor."""
from __future__ import annotations
import base64
import logging
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

logger = logging.getLogger(__name__)


class CryptoConverter:
    """对标 Java com.docdoku.plm.server.storage.CryptoConverter JPA AttributeConverter。"""

    def __init__(self, key: bytes):
        self._key = key

    def convert_to_db(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        try:
            iv = os.urandom(16)
            cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv))
            encryptor = cipher.encryptor()
            data = value.encode("utf-8")
            pad_len = 16 - (len(data) % 16)
            data += bytes([pad_len]) * pad_len
            encrypted = encryptor.update(data) + encryptor.finalize()
            return base64.b64encode(iv).decode() + "." + base64.b64encode(encrypted).decode()
        except Exception:
            logger.exception("Cannot encrypt, stores the value unchanged")
            return value

    def convert_from_db(self, stored: Optional[str]) -> Optional[str]:
        if not stored:
            return stored
        try:
            parts = stored.split(".")
            iv = base64.b64decode(parts[0])
            encrypted = base64.b64decode(parts[1])
            cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded = decryptor.update(encrypted) + decryptor.finalize()
            pad_len = padded[-1]
            return padded[:-pad_len].decode("utf-8")
        except Exception:
            logger.exception("Cannot decrypt, returns the value as stored")
            return stored
