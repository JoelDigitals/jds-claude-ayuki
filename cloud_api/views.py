import mimetypes
import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .models import CloudFile, Folder
from .serializers import (
    CloudFileSerializer,
    FileUploadSerializer,
    FolderSerializer,
)


# ── Auth ───────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    """Register a new user and return their API token."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        email = request.data.get('email', '').strip()

        if not username or not password:
            return Response(
                {'error': 'username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already taken.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(username=username, password=password, email=email)
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {'token': token.key, 'username': user.username},
            status=status.HTTP_201_CREATED,
        )


class ObtainTokenView(APIView):
    """Exchange credentials for an API token."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'username': user.username})


# ── Folders ────────────────────────────────────────────────────────────────────

class FolderListCreateView(generics.ListCreateAPIView):
    serializer_class = FolderSerializer

    def get_queryset(self):
        qs = Folder.objects.filter(owner=self.request.user)
        parent = self.request.query_params.get('parent')
        if parent == 'root':
            qs = qs.filter(parent=None)
        elif parent:
            qs = qs.filter(parent_id=parent)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FolderDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FolderSerializer

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)


# ── File Upload ────────────────────────────────────────────────────────────────

class FileUploadView(APIView):
    """
    POST /api/upload/
    Upload one or more files.  Use multipart/form-data.

    Form fields:
      files  – one or more file fields (required)
      folder – UUID of target folder   (optional)
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        files = request.FILES.getlist('files')
        if not files:
            # Also accept single file field named 'file'
            single = request.FILES.get('file')
            if single:
                files = [single]

        data = {'files': files, 'folder': request.data.get('folder')}
        serializer = FileUploadSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        folder = None
        folder_id = serializer.validated_data.get('folder')
        if folder_id:
            folder = get_object_or_404(Folder, id=folder_id, owner=request.user)

        created = []
        for f in serializer.validated_data['files']:
            mime, _ = mimetypes.guess_type(f.name)
            cloud_file = CloudFile.objects.create(
                owner=request.user,
                folder=folder,
                original_name=f.name,
                file=f,
                size=f.size,
                mime_type=mime or 'application/octet-stream',
            )
            created.append(cloud_file)

        return Response(
            CloudFileSerializer(created, many=True, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


# ── File List / Detail ─────────────────────────────────────────────────────────

class FileListView(generics.ListAPIView):
    """
    GET /api/files/
    List all files of the authenticated user.

    Query params:
      folder=<uuid>   filter by folder
      folder=root     only root-level files (no folder)
      search=<str>    search by original filename
    """
    serializer_class = CloudFileSerializer

    def get_queryset(self):
        qs = CloudFile.objects.filter(owner=self.request.user)
        folder = self.request.query_params.get('folder')
        if folder == 'root':
            qs = qs.filter(folder=None)
        elif folder:
            qs = qs.filter(folder_id=folder)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(original_name__icontains=search)
        return qs


class FileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/files/<id>/   – file metadata
    PATCH  /api/files/<id>/   – update folder or is_public flag
    DELETE /api/files/<id>/   – delete file
    """
    serializer_class = CloudFileSerializer

    def get_queryset(self):
        return CloudFile.objects.filter(owner=self.request.user)


# ── Download ───────────────────────────────────────────────────────────────────

class FileDownloadView(APIView):
    """
    GET /api/files/<id>/download/
    Stream the file back to the authenticated user.
    """
    def get(self, request, pk):
        cloud_file = get_object_or_404(CloudFile, pk=pk, owner=request.user)
        if not os.path.isfile(cloud_file.file.path):
            raise Http404("Physical file not found.")
        response = FileResponse(
            open(cloud_file.file.path, 'rb'),
            content_type=cloud_file.mime_type or 'application/octet-stream',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="{cloud_file.original_name}"'
        )
        return response


class PublicFileDownloadView(APIView):
    """
    GET /api/files/public/<token>/
    Download a file that has been shared publicly (no auth required).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        cloud_file = get_object_or_404(CloudFile, public_token=token, is_public=True)
        if not os.path.isfile(cloud_file.file.path):
            raise Http404("Physical file not found.")
        response = FileResponse(
            open(cloud_file.file.path, 'rb'),
            content_type=cloud_file.mime_type or 'application/octet-stream',
        )
        response['Content-Disposition'] = (
            f'attachment; filename="{cloud_file.original_name}"'
        )
        return response


# ── Storage Stats ──────────────────────────────────────────────────────────────

@api_view(['GET'])
def storage_stats(request):
    """GET /api/stats/ – total storage used by the authenticated user."""
    from django.db.models import Sum, Count
    stats = CloudFile.objects.filter(owner=request.user).aggregate(
        total_files=Count('id'),
        total_bytes=Sum('size'),
    )
    total_bytes = stats['total_bytes'] or 0

    def humanize(n):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if n < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} PB"

    return Response({
        'total_files': stats['total_files'],
        'total_bytes': total_bytes,
        'total_size_human': humanize(total_bytes),
    })
