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

    def test_service_file_list_queries_acknowledgements_for_unique_file_names(self):
        with (
            patch.object(
                FileUploadRepository,
                "file_names_for_arn",
                return_value=["1", "2", "1"],
            ),
            patch(
                "dms_consumer.repositories.file_upload_repository.connection"
            ) as mocked_connection,
        ):
            cursor = mocked_connection.cursor.return_value.__enter__.return_value
            cursor.fetchall.return_value = [
                ("Copy of mutation certificate",),
                ("Required Document 1",),
            ]

            result = FileUploadRepository.service_file_list("APP-1001", "PT")

        self.assertEqual(
            result,
            [
                {"fileName": "Copy of mutation certificate"},
                {"fileName": "Required Document 1"},
            ],
        )
        cursor.execute.assert_called_once()
        sql, params = cursor.execute.call_args.args
        self.assertIn("WHERE code = %s", sql)
        self.assertIn("slno::text IN (%s, %s)", sql)
        self.assertEqual(params, ["PT", "1", "2"])

    def test_service_file_list_returns_empty_without_file_names(self):
        with (
            patch.object(
                FileUploadRepository,
                "file_names_for_arn",
                return_value=[],
            ),
            patch(
                "dms_consumer.repositories.file_upload_repository.connection"
            ) as mocked_connection,
        ):
            result = FileUploadRepository.service_file_list(
                "APP-WITHOUT-FILES", "PT"
            )

        self.assertEqual(result, [])
        mocked_connection.cursor.assert_not_called()
