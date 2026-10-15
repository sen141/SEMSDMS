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
