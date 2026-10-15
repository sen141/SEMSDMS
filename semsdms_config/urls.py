from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from dms_consumer.views import HealthView
from dms_consumer.controllers.document_upload_controller import (
    DocumentUploadController, BatchUploadController, FinalUploadController,
    DownloadController, TemporaryDownloadController, FileListController, DeleteController,
)

urlpatterns = [
    path("", HealthView.as_view(), name="root-health"),
    path("health/", HealthView.as_view(), name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/documents/", include("dms_consumer.urls")),
    path("uploadDocument", DocumentUploadController.as_view(), name="legacy-upload-document-root"),
    path("uploadBatchDocuments", BatchUploadController.as_view(), name="legacy-upload-batch-root"),
    path("finalUpload", FinalUploadController.as_view(), name="legacy-final-upload-root"),
    path("downloadFile", DownloadController.as_view(), name="legacy-download-root"),
    path("downloadFileFromTemp", TemporaryDownloadController.as_view(), name="legacy-download-temp-root"),
    path("getFileListServiceWise", FileListController.as_view(), name="legacy-file-list-root"),
    path("deleteDocument", DeleteController.as_view(), name="legacy-delete-root"),
]
