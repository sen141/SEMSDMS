import base64
import os
import tempfile
from pathlib import Path

from django.test import SimpleTestCase
from dms_consumer.services.crypto_service import JavaCompatibleCrypto


class CryptoServiceTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.key = os.urandom(32)
        self.key_path = Path(self.tmp.name) / "key.txt"
        self.key_path.write_text(base64.b64encode(self.key).decode("ascii"), encoding="ascii")
        self.crypto = JavaCompatibleCrypto(str(self.key_path))

    def test_encrypt_decrypt_round_trip(self):
        value = '{"arn":"TEST","documentId":"1"}'
        self.assertEqual(self.crypto.decrypt_text(self.crypto.encrypt_text(value)), value)

    def test_hmac_is_stable(self):
        encrypted = self.crypto.encrypt_text("payload")
        self.assertEqual(self.crypto.hmac_b64(encrypted), self.crypto.hmac_b64(encrypted))
