from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from dms_consumer.dto.serializers import TemporaryUploadSerializer


class TemporaryUploadSerializerTests(SimpleTestCase):
    def test_idn_is_not_a_serializer_field_or_required(self):
        serializer = TemporaryUploadSerializer(data={
            "file": SimpleUploadedFile("pan.pdf", b"pdf-bytes"),
            "arn": "APP-1001",
            "document_id": "PAN",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("idn", serializer.fields)
        self.assertNotIn("idn", serializer.validated_data)
