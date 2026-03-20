import os
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


def user_upload_path(instance, filename):
    """Store files under media/uploads/<user_id>/<uuid>/<filename>"""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return f"uploads/{instance.owner.id}/{unique_name}"


class Folder(models.Model):
    """Virtual folder to organise files."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.CASCADE, related_name='children'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'parent', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class CloudFile(models.Model):
    """A file stored in the cloud."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    folder = models.ForeignKey(
        Folder, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='files'
    )
    original_name = models.CharField(max_length=500)
    file = models.FileField(upload_to=user_upload_path)
    size = models.BigIntegerField(default=0, help_text=_('File size in bytes'))
    mime_type = models.CharField(max_length=200, blank=True)
    is_public = models.BooleanField(default=False, help_text=_('Publicly accessible without auth'))
    public_token = models.UUIDField(default=uuid.uuid4, unique=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_name

    @property
    def extension(self):
        return os.path.splitext(self.original_name)[1].lower()

    def delete(self, *args, **kwargs):
        """Also delete the physical file when the model is deleted."""
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)
