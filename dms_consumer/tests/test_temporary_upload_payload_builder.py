import base64
import json
from unittest.mock import Mock

from django.test import SimpleTestCase
from dms_consumer.business.document_business import DocumentBusiness


class TemporaryUploadPayloadBuilderTests(SimpleTestCase):
    def test_payload_contains_expected_fields_and_base64_file_bytes(self):
        business = DocumentBusiness()
        crypto = Mock()
        crypto.encrypt_text.side_effect = lambda value: "encrypted:" + value
        crypto.hmac_b64.return_value = "signature"
        business._crypto = crypto
        encrypted, signature = business._prepare_upload_payload(
            arn="APP-1001", document_id="PAN", doc_type_name=r"C:\uploads\pan.pdf",
            file_bytes=b"sample-pdf", beneficiary_mobile="9000000000",
        )
        payload_json = encrypted.removeprefix("encrypted:")
        payload = json.loads(payload_json)
        self.assertEqual(payload["arn"], "APP-1001")
        self.assertEqual(payload["documentId"], "PAN")
        self.assertEqual(payload["docTypeName"], "pan.pdf")
        self.assertEqual(payload["docNumber"], "07")
        self.assertEqual(base64.b64decode(payload["file"]), b"sample-pdf")
        self.assertEqual(payload["beneficiaryMobile"], "9000000000")
        self.assertEqual(signature, "signature")
        crypto.hmac_b64.assert_called_once_with("encrypted:" + payload_json)
