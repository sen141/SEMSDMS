# Java-to-Django mapping

| Java component / operation | Django implementation |
|---|---|
| `FileUploadController.uploadDocument` | `DocumentUploadController` + `DocumentBusiness.upload_single` |
| `FileUploadBusinessImpl.uploadDocument` | `DocumentBusiness._stage_file` |
| `FileUploadBusinessImpl.uploadBatchDocuments` | `DocumentBusiness.upload_batch` |
| `FileUploadBusinessImpl.finalUpload` | `DocumentBusiness.final_upload` |
| `FileDownloadBusinessImpl.downloadEncryptedFile` | `DocumentBusiness.download_permanent` |
| `FileDownloadBusinessImpl.downloadEncryptedFileFromTemp` | `DocumentBusiness.download_temporary` |
| `FileDownloadBusinessImpl.getFileListServiceWise` | `DocumentBusiness.file_list` |
| `FileUploadBusinessImpl.deleteDocument` | `DocumentBusiness.delete` |
| `AesEncryption.encryptAES1` / `dencryptAES1` | `JavaCompatibleCrypto.encrypt_text` / `decrypt_text` |
| `HmacUtil.generateHmac` | `JavaCompatibleCrypto.hmac_b64` |
| `ProjectFunction.uploadMutationFile` | `FileServerClient.submit_temporary_document` |
| `ProjectFunction.finalUpload` | `FileServerClient.final_upload` |
| `ProjectFunction.callExternalServiceForFiles` | `FileServerClient.download_by_mrn` |
| `ProjectFunction.callExternalServiceForTempFiles` | `FileServerClient.download_temporary` |
| `ProjectFunction.deleteMutationFile` | `FileServerClient.delete_temporary_document` |
| `FileUploadRepository` | `FileUploadRepository` raw SQL against the existing schema |

## State and consistency rules

- Stage success means FileServerApp accepted a temporary file; it is not a permanent upload.
- `idn` is database-only metadata for the legacy Banglarbhumi tracking table. It is not part of the API and is not sent to FileServerApp. Since the existing schema requires it, metadata creation is skipped unless a legitimate server-side `DMS_METADATA_IDN` is configured.
- Finalization's encrypted response contains `arn`, `document_id`, and `mrn`. Django decrypts it and updates `file_upload.mrn`. A remote success with missing local MRN updates is reported as a partial result rather than a full success.
- No MongoDB code exists in Django: FileServerApp remains the owner of DMS PostgreSQL, MongoDB metadata, and GridFS operations.
