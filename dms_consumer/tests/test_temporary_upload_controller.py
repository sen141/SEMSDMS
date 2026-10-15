from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from dms_consumer.controllers.document_upload_controller import TemporaryUploadController


class TemporaryUploadControllerTests(SimpleTestCase):
    def test_temporary_request_does_not_require_or_forward_idn(self):
        request = APIRequestFactory().post("/temporary-upload", {
            "file": SimpleUploadedFile("pan.pdf", b"pdf-bytes"),
            "arn": "APP-1001",
            "document_id": "PAN",
            "beneficiary_mobile": "9000000000",
        }, format="multipart")
        business = Mock()
        business.upload_single.return_value = ({"msg": "success"}, 200)
        with patch("dms_consumer.controllers.document_upload_controller.DocumentBusiness", return_value=business):
            response = TemporaryUploadController.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("idn", business.upload_single.call_args.kwargs)
        self.assertIsNone(business.upload_single.call_args.kwargs["doc_type_name"])
