from django.contrib import admin
from .models import CloudFile, Folder, ApiToken

@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display  = ['name', 'user', 'verein_name', 'aktiv', 'created_at', 'last_used']
    list_filter   = ['aktiv']
    search_fields = ['name', 'user__username', 'verein_name']
    readonly_fields = ['token', 'created_at', 'last_used']

    def save_model(self, request, obj, form, change):
        if not obj.token:
            from .models import ApiToken as T
            obj.token = T.generate()
        super().save_model(request, obj, form, change)

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'created_at']

@admin.register(CloudFile)
class CloudFileAdmin(admin.ModelAdmin):
    list_display  = ['original_name', 'owner', 'size_human', 'source_app',
                     'source_verein_name', 'source_kontext', 'is_public', 'uploaded_at']
    list_filter   = ['source_app', 'source_kontext', 'is_public']
    search_fields = ['original_name', 'owner__username', 'source_verein_name']
    readonly_fields = ['public_token', 'uploaded_at']
