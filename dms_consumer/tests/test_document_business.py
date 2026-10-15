import json
import os
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from dms_consumer.business.document_business import DocumentBusiness
from dms_consumer.repositories.file_upload_repository import FileUploadRepository
from dms_consumer.services.fileserver_client import FileServerError


class DocumentBusinessTests(SimpleTestCase):
    def setUp(self):
        self.business = DocumentBusiness()
        self.upload = lambda name="sample.pdf", data=b"sample content": SimpleUploadedFile(
            name, data, content_type="application/pdf"
        )

    def test_successful_stage_without_configured_idn_does_not_fail_or_invent_idn(self):
        self.business._prepare_upload_payload = Mock(return_value=("encrypted", "signature"))
        self.business._submit_prepared = Mock(return_value={"msg": "success"})
        with patch.dict(os.environ, {"DMS_METADATA_IDN": ""}), patch.object(
            FileUploadRepository, "create_metadata", wraps=FileUploadRepository.create_metadata
        ) as create_metadata:
            body, status_code = self.business.upload_single(
                document_id="PAN", file_obj=self.upload(), applnno="APP-1001", user_id="9000000000"
            )
        self.assertEqual(status_code, 200)
        self.assertTrue(body["submittedToFileServer"])
        self.assertFalse(body["metadataSaved"])
        self.assertEqual(body["metadataSaveReason"], "idn_not_available")
        create_metadata.assert_called_once_with(
            file_name="PAN", applnno="APP-1001", idn="", file_type="pdf", uploaded_by="9000000000"
        )
        self.business._submit_prepared.assert_called_once_with("encrypted", "signature")

    def test_remote_stage_failure_returns_502_and_does_not_write_metadata(self):
        self.business._prepare_upload_payload = Mock(return_value=("encrypted", "signature"))
        self.business._submit_prepared = Mock(side_effect=FileServerError("remote rejected"))
        with patch.object(FileUploadRepository, "create_metadata") as create_metadata:
            body, status_code = self.business.upload_single(
                document_id="PAN", file_obj=self.upload(), applnno="APP-1001", user_id="9000000000"
            )
        self.assertEqual(status_code, 502)
        self.assertFalse(body["submittedToFileServer"])
        self.assertFalse(body["metadataSaved"])
        create_metadata.assert_not_called()

    def test_preparation_failure_returns_safe_business_error_without_submission(self):
        self.business._prepare_upload_payload = Mock(side_effect=RuntimeError("key file unavailable"))
        self.business._submit_prepared = Mock()
        with patch.object(FileUploadRepository, "create_metadata") as create_metadata:
            body, status_code = self.business.upload_single(
                document_id="PAN", file_obj=self.upload(), applnno="APP-1001", user_id="9000000000"
            )
        self.assertEqual(status_code, 200)
        self.assertFalse(body["submittedToFileServer"])
        self.assertFalse(body["metadataSaved"])
        self.business._submit_prepared.assert_not_called()
        create_metadata.assert_not_called()

    def test_stage_metadata_success_uses_server_configured_idn(self):
        self.business._prepare_upload_payload = Mock(return_value=("encrypted", "signature"))
        self.business._submit_prepared = Mock(return_value={"msg": "success"})
        with patch.dict(os.environ, {"DMS_METADATA_IDN": "LEGITIMATE-IDN"}), patch.object(
            FileUploadRepository, "create_metadata", return_value=(True, None)
        ) as create_metadata:
            body, status_code = self.business.upload_single(
                document_id="PAN", file_obj=self.upload(), applnno="APP-1001", user_id="9000000000"
            )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["msg"], "success")
        self.assertTrue(body["metadataSaved"])
        create_metadata.assert_called_once_with(
            file_name="PAN", applnno="APP-1001", idn="LEGITIMATE-IDN", file_type="pdf", uploaded_by="9000000000"
        )

    def test_temporary_upload_uses_explicit_doc_type_name(self):
        captured = {}

        def prepare(**kwargs):
            captured.update(kwargs)
            return "encrypted", "signature"

        self.business._prepare_upload_payload = prepare
        self.business._submit_prepared = Mock(return_value={"msg": "success"})
        with patch.dict(os.environ, {"DMS_METADATA_IDN": ""}):
            body, status_code = self.business.upload_single(
                document_id="1", file_obj=self.upload("original.pdf"), applnno="TESTARN",
                user_id="1234567890", doc_type_name=r"C:\uploads\declared-name.pdf",
            )
        self.assertEqual(status_code, 200)
        self.assertEqual(captured["doc_type_name"], "declared-name.pdf")
        self.assertTrue(body["submittedToFileServer"])

    def test_empty_file_is_rejected_before_submission(self):
        self.business._prepare_upload_payload = Mock()
        body, status_code = self.business.upload_single(
            document_id="1", file_obj=self.upload(data=b""), applnno="APP", user_id="1234567890"
        )
        self.assertEqual(status_code, 400)
        self.business._prepare_upload_payload.assert_not_called()

    def test_batch_increments_ids_even_when_empty_file_is_skipped(self):
        empty = self.upload("empty.pdf", b"")
        good = self.upload("good.pdf", b"good")
        self.business._prepare_upload_payload = Mock(return_value=("encrypted", "signature"))
        self.business._submit_prepared = Mock(return_value={"msg": "success"})
        with patch.dict(os.environ, {"DMS_METADATA_IDN": ""}):
            body, status_code = self.business.upload_batch(files=[empty, good], applnno="APP-1001")
        self.assertEqual(status_code, 200)
        self.assertEqual(body["results"][0]["documentId"], "1")
        self.assertFalse(body["results"][0]["submittedToFileServer"])
        self.assertEqual(body["results"][1]["documentId"], "2")
        self.assertTrue(body["results"][1]["submittedToFileServer"])

    def test_final_upload_decrypts_mrns_and_updates_local_tracking(self):
        self.business._crypto = Mock()
        self.business._crypto.encrypt_text.return_value = "encrypted-request"
        self.business._crypto.hmac_b64.return_value = "request-signature"
        self.business._crypto.decrypt_text.return_value = json.dumps([
            {"arn": "APP-1001", "document_id": "PAN", "mrn": "507f1f77bcf86cd799439011"},
            {"arn": "APP-1001", "document_id": "AADHAAR", "mrn": "507f191e810c19729de860ea"},
        ])
        self.business.client.final_upload = Mock(return_value={
            "msg": "success", "serviceEncryptedResponse": "encrypted-response", "serviceSignatureResponse": "rsa-signature"
        })
        with patch.object(FileUploadRepository, "update_mrn", side_effect=[1, 1]) as update_mrn:
            body, status_code = self.business.final_upload("APP-1001", "PAN,AADHAAR")
        self.assertEqual(status_code, 200)
        self.assertEqual(body["msg"], "success")
        self.assertTrue(body["finalizedAtFileServer"])
        self.assertTrue(body["metadataSaved"])
        self.assertEqual(body["documents"], [
            {"arn": "APP-1001", "documentId": "PAN", "mrn": "507f1f77bcf86cd799439011"},
            {"arn": "APP-1001", "documentId": "AADHAAR", "mrn": "507f191e810c19729de860ea"},
        ])
        self.assertEqual(update_mrn.call_count, 2)

    def test_final_upload_marks_remote_success_partial_if_no_local_rows_updated(self):
        self.business._crypto = Mock()
        self.business._crypto.encrypt_text.return_value = "encrypted-request"
        self.business._crypto.hmac_b64.return_value = "request-signature"
        self.business._crypto.decrypt_text.return_value = '[{"arn":"APP-1001","document_id":"PAN","mrn":"507f1f77bcf86cd799439011"}]'
        self.business.client.final_upload = Mock(return_value={
            "msg": "success", "serviceEncryptedResponse": "encrypted-response"
        })
        with patch.object(FileUploadRepository, "update_mrn", return_value=0):
            body, status_code = self.business.final_upload("APP-1001", "PAN")
        self.assertEqual(status_code, 200)
        self.assertTrue(body["finalizedAtFileServer"])
        self.assertFalse(body["metadataSaved"])
        self.assertEqual(body["msg"], "finalized_but_tracking_incomplete")
        self.assertEqual(body["documents"][0]["mrn"], "507f1f77bcf86cd799439011")

    def test_final_upload_never_stores_file_server_error_text_as_an_mrn(self):
        self.business._crypto = Mock()
        self.business._crypto.encrypt_text.return_value = "encrypted-request"
        self.business._crypto.hmac_b64.return_value = "request-signature"
        self.business._crypto.decrypt_text.return_value = json.dumps([
            {"arn": "APP-1001", "document_id": "PAN", "mrn": "No File has been found against this Document Id ...ERROR"}
        ])
        self.business.client.final_upload = Mock(return_value={
            "msg": "success", "serviceEncryptedResponse": "encrypted-response"
        })
        with patch.object(FileUploadRepository, "update_mrn") as update_mrn:
            body, status_code = self.business.final_upload("APP-1001", "PAN")
        self.assertEqual(status_code, 200)
        self.assertTrue(body["finalizedAtFileServer"])
        self.assertFalse(body["metadataSaved"])
        self.assertEqual(body["documents"], [])
        self.assertEqual(body["invalidDocuments"][0]["documentId"], "PAN")
        update_mrn.assert_not_called()

    def test_final_upload_rejects_empty_document_list(self):
        body, status_code = self.business.final_upload("APP-1001", " , ")
        self.assertEqual(status_code, 400)
        self.assertFalse(body["finalizedAtFileServer"])

    def test_permanent_download_does_not_call_file_server_without_mrns(self):
        with patch.object(FileUploadRepository, "mrns_for_arn", return_value=[]), patch.object(
            self.business.client, "download_by_mrn"
        ) as download:
            body, status_code = self.business.download_permanent("APP-1001")
        self.assertEqual(status_code, 200)
        self.assertIn("No files found", body["msg"])
        download.assert_not_called()

    def test_download_responses_are_returned_as_filename_maps(self):
        with patch.object(FileUploadRepository, "mrns_for_arn", return_value=["mrn-1"]), patch.object(
            self.business.client, "download_by_mrn", return_value=[{"fileName": "pan.pdf", "data": "cGRm"}]
        ):
            body, status_code = self.business.download_permanent("APP-1001")
        self.assertEqual(status_code, 200)
        self.assertEqual(body, {"pan.pdf": "cGRm", "msg": "success"})
