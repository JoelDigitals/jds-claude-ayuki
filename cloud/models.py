import os, uuid, secrets
from django.db import models
from django.contrib.auth.models import User


def upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"uploads/{instance.owner.id}/{uuid.uuid4().hex}{ext}"


# ── API Token für externe Apps (z.B. Vereins-App) ───────────────────────────
class ApiToken(models.Model):
    """Statische API-Tokens für externe Anwendungen."""
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_tokens')
    name        = models.CharField(max_length=100, help_text='z.B. "Vereins-App" oder "JDS-Verein"')
    token       = models.CharField(max_length=64, unique=True, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    last_used   = models.DateTimeField(null=True, blank=True)
    aktiv       = models.BooleanField(default=True)

    # Optional: Welche Verein-ID (aus dem Vereinsprojekt) darf hochladen
    verein_id   = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Verein-ID aus dem Vereinsprojekt (optional, für Filterung)'
    )
    verein_name = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'API Token'
        verbose_name_plural = 'API Tokens'

    def __str__(self):
        return f'{self.name} ({self.user.username})'

    @staticmethod
    def generate():
        return secrets.token_hex(32)  # 64 Zeichen langer sicherer Token

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = ApiToken.generate()
        super().save(*args, **kwargs)


class Folder(models.Model):
    owner  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    name   = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, blank=True,
                               on_delete=models.CASCADE, related_name='children')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'parent', 'name')
        ordering = ['name']

    def __str__(self):
        return self.name


class CloudFile(models.Model):
    owner         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='files')
    folder        = models.ForeignKey(Folder, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='files')
    original_name = models.CharField(max_length=500)
    file          = models.FileField(upload_to=upload_path)
    size          = models.BigIntegerField(default=0)
    mime_type     = models.CharField(max_length=200, blank=True)
    is_public     = models.BooleanField(default=False)
    public_token  = models.CharField(max_length=64, unique=True, default='')
    uploaded_at   = models.DateTimeField(auto_now_add=True)

    # Herkunft: externe API-Uploads bekommen Kontext
    source_app         = models.CharField(max_length=100, blank=True,
                                          help_text='z.B. "jds-verein"')
    source_verein_id   = models.PositiveIntegerField(null=True, blank=True)
    source_verein_name = models.CharField(max_length=255, blank=True)
    source_kontext     = models.CharField(max_length=50, blank=True,
                                          help_text='z.B. "satzung", "beleg", "protokoll"')
    source_ref_id      = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_name

    @property
    def extension(self):
        return os.path.splitext(self.original_name)[1].lower().lstrip('.')

    @property
    def size_human(self):
        n = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    @property
    def icon(self):
        ext = self.extension
        mapping = {
            'pdf': '📄', 'doc': '📝', 'docx': '📝', 'txt': '📝',
            'xls': '📊', 'xlsx': '📊', 'csv': '📊',
            'ppt': '📑', 'pptx': '📑',
            'jpg': '🖼', 'jpeg': '🖼', 'png': '🖼', 'gif': '🖼', 'webp': '🖼', 'svg': '🖼',
            'mp4': '🎬', 'mov': '🎬', 'avi': '🎬', 'mkv': '🎬',
            'mp3': '🎵', 'wav': '🎵', 'flac': '🎵',
            'zip': '🗜', 'rar': '🗜', '7z': '🗜', 'tar': '🗜', 'gz': '🗜',
            'py': '🐍', 'js': '⚡', 'html': '🌐', 'css': '🎨',
        }
        return mapping.get(ext, '📁')

    def save(self, *args, **kwargs):
        if not self.public_token:
            self.public_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)
