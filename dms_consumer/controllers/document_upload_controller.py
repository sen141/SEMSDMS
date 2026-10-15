from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from dms_consumer.business.document_business import DocumentBusiness
from dms_consumer.dto.serializers import (
    UploadSerializer, TemporaryUploadSerializer, BatchUploadSerializer,
    FinalUploadSerializer, ArnSerializer, FileListSerializer, DeleteSerializer,
)


def execute_business(call):
    body, http_status = call
    return Response(body, status=http_status)


class DocumentUploadController(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(summary="Upload a document", request=UploadSerializer, responses={200: OpenApiResponse(description="FileServerApp result")})
    def post(self, request):
        serializer = UploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return execute_business(DocumentBusiness().upload_single(
            document_id=data["fileNo"],
            file_obj=data["file"],
            applnno=data["applnno"],
            user_id=data["userId"],
        ))


class TemporaryUploadController(APIView):
    serializer_class = TemporaryUploadSerializer
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
    summary="Upload a temporary document directly to FileServerApp",
    request=TemporaryUploadSerializer,
    responses={200: OpenApiResponse(description="FileServerApp result")},
)
    def post(self, request):
        serializer = TemporaryUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return execute_business(DocumentBusiness().upload_single(
            document_id=data["document_id"],
            file_obj=data["file"],
            applnno=data["arn"],
            user_id=data.get("beneficiary_mobile", ""),
            doc_type_name=data.get("doc_type_name") or None,
        ))


class BatchUploadController(APIView):
    serializer_class = BatchUploadSerializer
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(summary="Upload multiple documents", request=BatchUploadSerializer)
    def post(self, request):
        # Django QueryDict returns multiple values for repeated "files" form keys.
        files = request.FILES.getlist("files")
        applnno = request.data.get("applnno")
        serializer = BatchUploadSerializer(data={"files": files, "applnno": applnno})
        serializer.is_valid(raise_exception=True)
        return execute_business(DocumentBusiness().upload_batch(
            files=serializer.validated_data["files"],
            applnno=serializer.validated_data["applnno"],
        ))


class FinalUploadController(APIView):
    serializer_class = FinalUploadSerializer
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    @extend_schema(summary="Finalize uploaded documents and update MRNs", request=FinalUploadSerializer)
    def post(self, request):
        serializer = FinalUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return execute_business(DocumentBusiness().final_upload(data["applnno"], data["batchFileNames"]))


class DownloadController(APIView):
    serializer_class = ArnSerializer
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    @extend_schema(summary="Download permanent files by application number", request=ArnSerializer)
    def post(self, request):
        serializer = ArnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return execute_business(DocumentBusiness().download_permanent(serializer.validated_data["arn"]))


class TemporaryDownloadController(APIView):
    serializer_class = ArnSerializer
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    @extend_schema(summary="Download temporary files by application number", request=ArnSerializer)
    def post(self, request):
        serializer = ArnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return execute_business(DocumentBusiness().download_temporary(serializer.validated_data["arn"]))


class FileListController(APIView):
    serializer_class = FileListSerializer
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    @extend_schema(summary="Get uploaded file list for a service", request=FileListSerializer)
    def post(self, request):
        serializer = FileListSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return execute_business(DocumentBusiness().file_list(data["applnno"], data["serviceCode"]))


class DeleteController(APIView):
    serializer_class = DeleteSerializer
    parser_classes = [FormParser, MultiPartParser, JSONParser]

    @extend_schema(summary="Delete a temporary document", request=DeleteSerializer)
    def post(self, request):
        serializer = DeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return execute_business(DocumentBusiness().delete(data["fileNo"], data["applnno"]))
