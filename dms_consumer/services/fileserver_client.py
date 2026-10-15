import os
from urllib.parse import urljoin

import requests


class FileServerError(RuntimeError):
    """A transport or application-level error returned by FileServerApp."""


class FileServerClient:
    def __init__(self):
        self.base_url = os.getenv(
            "FILESERVER_BASE_URL",
            "http://192.168.56.62:3543/DocumentManagementSystem/service",
        ).rstrip("/") + "/"
        self.registration_no = os.getenv("DMS_REGISTRATION_NO", "DMS20260006").strip()
        self.timeout = float(os.getenv("FILESERVER_TIMEOUT_SECONDS", "30"))

    def _url(self, endpoint):
        return urljoin(self.base_url, endpoint.lstrip("/"))

    def _post_form(self, endpoint, data):
        try:
            response = requests.post(self._url(endpoint), data=data, timeout=self.timeout)
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise FileServerError(f"FileServerApp request to {endpoint} failed: {exc}") from exc
        except ValueError as exc:
            raise FileServerError(f"FileServerApp returned a non-JSON response from {endpoint}.") from exc
        if not isinstance(body, dict):
            raise FileServerError(f"FileServerApp returned an unexpected response from {endpoint}.")
        return body

    def _post_json(self, endpoint, data):
        try:
            response = requests.post(self._url(endpoint), json=data, timeout=self.timeout)
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise FileServerError(f"FileServerApp request to {endpoint} failed: {exc}") from exc
        except ValueError as exc:
            raise FileServerError(f"FileServerApp returned a non-JSON response from {endpoint}.") from exc
        if not isinstance(body, list):
            raise FileServerError(f"FileServerApp returned an unexpected response from {endpoint}.")
        return body

    @staticmethod
    def _require_success(body, operation):
        if str(body.get("msg", "")).lower() != "success":
            raise FileServerError(body.get("msg") or f"FileServerApp {operation} failed.")
        return body

    def submit_temporary_document(self, encrypted_data, signature):
        body = self._post_form("onChangeFileSubmit", {
            "dmsRegistrationNo": self.registration_no,
            "data": encrypted_data,
            "transactionSignature": signature,
        })
        return self._require_success(body, "temporary upload")

    def delete_temporary_document(self, arn, document_id):
        body = self._post_form("onChangeFileDelete", {
            "dmsRegistrationNo": self.registration_no,
            "arn": arn,
            "documentId": str(document_id),
        })
        return body.get("msg", "success")

    def final_upload(self, encrypted_data, signature):
        return self._post_form("upload", {
            "dms_registration_no": self.registration_no,
            "data": encrypted_data,
            "user_transaction_signature": signature,
        })

    def download_by_mrn(self, mrns):
        return self._post_json("downloadFile", {
            "mrn": mrns,
            "dmsRegistrationNo": self.registration_no,
        })

    def download_temporary(self, arn):
        try:
            response = requests.post(
                self._url("downloadFileFromTemp"),
                data={"arn": arn, "dmsRegistrationNo": self.registration_no},
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise FileServerError(f"FileServerApp request to downloadFileFromTemp failed: {exc}") from exc
        except ValueError as exc:
            raise FileServerError("FileServerApp returned a non-JSON response from downloadFileFromTemp.") from exc
        if not isinstance(body, list):
            raise FileServerError("FileServerApp returned an unexpected temporary-download response.")
        return body
