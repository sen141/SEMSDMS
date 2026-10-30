from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from dms_consumer.controllers.document_upload_controller import (
    TemporaryDocumentListController,
    PermanentDocumentListController,
)


class DocumentMetadataListControllerTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_temporary_list_passes_arn_to_business(self):
        expected = {
            "msg": "success",
            "documents": [{"arn": "APP-1001", "documentId": "DOC001"}],
        }
        business = Mock()
        business.list_temporary_documents.return_value = (expected, 200)
        request = self.factory.get("/api/documents/temporary-documents/?arn=APP-1001")

        with patch(
            "dms_consumer.controllers.document_upload_controller.DocumentBusiness",
            return_value=business,
        ):
            response = TemporaryDocumentListController.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)
        business.list_temporary_documents.assert_called_once_with("APP-1001")

    def test_permanent_list_passes_arn_to_business(self):
        expected = {"msg": "success", "documents": [{"mrn": "MRN001"}]}
        business = Mock()
        business.list_permanent_documents.return_value = (expected, 200)
        request = self.factory.get("/api/documents/permanent-documents/?arn=APP-1001")

        with patch(
            "dms_consumer.controllers.document_upload_controller.DocumentBusiness",
            return_value=business,
        ):
            response = PermanentDocumentListController.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, expected)
        business.list_permanent_documents.assert_called_once_with("APP-1001")

    def test_both_lists_reject_missing_arn(self):
        for controller in (
            TemporaryDocumentListController,
            PermanentDocumentListController,
        ):
            with self.subTest(controller=controller.__name__):
                request = self.factory.get("/api/documents/metadata/")
                response = controller.as_view()(request)
                self.assertEqual(response.status_code, 400)
