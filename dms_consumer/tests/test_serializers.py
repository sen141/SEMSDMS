import os
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from dms_consumer.dto.serializers import UploadSerializer, TemporaryUploadSerializer, BatchUploadSerializer


class SerializerTests(SimpleTestCase):
    def test_java_upload_does_not_require_idn(self):
        serializer = UploadSerializer(data={
            "fileNo": "1", "applnno": "TESTARN", "userId": "1234567890"
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)
        self.assertNotIn("idn", serializer.fields)

    def test_temporary_serializer_has_no_idn_field(self):
        self.assertNotIn("idn", TemporaryUploadSerializer().fields)

    def test_upload_size_limit_is_enforced(self):
        file_obj = SimpleUploadedFile("large.pdf", b"x" * 11, content_type="application/pdf")
        with patch.dict(os.environ, {"MAX_UPLOAD_MB": "0"}):
            serializer = UploadSerializer(data={
                "file": file_obj, "fileNo": "1", "applnno": "APP", "userId": "1234567890"
            })
            self.assertFalse(serializer.is_valid())
            self.assertIn("file", serializer.errors)

    def test_batch_serializer_accepts_repeated_file_list(self):
        serializer = BatchUploadSerializer(data={
            "files": [SimpleUploadedFile("a.pdf", b"a"), SimpleUploadedFile("b.pdf", b"b")],
            "applnno": "APP-1001",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
