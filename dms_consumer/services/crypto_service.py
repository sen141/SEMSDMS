import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class CryptoConfigurationError(RuntimeError):
    pass


class JavaCompatibleCrypto:
    """Implements the AES/HMAC format used by the supplied Java client."""

    def __init__(self, key_path=None):
        configured = key_path or os.getenv("DMS_AES_KEY_PATH", "")
        if not configured:
            raise CryptoConfigurationError("DMS_AES_KEY_PATH is not configured.")
        path = Path(configured).expanduser()
        if not path.is_file():
            raise CryptoConfigurationError(f"AES key file does not exist: {path}")
        try:
            self.key = base64.b64decode(path.read_bytes().strip(), validate=True)
        except Exception as exc:
            raise CryptoConfigurationError("AES key file must contain valid Base64 text.") from exc
        if len(self.key) not in (16, 24, 32):
            raise CryptoConfigurationError("Decoded AES key must be 16, 24, or 32 bytes.")

    def encrypt_text(self, plaintext: str) -> str:
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(b"\x00" * 16))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        return base64.b64encode(ciphertext).decode("ascii")

    def decrypt_text(self, encrypted: str) -> str:
        ciphertext = base64.b64decode(encrypted, validate=True)
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(b"\x00" * 16))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")

    def hmac_b64(self, value: str) -> str:
        return base64.b64encode(hmac.new(self.key, value.encode("utf-8"), hashlib.sha256).digest()).decode("ascii")

    def make_upload_payload(self, *, arn, document_id, doc_type_name, doc_number, file_bytes, beneficiary_mobile):
        payload = {
            "arn": arn,
            "documentId": str(document_id),
            "docTypeName": doc_type_name,
            "docNumber": str(doc_number),
            "file": base64.b64encode(file_bytes).decode("ascii"),
            "beneficiaryMobile": beneficiary_mobile,
        }
        # Compact JSON matches JSONObject.toString() used by the Java client.
        plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        encrypted = self.encrypt_text(plaintext)
        return encrypted, self.hmac_b64(encrypted)
