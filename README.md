# SEMSDMS — Django replacement for documentUploadService

This project ports the business workflows found in the supplied Spring Boot source:
single upload, batch upload, final upload/MRN update, permanent download, temporary
download, service-wise file list, and temporary delete. It calls **FileServerApp
directly**; `documentUploadService` is not required at runtime.

## Important compatibility details

- The Java client encrypts compact JSON using AES/CBC/PKCS5Padding with a 16-byte
  all-zero IV. Python's PKCS7 padding is byte-compatible with Java PKCS5Padding for AES.
- The AES key file contains Base64 text. The decoded key is used for AES and HMAC-SHA256.
- Upload request form fields to FileServerApp are `dmsRegistrationNo`, `data`, and
  `transactionSignature`. Final upload uses `dms_registration_no`, `data`, and
  `user_transaction_signature`. These names are intentionally different because the
  Java code uses different endpoint contracts.
- The temporary upload payload keys are `arn`, `documentId`, `docTypeName`,
  `docNumber`, `file`, and `beneficiaryMobile`.
- `DMS_REGISTRATION_NO` defaults to the Java source's `DMS20260006`.
- The API does not accept `idn` and never sends it to FileServerApp. The original Java
  service persists `idn` in PostgreSQL after upload. Since the existing `file_upload`
  table requires it, set a trusted server-side `DMS_METADATA_IDN` if this deployment
  has a single applicable value. If unset, the upload still proceeds and the response
  explicitly says metadata was not saved. No fake IDN is generated.
- Batch Java code hard-coded a mobile number. This port uses `DMS_BATCH_BENEFICIARY_MOBILE`
  instead, to avoid baking a personal number into source code. Configure it if batch
  upload is used.
- Existing database tables are accessed with raw SQL; there are no migrations and no
  table/schema changes.
- No Java configuration secrets or certificate/key files are included in this archive.

## Setup on Windows

1. Extract this ZIP into `E:\\Projects\\SEMSDMS` (or another folder).
2. Create a virtual environment and install dependencies:
   ```powershell
   py -3.14 -m venv .venv
   .\\.venv\\Scripts\\python.exe -m pip install --upgrade pip
   .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and edit the database password and AES key path.
   Do not commit `.env` or key material.
4. Start the API:
   ```powershell
   .\\.venv\\Scripts\\python.exe manage.py runserver 127.0.0.1:8000
   ```
5. Swagger: `http://127.0.0.1:8000/api/docs/`
   OpenAPI JSON: `http://127.0.0.1:8000/api/schema/`

## Endpoints

All endpoints accept multipart/form data unless noted.

| Method | Endpoint | Java equivalent |
|---|---|---|
| POST | `/api/documents/upload/` | `/uploadDocument` |
| POST | `/api/documents/temporary-upload/` | Explicit temporary-upload alias |
| POST | `/api/documents/batch-upload/` | `/uploadBatchDocuments` |
| POST | `/api/documents/final-upload/` | `/finalUpload` |
| POST | `/api/documents/download/` | `/downloadFile` |
| POST | `/api/documents/download-temp/` | `/downloadFileFromTemp` |
| POST | `/api/documents/file-list/` | `/getFileListServiceWise` |
| POST | `/api/documents/delete/` | `/deleteDocument` |

### Upload fields

- `/upload/`: `file`, `fileNo`, `applnno`, `userId`
- `/temporary-upload/`: `file`, `arn`, `document_id`, optional `doc_type_name`, `beneficiary_mobile`
- `/batch-upload/`: one or more `files`, `applnno`
- `/final-upload/`: `applnno`, comma-separated `batchFileNames`
- `/download/`, `/download-temp/`: `arn`
- `/file-list/`: `applnno`, `serviceCode`
- `/delete/`: `fileNo`, `applnno`

The API accepts Java-style camelCase field names on Java-equivalent endpoints. The temporary
alias also accepts the field names used by the earlier SEMSDMS prototype.

## Before production

The supplied Java source contains environment-specific behavior (fixed registration number,
fixed AES key path, and a hard-coded batch beneficiary mobile). This project externalizes
those values. Confirm the exact deployed AES key file and PostgreSQL schema/column casing
before production use. Do not run migrations against the existing database.
