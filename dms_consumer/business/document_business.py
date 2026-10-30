import base64
import json
import os
import re

from dms_consumer.repositories.file_upload_repository import FileUploadRepository
from dms_consumer.services.crypto_service import JavaCompatibleCrypto
from dms_consumer.services.fileserver_client import FileServerClient, FileServerError


class DocumentBusiness:
    """Port of documentUploadService's staged/finalized document workflows."""

    def __init__(self):
        self._crypto = None
        self.client = FileServerClient()

    @property
    def crypto(self):
        if self._crypto is None:
            self._crypto = JavaCompatibleCrypto()
        return self._crypto

    @staticmethod
    def _clean_filename(filename):
        # Java StringUtils.cleanPath handles both slash styles; pathlib on Windows
        # alone would not normalize a Windows path when tests run on Linux.
        name = str(filename or "").replace("\\", "/").split("/")[-1]
        name = name.strip()
        if not name or name in {".", ".."}:
            return "document"
        return name

    def _prepare_upload_payload(self, *, arn, document_id, doc_type_name, file_bytes, beneficiary_mobile, doc_number="07"):
        payload = {
            "arn": arn,
            "documentId": str(document_id),
            "docTypeName": self._clean_filename(doc_type_name),
            "docNumber": str(doc_number),
            "file": base64.b64encode(file_bytes).decode("ascii"),
            "beneficiaryMobile": beneficiary_mobile or "",
        }
        # Keep insertion order and compact JSON to mirror JSONObject.toString().
        plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        encrypted = self.crypto.encrypt_text(plaintext)
        signature = self.crypto.hmac_b64(encrypted)
        return encrypted, signature

    def _submit_prepared(self, encrypted, signature):
        return self.client.submit_temporary_document(encrypted, signature)

    def _stage_file(self, *, arn, document_id, file_obj, beneficiary_mobile, doc_type_name=None):
        if not file_obj or not getattr(file_obj, "size", 0):
            return {"msg": "File is empty", "submittedToFileServer": False, "metadataSaved": False}, 400
        submission_enabled = (
            os.getenv("DMS_TEMP_UPLOAD_SUBMIT_ENABLED", "False")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"}
        )

        if not submission_enabled:
            return {
                "msg": "Temporary upload submission is disabled by configuration.",
                "submittedToFileServer": False,
                "metadataSaved": False,
            }, 503
        try:
            file_bytes = file_obj.read()
            encrypted, signature = self._prepare_upload_payload(
                arn=arn,
                document_id=document_id,
                doc_type_name=self._clean_filename(doc_type_name or file_obj.name),
                file_bytes=file_bytes,
                beneficiary_mobile=beneficiary_mobile,
            )
        except Exception as exc:
            # Legacy uploadDocument catches local preparation errors and returns a
            # business response. Crucially, no FileServerApp call or DB write occurs.
            return {
                "msg": "Upload preparation failed; document was not submitted.",
                "submittedToFileServer": False,
                "metadataSaved": False,
                "error": str(exc),
            }, 200

        try:
            file_server_response = self._submit_prepared(encrypted, signature)
        except Exception as exc:
            # A remote rejection/transport failure is not a successful stage.
            return {
                "msg": str(exc),
                "submittedToFileServer": False,
                "metadataSaved": False,
            }, 502

        configured_idn = os.getenv("DMS_METADATA_IDN", "").strip()
        try:
            metadata_saved, metadata_reason = FileUploadRepository.create_metadata(
                file_name=str(document_id),
                applnno=arn,
                idn=configured_idn,
                file_type="pdf",  # Retain the legacy table value for compatibility.
                uploaded_by=beneficiary_mobile or "",
            )
        except Exception as exc:
            # FileServerApp has already staged the file. Do not invite a blind retry
            # that could stage a duplicate; report the partial result explicitly.
            return {
                "msg": "FileServerApp accepted the document, but local tracking metadata could not be saved.",
                "arn": arn,
                "documentId": str(document_id),
                "submittedToFileServer": True,
                "metadataSaved": False,
                "metadataError": str(exc),
            }, 200

        response = {
            "msg": "success" if metadata_saved else "FileServerApp accepted the document; local tracking metadata was not saved.",
            "arn": arn,
            "documentId": str(document_id),
            "submittedToFileServer": True,
            "metadataSaved": metadata_saved,
        }
        if metadata_reason:
            response["metadataSaveReason"] = metadata_reason
        return response, 200

    def upload_single(self, *, document_id, file_obj, applnno, user_id, doc_type_name=None):
        return self._stage_file(
            arn=applnno,
            document_id=document_id,
            file_obj=file_obj,
            beneficiary_mobile=user_id,
            doc_type_name=doc_type_name,
        )

    def upload_batch(self, *, files, applnno):
        mobile = os.getenv("DMS_BATCH_BENEFICIARY_MOBILE", "").strip()
        outcomes = []
        for index, file_obj in enumerate(files, start=1):
            if not file_obj or not getattr(file_obj, "size", 0):
                # Java increments the numeric document ID even when a file is empty.
                outcomes.append({
                    "documentId": str(index), "msg": "File is empty; skipped",
                    "submittedToFileServer": False, "metadataSaved": False,
                })
                continue
            body, status_code = self._stage_file(
                arn=applnno,
                document_id=str(index),
                file_obj=file_obj,
                beneficiary_mobile=mobile,
                doc_type_name=file_obj.name,
            )
            outcomes.append(body)
            if status_code != 200 or not body.get("submittedToFileServer"):
                return {"msg": "error", "results": outcomes}, (
                    status_code if status_code in {502, 503} else 200
                )
        if any(item.get("metadataSaved") is False and item.get("submittedToFileServer") for item in outcomes):
            msg = "success_with_metadata_not_saved"
        else:
            msg = "success"
        return {"msg": msg, "results": outcomes}, 200

    def final_upload(self, applnno, batch_file_names):
        ids = [item.strip() for item in str(batch_file_names or "").split(",") if item.strip()]
        if not ids:
            return {"msg": "No document IDs were supplied", "finalizedAtFileServer": False}, 400
        try:
            payload = [{"arn": applnno}, [{"document_id": item} for item in ids]]
            plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
            encrypted = self.crypto.encrypt_text(plaintext)
            signature = self.crypto.hmac_b64(encrypted)
        except Exception as exc:
            return {
                "msg": "Final-upload preparation failed; FileServerApp was not called.",
                "finalizedAtFileServer": False,
                "error": str(exc),
            }, 502

        try:
            response = self.client.final_upload(encrypted, signature)
        except Exception as exc:
            return {"msg": str(exc), "finalizedAtFileServer": False}, 502
        if str(response.get("msg", "")).lower() != "success":
            return {
                "msg": response.get("msg") or "FileServerApp final upload failed.",
                "finalizedAtFileServer": False,
            }, 502

        encrypted_response = response.get("serviceEncryptedResponse")
        if not encrypted_response:
            return {
                "msg": "FileServerApp reported success but did not return the MRN response.",
                "finalizedAtFileServer": True,
                "metadataSaved": False,
            }, 502
        try:
            decoded = json.loads(self.crypto.decrypt_text(encrypted_response))
            if not isinstance(decoded, list):
                raise ValueError("Decrypted final-upload response is not a list.")
            documents = []
            invalid_documents = []
            for item in decoded:
                if not isinstance(item, dict):
                    continue
                arn = str(item.get("arn") or "")
                document_id = str(item.get("document_id") or "")
                mrn = str(item.get("mrn") or "")
                if arn and document_id and re.fullmatch(r"[0-9a-fA-F]{24}", mrn):
                    documents.append({"arn": arn, "documentId": document_id, "mrn": mrn})
                elif arn and document_id:
                    invalid_documents.append({
                        "arn": arn,
                        "documentId": document_id,
                        "reason": "FileServerApp did not return a valid MongoDB ObjectId MRN.",
                    })
            if not documents and not invalid_documents:
                raise ValueError("The final-upload response contained no document results.")
        except Exception as exc:
            return {
                "msg": "FileServerApp finalized the request, but SEMSDMS could not read the MRN response.",
                "finalizedAtFileServer": True,
                "metadataSaved": False,
                "error": str(exc),
            }, 502

        updated_count = 0
        metadata_error = None
        try:
            for document in documents:
                updated_count += FileUploadRepository.update_mrn(
                    document["arn"], document["documentId"], document["mrn"]
                )
        except Exception as exc:
            metadata_error = str(exc)

        expected_count = len(ids)
        returned_ids = [item["documentId"] for item in documents]
        all_requested_ids_returned = all(item in returned_ids for item in ids)
        complete = (
            metadata_error is None
            and not invalid_documents
            and len(documents) == expected_count
            and all_requested_ids_returned
            and updated_count >= expected_count
        )
        result = {
            "msg": "success" if complete else "finalized_but_tracking_incomplete",
            "finalizedAtFileServer": True,
            "metadataSaved": complete,
            "metadataUpdatedCount": updated_count,
            "documents": documents,
        }
        if invalid_documents:
            result["invalidDocuments"] = invalid_documents
        if not complete:
            result["warning"] = (
                "FileServerApp finalized the documents, but SEMSDMS could not confirm an MRN was stored "
                "for every requested document. Check DMS_METADATA_IDN and public.file_upload before retrying."
            )
            if metadata_error:
                result["metadataError"] = metadata_error
            result["requestedDocumentCount"] = expected_count
        return result, 200

    @staticmethod
    def _map_file_response(response):
        result = {}
        if isinstance(response, list):
            for item in response:
                if isinstance(item, dict) and item.get("fileName") is not None:
                    result[str(item["fileName"])] = item.get("data")
        return result

    def download_permanent(self, arn):
        try:
            mrns = FileUploadRepository.mrns_for_arn(arn)
            if not mrns:
                return {"msg": "No files found for the given Application No"}, 200
            response = self.client.download_by_mrn(mrns)
            result = self._map_file_response(response)
            result["msg"] = "success" if result else "No files found for the given Application No"
            return result, 200
        except Exception as exc:
            return {"msg": str(exc)}, 502

    def download_temporary(self, arn):
        try:
            response = self.client.download_temporary(arn)
            result = self._map_file_response(response)
            result["msg"] = "success"
            return result, 200
        except Exception as exc:
            return {"msg": str(exc)}, 502

    def list_temporary_documents(self, arn):
        try:
            documents = self.client.list_temporary_documents(arn)
            return {"msg": "success", "documents": documents}, 200
        except Exception as exc:
            return {"msg": str(exc)}, 502

    def list_permanent_documents(self, arn):
        try:
            documents = self.client.list_permanent_documents(arn)
            return {"msg": "success", "documents": documents}, 200
        except Exception as exc:
            return {"msg": str(exc)}, 502

    def file_list(self, applnno, service_code):
        try:
            return {"msg": "success", "fileList": FileUploadRepository.service_file_list(applnno, service_code)}, 200
        except Exception as exc:
            return {"msg": "error", "error": str(exc)}, 500

    def delete(self, file_no, applnno):
        try:
            msg = self.client.delete_temporary_document(applnno, file_no)
            return {"msg": msg}, (200 if str(msg).lower() == "success" else 502)
        except Exception as exc:
            return {"msg": str(exc)}, 502
