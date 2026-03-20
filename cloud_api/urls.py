from django.urls import path
from . import views

urlpatterns = [
    # ── Authentication ──────────────────────────────────────────────────────
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/',    views.ObtainTokenView.as_view(), name='login'),

    # ── Folders ─────────────────────────────────────────────────────────────
    path('folders/',           views.FolderListCreateView.as_view(), name='folder-list'),
    path('folders/<uuid:pk>/', views.FolderDetailView.as_view(),     name='folder-detail'),

    # ── Upload ───────────────────────────────────────────────────────────────
    path('upload/', views.FileUploadView.as_view(), name='file-upload'),

    # ── Files ────────────────────────────────────────────────────────────────
    path('files/',                          views.FileListView.as_view(),          name='file-list'),
    path('files/<uuid:pk>/',                views.FileDetailView.as_view(),        name='file-detail'),
    path('files/<uuid:pk>/download/',       views.FileDownloadView.as_view(),      name='file-download'),
    path('files/public/<uuid:token>/',      views.PublicFileDownloadView.as_view(),name='file-public'),

    # ── Stats ────────────────────────────────────────────────────────────────
    path('stats/', views.storage_stats, name='storage-stats'),
]
