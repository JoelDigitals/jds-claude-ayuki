from django.contrib import admin
from .models import CloudFile, Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'created_at']
    list_filter = ['owner']
    search_fields = ['name', 'owner__username']


@admin.register(CloudFile)
class CloudFileAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'owner', 'folder', 'size', 'mime_type', 'is_public', 'uploaded_at']
    list_filter = ['owner', 'is_public', 'mime_type']
    search_fields = ['original_name', 'owner__username']
    readonly_fields = ['id', 'public_token', 'uploaded_at', 'updated_at']
