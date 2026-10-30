from django.urls import path
from dms_consumer.controllers.document_upload_controller import (
    DocumentUploadController, TemporaryUploadController, BatchUploadController,
    FinalUploadController, DownloadController, TemporaryDownloadController,
    FileListController, DeleteController,
    TemporaryDocumentListController, PermanentDocumentListController,
)

urlpatterns = [
    # Recommended REST paths.
    path("upload/", DocumentUploadController.as_view(), name="upload-document"),
    path("temporary-upload/", TemporaryUploadController.as_view(), name="temporary-upload"),
    path("batch-upload/", BatchUploadController.as_view(), name="batch-upload"),
    path("final-upload/", FinalUploadController.as_view(), name="final-upload"),
    path("download/", DownloadController.as_view(), name="download-file"),
    path("download-temp/", TemporaryDownloadController.as_view(), name="download-file-temp"),
    path("file-list/", FileListController.as_view(), name="file-list-service-wise"),
    path("temporary-documents/", TemporaryDocumentListController.as_view(), name="temporary-document-metadata-list"),
    path("permanent-documents/", PermanentDocumentListController.as_view(), name="permanent-document-metadata-list"),
    path("delete/", DeleteController.as_view(), name="delete-document"),
    # Legacy operation-name aliases for a lower-friction migration from Java.
    path("uploadDocument", DocumentUploadController.as_view(), name="legacy-upload-document"),
    path("uploadBatchDocuments", BatchUploadController.as_view(), name="legacy-upload-batch-documents"),
    path("finalUpload", FinalUploadController.as_view(), name="legacy-final-upload"),
    path("downloadFile", DownloadController.as_view(), name="legacy-download-file"),
    path("downloadFileFromTemp", TemporaryDownloadController.as_view(), name="legacy-download-file-temp"),
    path("getFileListServiceWise", FileListController.as_view(), name="legacy-file-list-service-wise"),
    path("listTemporaryDocuments", TemporaryDocumentListController.as_view(), name="legacy-list-temporary-documents"),
    path("listPermanentDocuments", PermanentDocumentListController.as_view(), name="legacy-list-permanent-documents"),
    path("deleteDocument", DeleteController.as_view(), name="legacy-delete-document"),
]
