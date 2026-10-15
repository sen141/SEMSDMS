import os
from rest_framework import serializers


def _max_upload_bytes():
    try:
        return int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
    except ValueError:
        return 10 * 1024 * 1024


class UploadSizeMixin:
    def validate_file(self, value):
        if value.size <= 0:
            raise serializers.ValidationError("The uploaded file is empty.")
        if value.size > _max_upload_bytes():
            raise serializers.ValidationError(f"The file exceeds the {_max_upload_bytes() // (1024 * 1024)} MB upload limit.")
        return value


class UploadSerializer(UploadSizeMixin, serializers.Serializer):
    file = serializers.FileField()
    fileNo = serializers.CharField(max_length=128, trim_whitespace=True)
    applnno = serializers.CharField(max_length=128, trim_whitespace=True)
    userId = serializers.CharField(max_length=64, trim_whitespace=True)

    def validate_fileNo(self, value):
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_applnno(self, value):
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value

    def validate_userId(self, value):
        if not value:
            raise serializers.ValidationError("This field may not be blank.")
        return value


class TemporaryUploadSerializer(UploadSizeMixin, serializers.Serializer):
    file = serializers.FileField()
    arn = serializers.CharField(max_length=128, trim_whitespace=True)
    document_id = serializers.CharField(max_length=128, trim_whitespace=True)
    doc_type_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    beneficiary_mobile = serializers.CharField(max_length=64, required=False, allow_blank=True)


class BatchUploadSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField(), allow_empty=False, max_length=100)
    applnno = serializers.CharField(max_length=128, trim_whitespace=True)

    def validate_files(self, files):
        maximum = _max_upload_bytes()
        total = 0
        for file_obj in files:
            # The Java batch implementation skips empty files but still advances IDs.
            if file_obj.size > maximum:
                raise serializers.ValidationError(f"Each file must be no larger than {maximum // (1024 * 1024)} MB.")
            total += file_obj.size
        if total > maximum:
            raise serializers.ValidationError(f"The combined batch exceeds the {maximum // (1024 * 1024)} MB upload limit.")
        return files


class FinalUploadSerializer(serializers.Serializer):
    applnno = serializers.CharField(max_length=128, trim_whitespace=True)
    batchFileNames = serializers.CharField(max_length=4000, trim_whitespace=True)


class ArnSerializer(serializers.Serializer):
    arn = serializers.CharField(max_length=128, trim_whitespace=True)


class FileListSerializer(serializers.Serializer):
    applnno = serializers.CharField(max_length=128, trim_whitespace=True)
    serviceCode = serializers.CharField(max_length=128, trim_whitespace=True)


class DeleteSerializer(serializers.Serializer):
    fileNo = serializers.CharField(max_length=128, trim_whitespace=True)
    applnno = serializers.CharField(max_length=128, trim_whitespace=True)
