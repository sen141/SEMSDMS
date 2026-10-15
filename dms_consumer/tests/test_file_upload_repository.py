import os
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from dms_consumer.repositories.file_upload_repository import FileUploadRepository


class FileUploadRepositoryTests(SimpleTestCase):
    def test_missing_idn_skips_insert_without_opening_database(self):
        with patch(
            "dms_consumer.repositories.file_upload_repository.connection"
        ) as mocked_connection:
            saved, reason = FileUploadRepository.create_metadata(
                file_name="PAN",
                applnno="APP-1001",
                idn="",
                file_type="pdf",
                uploaded_by="9000000000",
            )

            self.assertFalse(saved)
            self.assertEqual(reason, "idn_not_available")
            mocked_connection.cursor.assert_not_called()

    def test_table_name_uses_configured_schema(self):
        with patch.dict(os.environ, {"DB_SCHEMA": "public"}):
            self.assertEqual(FileUploadRepository._table("file_upload"), '"public"."file_upload"')

    def test_invalid_schema_is_rejected(self):
        with patch.dict(os.environ, {"DB_SCHEMA": "public;drop table x"}):
            with self.assertRaises(ValueError):
                FileUploadRepository._table("file_upload")
