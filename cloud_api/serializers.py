import mimetypes
from django.conf import settings
from rest_framework import serializers
from .models import CloudFile, Folder


class FolderSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = ['id', 'name', 'parent', 'children_count', 'files_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_children_count(self, obj):
        return obj.children.count()

    def get_files_count(self, obj):
        return obj.files.count()

    def validate_name(self, value):
        forbidden = ['/', '\\', '..', '\x00']
        for char in forbidden:
            if char in value:
                raise serializers.ValidationError(
                    f"Folder name must not contain '{char}'."
                )
        return value.strip()


class CloudFileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()
    size_human = serializers.SerializerMethodField()

    class Meta:
        model = CloudFile
        fields = [
            'id', 'original_name', 'folder', 'size', 'size_human',
            'mime_type', 'extension', 'is_public',
            'download_url', 'public_url',
            'uploaded_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'original_name', 'size', 'size_human',
            'mime_type', 'extension', 'public_token',
            'download_url', 'public_url',
            'uploaded_at', 'updated_at',
        ]

    def get_download_url(self, obj):
        request = self.context.get('request')
        url = f"/api/files/{obj.id}/download/"
        return request.build_absolute_uri(url) if request else url

    def get_public_url(self, obj):
        if not obj.is_public:
            return None
        request = self.context.get('request')
        url = f"/api/files/public/{obj.public_token}/"
        return request.build_absolute_uri(url) if request else url

    def get_size_human(self, obj):
        size = obj.size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


class FileUploadSerializer(serializers.Serializer):
    """Used for the upload endpoint — accepts one or more files."""
    files = serializers.ListField(
        child=serializers.FileField(max_length=500, allow_empty_file=False),
        allow_empty=False,
    )
    folder = serializers.UUIDField(required=False, allow_null=True)

    def validate_files(self, files):
        max_size = getattr(settings, 'CLOUD_MAX_FILE_SIZE', 524288000)
        allowed_ext = getattr(settings, 'CLOUD_ALLOWED_EXTENSIONS', [])

        for f in files:
            if f.size > max_size:
                raise serializers.ValidationError(
                    f"'{f.name}' exceeds the maximum upload size of "
                    f"{max_size // 1024 // 1024} MB."
                )
            if allowed_ext:
                import os
                ext = os.path.splitext(f.name)[1].lower().lstrip('.')
                if ext not in allowed_ext:
                    raise serializers.ValidationError(
                        f"File type '.{ext}' is not allowed. "
                        f"Allowed: {', '.join(allowed_ext)}"
                    )
        return files
