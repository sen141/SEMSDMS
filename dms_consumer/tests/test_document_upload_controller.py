from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from dms_consumer.controllers.document_upload_controller import DocumentUploadController


class DocumentUploadControllerTests(SimpleTestCase):
    def test_java_style_upload_accepts_request_without_idn(self):
        request = APIRequestFactory().post("/uploadDocument", {
            "file": SimpleUploadedFile("pan.pdf", b"pdf-bytes"),
            "fileNo": "PAN",
            "applnno": "APP-1001",
            "userId": "9000000000",
        }, format="multipart")
        business = Mock()
        business.upload_single.return_value = ({"msg": "success", "submittedToFileServer": True}, 200)
        with patch("dms_consumer.controllers.document_upload_controller.DocumentBusiness", return_value=business):
            response = DocumentUploadController.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("idn", business.upload_single.call_args.kwargs)
        self.assertEqual(business.upload_single.call_args.kwargs["document_id"], "PAN")
