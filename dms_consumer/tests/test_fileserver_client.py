from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from dms_consumer.services.fileserver_client import FileServerClient, FileServerError


class FileServerClientTests(SimpleTestCase):
    def setUp(self):
        self.client = FileServerClient()

    @patch("dms_consumer.services.fileserver_client.requests.post")
    def test_stage_uses_exact_file_server_form_names(self, post):
        response = Mock()
        response.json.return_value = {"msg": "success"}
        response.raise_for_status.return_value = None
        post.return_value = response
        result = self.client.submit_temporary_document("enc", "hmac")
        self.assertEqual(result["msg"], "success")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["data"]["dmsRegistrationNo"], self.client.registration_no)
        self.assertEqual(kwargs["data"]["data"], "enc")
        self.assertEqual(kwargs["data"]["transactionSignature"], "hmac")
        self.assertNotIn("idn", kwargs["data"])

    @patch("dms_consumer.services.fileserver_client.requests.post")
    def test_stage_rejects_application_level_failure(self, post):
        response = Mock()
        response.json.return_value = {"msg": "Please check user transaction signature"}
        response.raise_for_status.return_value = None
        post.return_value = response
        with self.assertRaises(FileServerError):
            self.client.submit_temporary_document("enc", "bad-hmac")

    @patch("dms_consumer.services.fileserver_client.requests.post")
    def test_finalize_uses_distinct_legacy_field_names(self, post):
        response = Mock()
        response.json.return_value = {"msg": "success"}
        response.raise_for_status.return_value = None
        post.return_value = response
        self.client.final_upload("enc", "hmac")
        data = post.call_args.kwargs["data"]
        self.assertIn("dms_registration_no", data)
        self.assertIn("user_transaction_signature", data)
        self.assertNotIn("dmsRegistrationNo", data)

    @patch("dms_consumer.services.fileserver_client.requests.post")
    def test_permanent_download_uses_json_mrn_list(self, post):
        response = Mock()
        response.json.return_value = [
            {"fileName": "document.pdf", "data": "cGRm"}
        ]
        response.raise_for_status.return_value = None
        post.return_value = response

        result = self.client.download_by_mrn(["MRN001", "MRN002"])

        self.assertEqual(result, [{"fileName": "document.pdf", "data": "cGRm"}])
        args, kwargs = post.call_args
        self.assertTrue(args[0].endswith("/downloadFile"))
        self.assertEqual(
            kwargs["json"],
            {
                "mrn": ["MRN001", "MRN002"],
                "dmsRegistrationNo": self.client.registration_no,
            },
        )
        self.assertEqual(kwargs["timeout"], self.client.timeout)

    @patch("dms_consumer.services.fileserver_client.requests.post")
    def test_temporary_download_uses_form_fields(self, post):
        response = Mock()
        response.json.return_value = [
            {"fileName": "temporary.pdf", "data": "cGRm"}
        ]
        response.raise_for_status.return_value = None
        post.return_value = response

        result = self.client.download_temporary("TEST-ARN")

        self.assertEqual(
            result, [{"fileName": "temporary.pdf", "data": "cGRm"}]
        )
        args, kwargs = post.call_args
        self.assertTrue(args[0].endswith("/downloadFileFromTemp"))
        self.assertEqual(
            kwargs["data"],
            {
                "arn": "TEST-ARN",
                "dmsRegistrationNo": self.client.registration_no,
            },
        )
        self.assertEqual(kwargs["timeout"], self.client.timeout)
